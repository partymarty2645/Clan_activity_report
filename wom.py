import os
import asyncio
import logging
import aiohttp
import random
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Singleton instance
wom_client = None

class WOMClient:
    def __init__(self):
        self.api_key = os.getenv('WOM_API_KEY')
        self.base_url = os.getenv('WOM_BASE_URL', 'https://api.wiseoldman.net/v2')
        self.rate_limit_delay = float(os.getenv('WOM_RATE_LIMIT_DELAY', 0.67))  # ~90 RPM (60s/90 = 0.67s)
        self.target_rpm = int(os.getenv('WOM_TARGET_RPM', 90))  # Target requests per minute
        self.max_concurrent = int(os.getenv('WOM_MAX_CONCURRENT', 5))  # Concurrent requests
        self.user_agent = 'NevrLucky (Contact: partymarty94)'
        self.logger = logging.getLogger('WOMClient')
        self._session = None
        self._cache = {}  # Simple response cache: {(endpoint, params_hash): (timestamp, data)}
        self._cache_ttl = int(os.getenv('WOM_CACHE_TTL', 300))  # 5 minutes default
        self._rate_limit_hits = []  # Track 429s for adaptive adjustment
        self._semaphore = None  # Will be created in async context
        self._last_request_time = 0  # Track last request globally for coordinated delays
        self._delay_lock = None  # Lock for coordinating delays

    async def _get_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        if self._delay_lock is None:
            self._delay_lock = asyncio.Lock()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_cache_key(self, endpoint, params):
        """Generate cache key from endpoint and params."""
        import json
        params_str = json.dumps(params or {}, sort_keys=True)
        return f"{endpoint}:{params_str}"
    
    def _get_cached(self, cache_key):
        """Retrieve cached response if valid."""
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            age = asyncio.get_event_loop().time() - timestamp
            if age < self._cache_ttl:
                return data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key, data):
        """Store response in cache."""
        self._cache[cache_key] = (asyncio.get_event_loop().time(), data)
    
    def _adjust_rate_limit(self):
        """Adaptively adjust rate limit based on 429 hits."""
        now = asyncio.get_event_loop().time()
        # Clean old hits (>5 minutes)
        self._rate_limit_hits = [t for t in self._rate_limit_hits if now - t < 300]
        
        if len(self._rate_limit_hits) > 3:  # Multiple 429s recently
            # Slow down: increase delay by 10% (less aggressive)
            self.rate_limit_delay = min(self.rate_limit_delay * 1.1, 5.0)  # Cap at 5s max
            self.target_rpm = int(60 / self.rate_limit_delay)
            self.logger.warning(f"Adaptive rate limit: Slowing to ~{self.target_rpm} RPM (delay={self.rate_limit_delay:.2f}s)")
        elif len(self._rate_limit_hits) == 0 and self.rate_limit_delay > 0.67:
            # Speed up: decrease delay by 10% if no recent 429s
            self.rate_limit_delay *= 0.9
            self.target_rpm = int(60 / self.rate_limit_delay)
            self.logger.info(f"Adaptive rate limit: Speeding up to ~{self.target_rpm} RPM (delay={self.rate_limit_delay:.2f}s)")

    async def _request(self, method, endpoint, data=None, params=None, use_cache=True):
        # Check cache first (for GET requests)
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached = self._get_cached(cache_key)
            if cached:
                self.logger.debug(f"[WOM API] ⚡ CACHE HIT: {endpoint}")
                return cached
        
        headers = {
            'User-Agent': self.user_agent
        }
        if self.api_key:
            headers['x-api-key'] = self.api_key

        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        # --- RPM Tracking ---
        now_time = asyncio.get_event_loop().time()
        if not hasattr(self, '_req_timestamps'): self._req_timestamps = []
        self._req_timestamps.append(now_time)
        # Clean old (>60s)
        self._req_timestamps = [t for t in self._req_timestamps if now_time - t <= 60]
        current_rpm = len(self._req_timestamps)
        
        import time
        start_t = time.perf_counter()
        self.logger.debug(f"[WOM API] ➤ {method} {endpoint} (RPM: {current_rpm}/{self.target_rpm})")
        
        # Coordinated delay + request inside lock to prevent concurrent bursts
        async with self._delay_lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
            # Make the request while holding the lock
            for attempt in range(10):
                try:
                    async with session.request(method, url, json=data, params=params, headers=headers) as response:
                        elapsed = time.perf_counter() - start_t
                        
                        if response.status == 429:
                            # Track 429 for adaptive adjustment
                            self._rate_limit_hits.append(now_time)
                            self._adjust_rate_limit()
                            
                            # Exponential backoff: 2^attempt * base_delay
                            wait_time = min((2 ** attempt) * 5.0, 60.0)  # Max 60s
                            msg = f"\n[WOM API] 🛑 RATE LIMIT HIT (429)! Waiting {wait_time:.2f}s (Attempt {attempt+1}/10)... (Time: {datetime.now().strftime('%H:%M:%S')})\n"
                            self.logger.warning(msg)
                            self.logger.warning(f"Rate limited by WOM API (Attempt {attempt+1}). Backing off {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        if response.status >= 500:
                            # Server error, exponential backoff
                            wait_time = min((2 ** attempt) * 2.0, 30.0)
                            self.logger.warning(f"WOM API Server Error {response.status}. Retrying in {wait_time}s...")
                            self.logger.warning(f"[WOM API] ⚠️ Server Error {response.status} ({elapsed:.2f}s) - Retry in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue

                        response.raise_for_status()
                        self.logger.debug(f"[WOM API] ✅ {response.status} OK ({elapsed:.2f}s)")
                        
                        result = await response.json()
                        
                        # Cache successful GET responses
                        if method == 'GET' and use_cache:
                            cache_key = self._get_cache_key(endpoint, params)
                            self._set_cache(cache_key, result)
                        
                        # Clear old 429 hits on success
                        now = asyncio.get_event_loop().time()
                        self._rate_limit_hits = [t for t in self._rate_limit_hits if now - t < 60]
                        self._last_request_time = now  # Update after successful request
                        
                        return result
                        
                except aiohttp.ClientResponseError as e:
                    if e.status < 500 and e.status != 429:
                        # Client error (4xx), do not retry
                        self.logger.error(f"WOM API Client Error: {e.status} - {e.message}")
                        raise
                    self.logger.error(f"WOM API Error (Attempt {attempt+1}): {e.status} - {e.message}")
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error (Attempt {attempt+1}): {e}")
                    # Exponential backoff for network errors
                    wait_time = min((2 ** attempt) * 1.0, 10.0)
                    await asyncio.sleep(wait_time)
        
        raise Exception(f"Max retries exceeded for WOM API: {endpoint}")

    async def fetch_paginated(self, endpoint, method='GET', params=None, limit=50, max_pages=None):
        """
        Generic pagination helper for WOM endpoints supporting offset/limit.
        Returns a generator or list of all items.
        """
        all_items = []
        offset = 0
        if params is None:
            params = {}
            
        params['limit'] = limit
        
        while True:
            params['offset'] = offset
            
            # Request
            # Note: _request logs RPM internally
            batch = await self._request(method, endpoint, params=params)
             
            if not batch:
                break
                
            all_items.extend(batch)
            
            if len(batch) < limit:
                break
                
            offset += limit
            
            # Safety break
            if max_pages and (offset / limit) > max_pages:
                break
                
        return all_items

    async def search_name_changes(self, username, status='approved', limit=5):
        """
        Searches for name changes for a specific username.
        Docs: https://docs.wiseoldman.net/api/name-changes/name-endpoints
        """
        params = {'username': username, 'status': status, 'limit': limit}
        return await self._request('GET', '/names', params=params)

    async def update_player(self, username):
        return await self._request('POST', f'/players/{username}')

    async def get_player_details(self, username):
        return await self._request('GET', f'/players/{username}')

    async def get_group_details(self, group_id):
         return await self._request('GET', f'/groups/{group_id}')

    async def update_group(self, group_id, secret_code):
        """
        Triggers an update for all members of the group.
        Docs: https://docs.wiseoldman.net/groups-api/update-all-members
        """
        data = {'verificationCode': secret_code}
        return await self._request('POST', f'/groups/{group_id}/update-all', data=data)

    async def get_group_activity(self, group_id, limit=50, offset=0):
        """
        Fetches the recent activity logs for the group.
        """
        params = {'limit': limit, 'offset': offset}
        return await self._request('GET', f'/groups/{group_id}/activity', params=params)

    async def get_group_competitions(self, group_id):
        return await self._request('GET', f'/groups/{group_id}/competitions')

    async def get_group_members(self, group_id):
        """Fetch all members of a group."""
        # Use the main group endpoint as it contains the 'memberships' list
        data = await self._request('GET', f'/groups/{group_id}')
        
        members = []
        if 'memberships' in data:
            for m in data['memberships']:
                player = m.get('player', {})
                members.append({
                    'username': player.get('username'),
                    'displayName': player.get('displayName'),
                    'role': m.get('role')
                })
        return members

    async def get_group_gains(self, group_id, period, metric, limit=50, offset=0, start_date=None, end_date=None):
        params = {
            'metric': metric,
            'limit': limit,
            'offset': offset
        }
        if period:
            params['period'] = period
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
            
        return await self._request('GET', f'/groups/{group_id}/gained', params=params)

    async def get_player_gains(self, username, period, start_date=None, end_date=None):
        params = {'period': period}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        return await self._request('GET', f'/players/{username}/gained', params=params)

# Instantiate
wom_client = WOMClient()
