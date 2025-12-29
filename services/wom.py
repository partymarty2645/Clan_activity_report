import asyncio
import logging
import aiohttp
import json
from datetime import datetime
from core.config import Config
from core.performance import retry_async, timed_operation

class WOMClient:
    def __init__(self):
        self.api_key = Config.WOM_API_KEY
        self.base_url = Config.WOM_BASE_URL
        self.rate_limit_delay = float(Config.WOM_RATE_LIMIT_DELAY or 0.67)
        self.target_rpm = int(Config.WOM_TARGET_RPM or 90)
        self.max_concurrent = int(Config.WOM_MAX_CONCURRENT or 5)
        self.user_agent = 'NevrLucky (Contact: partymarty94)'
        self.logger = logging.getLogger('WOMClient')
        self._session = None
        self._cache = {} 
        self._cache_ttl = 300
        self._max_cache_size = 1000  # BUG-001: Prevent unbounded growth
        self._rate_limit_hits = []
        self._semaphore = None
        self._last_request_time = 0
        self._delay_lock = None
        self._creation_lock = asyncio.Lock()  # Prevent concurrent session creation

    async def _get_session(self):
        # Use creation lock to prevent race condition when creating session
        # (prevents multiple concurrent calls from creating multiple session instances)
        async with self._creation_lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=30)
                self._session = aiohttp.ClientSession(timeout=timeout)
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        if self._delay_lock is None:
            self._delay_lock = asyncio.Lock()
        return self._session

    async def close(self):
        # Display rate limit stats before closing
        if self._rate_limit_hits:
            recent_hits = [t for t in self._rate_limit_hits if asyncio.get_event_loop().time() - t < 3600]
            if recent_hits:
                print(f"\033[91m⚠️  WOM Rate Limit Summary: {len(recent_hits)} hits in last hour\033[0m")
        
        if self._session and not self._session.closed:
            await self._session.close()
            # Wait for underlying connections to close properly
            await asyncio.sleep(0.25)
    
    def _get_cache_key(self, endpoint, params):
        params_str = json.dumps(params or {}, sort_keys=True)
        return f"{endpoint}:{params_str}"
    
    def _get_cached(self, cache_key):
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            age = asyncio.get_event_loop().time() - timestamp
            if age < self._cache_ttl:
                return data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key, data):
        # BUG-001 Fix: Enforce cache limits
        if len(self._cache) >= self._max_cache_size:
            now = asyncio.get_event_loop().time()
            # 1. Prune all expired items first
            expired = [k for k, (ts, _) in self._cache.items() if now - ts >= self._cache_ttl]
            for k in expired:
                del self._cache[k]
            
            # 2. If still full, remove the oldest item (FIFO - Python dicts preserve insertion order)
            if len(self._cache) >= self._max_cache_size:
                try:
                    # Efficiently get the first key (oldest inserted)
                    del self._cache[next(iter(self._cache))]
                except StopIteration:
                    pass # Should not happen if len check passed

        self._cache[cache_key] = (asyncio.get_event_loop().time(), data)

    def _adjust_rate_limit(self):
        """Adaptively adjust rate limit based on 429 hits."""
        now = asyncio.get_event_loop().time()
        # Clean old hits (>5 minutes)
        self._rate_limit_hits = [t for t in self._rate_limit_hits if now - t < 300]
        
        if len(self._rate_limit_hits) > 3:  # Multiple 429s recently
            self.rate_limit_delay = min(self.rate_limit_delay * 1.1, 5.0)  # Cap at 5s max
            self.target_rpm = int(60 / self.rate_limit_delay)
            self.logger.warning(f"Adaptive rate limit: Slowing to ~{self.target_rpm} RPM (delay={self.rate_limit_delay:.2f}s)")
        elif len(self._rate_limit_hits) == 0 and self.rate_limit_delay > 0.67:
            self.rate_limit_delay *= 0.9
            self.target_rpm = int(60 / self.rate_limit_delay)
            # self.logger.info(f"Adaptive rate limit: Speeding up to ~{self.target_rpm} RPM")

    async def _request(self, method, endpoint, data=None, params=None, use_cache=True):
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        headers = {'User-Agent': self.user_agent}
        if self.api_key:
            headers['x-api-key'] = self.api_key

        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        # Rate Limit Pacing
        async with self._delay_lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
            # Reset time to NOW (start of this virtual slot)
            self._last_request_time = asyncio.get_event_loop().time()
            
        # Perform Request (Outside Serial Lock)
        for attempt in range(6): 
            try:
                # Re-check session inside retry loop just in case
                session = await self._get_session()
                async with session.request(method, url, json=data, params=params, headers=headers) as response:
                    
                    if response.status == 429:
                        self._rate_limit_hits.append(asyncio.get_event_loop().time())
                        self._adjust_rate_limit()
                        
                        wait_time = min((2 ** attempt) * 5.0, 60.0)
                        rate_limit_msg = f"🔴 WOM RATE LIMIT HIT (429) - Waiting {wait_time:.1f}s before retry (Attempt {attempt+1}/6)"
                        print(f"\033[91m{rate_limit_msg}\033[0m")  # Print in RED to stdout
                        self.logger.warning(rate_limit_msg)
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status >= 500:
                        wait_time = min((2 ** attempt) * 2.0, 30.0)
                        self.logger.warning(f"WOM Server Error {response.status}. Retrying in {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    result = await response.json()
                    
                    if method == 'GET' and use_cache:
                        self._set_cache(self._get_cache_key(endpoint, params), result)
                    
                    # Clear old hits on success to allow speedup
                    self._rate_limit_hits = [t for t in self._rate_limit_hits if asyncio.get_event_loop().time() - t < 300]
                    return result

            except aiohttp.ClientResponseError as e:
                # Specific check for Auth Errors
                if e.status in [401, 403]:
                    self.logger.error(f"AUTH ERROR: Access Denied ({e.status}). Please check your WOM_API_KEY in .env!")
                    raise Exception("WOM API Authentication Failed")
                
                self.logger.error(f"WOM API Client Error: {e.status} - {e.message}")
                if e.status == 502:
                     self.logger.warning("WOM 502 Bad Gateway. Retrying is typically effective.")
                raise
            except Exception as e:
                self.logger.error(f"Request Error (Attempt {attempt+1}): {e}")
                await asyncio.sleep(2 * (attempt + 1)) # Linear backoff
        
        raise Exception(f"Max retries exceeded for WOM API: {endpoint}")

    @timed_operation("WOM Get Group Members")
    async def get_group_members(self, group_id):
        if not group_id or not str(group_id).strip():
            self.logger.error("WOM Group ID is missing or empty.")
            return []
            
        # Use simple get for group payload which includes members
        data = await self._request('GET', f'/groups/{group_id}')
        members = []
        if data and 'memberships' in data:
            for m in data['memberships']:
                player = m.get('player', {})
                members.append({
                    'username': player.get('username'),
                    'displayName': player.get('displayName'),
                    'role': m.get('role'),
                    'joined_at': m.get('createdAt')
                })
        return members

    async def get_player_details(self, username):
        return await self._request('GET', f'/players/{username}')

    async def update_player(self, username):
        """Request a fresh scan for a player."""
        return await self._request('POST', f'/players/{username}')
    
    async def search_name_changes(self, username, limit=5):
        params = {'username': username, 'status': 'approved', 'limit': limit}
        return await self._request('GET', '/names', params=params)

    async def get_player_name_changes(self, username):
        """Fetch approved name changes for a single player.

        Docs: GET /players/:username/names
        Returns an array of NameChange objects.
        """
        if not username:
            return []
        return await self._request('GET', f'/players/{username}/names')

    @timed_operation("WOM Update Group")
    async def update_group(self, group_id, secret_code):
        data = {'verificationCode': secret_code}
        return await self._request('POST', f'/groups/{group_id}/update-all', data=data)

    async def get_player_gains(self, username, period, start_date=None, end_date=None):
        params = {}
        if period:
            params['period'] = period
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        return await self._request('GET', f'/players/{username}/gained', params=params)

    async def get_player_snapshots(self, username, period='all', start_date=None, end_date=None):
        """Fetches snapshot history for a player, handling pagination."""
        params = {}
        if period and period != 'all':
            params['period'] = period
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
            
        # Pagination loop
        all_snapshots = []
        offset = 0
        limit = 100 # Increased from 20 to 100 to reduce volume of requests
        
        while True:
            params['offset'] = offset
            params['limit'] = limit
            
            # self.logger.info(f"Fetching snapshots for {username} offset={offset}")
            batch = await self._request('GET', f'/players/{username}/snapshots', params=params)
            
            if not batch:
                break
                
            all_snapshots.extend(batch)
            
            if len(batch) < limit:
                break
                
            offset += limit
            
            # Safety break to avoid infinite loops if API behaves weirdly
            if offset > 5000: # 5000 snapshots is years of data
                break
                
        return all_snapshots

# REMOVED: Global singleton - Use ServiceFactory.get_wom_client() instead
