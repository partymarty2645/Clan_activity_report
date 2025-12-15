import re
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from core.utils import load_json_list, normalize_user_string
from database.connector import get_db
from database.models import DiscordMessage, WOMSnapshot

logger = logging.getLogger("Analysis")

class TextAnalyzer:
    def __init__(self):
        self.stop_words = load_json_list("stopwords.json")
        self.game_ranks = load_json_list("game_ranks.json")
        self.full_stop_list = self.stop_words.union(self.game_ranks)
        
        self.auto_announcement_triggers = [
            'received', 'completed', 'reached', 'log', 'collection', 'loot', 'burnt', 'level', 
            'maxed', 'coins', 'xp', 'kill', 'kills', 'kc', 'combat', 'achievements', 'valuable drop', 'achieved'
        ]
        self.allowed_slang = {'lol', 'gz', 'lmao', 'ty', 'haha', 'yeah', 'gzz', 'gzzz', 'tyvm'}
        
        # Bridge Pattern
        self.regex_bridge = re.compile(r"\*\*(.+?)\*\*:")

    def analyze_30d(self, target_users):
        """
        Analyzes messages from the last 30 days.
        Returns: {username: {'questions': int, 'fav_word': str}}
        target_users: list of WOM usernames (to map bridge/discord aliases to)
        """
        db = next(get_db())
        
        # 1. Blocklist names (Dynamic)
        self._load_dynamic_blocklist(db)
        
        # 2. Setup User Map
        user_map = {normalize_user_string(u): u.lower() for u in target_users}
        
        # 3. Query Messages (Last 30d)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        # Note: SQLite stores datetime as simple string usually, need to be careful with comparison
        # SQLAlchemy handles this if configured content correctly. 
        # But we'll query all and filter in python if needed or rely on index.
        
        stmt = select(DiscordMessage).where(DiscordMessage.created_at >= cutoff)
        result = db.execute(stmt)
        messages = result.scalars().all()
        
        stats = defaultdict(lambda: {'q_count': 0, 'word_counts': Counter()})
        
        for msg in messages:
            content = msg.content or ""
            author = msg.author_name or ""
            
            # Resolve User
            real_key = self._resolve_user(author, content, user_map)
            
            if real_key:
                clean_content = self._extract_clean_content(content)
                if self._is_announcement(clean_content):
                    continue
                
                # Questions
                stats[real_key]['q_count'] += clean_content.count('?')
                
                # Words
                words = self._tokenize(clean_content)
                stats[real_key]['word_counts'].update(words)
        
        # Format Results
        final_results = {}
        for u, data in stats.items():
            top = data['word_counts'].most_common(1)
            fav_word = top[0][0] if top else "N/A"
            final_results[u] = {
                'questions': data['q_count'],
                'fav_word': fav_word
            }
            
        return final_results

    def _resolve_user(self, author, content, user_map):
        # 1. Direct Author
        norm = normalize_user_string(author)
        if norm in user_map:
            return user_map[norm]
        
        # 2. Bridge
        matches = self.regex_bridge.findall(content)
        if matches:
            norm_birdge = normalize_user_string(matches[0])
            if norm_birdge in user_map:
                return user_map[norm_birdge]
        return None

    def _extract_clean_content(self, content):
        # Remove Bridge Prefix "**User**: "
        parts = content.split(':', 1)
        if len(parts) > 1 and "**" in parts[0]: 
            return parts[1].strip()
        return content

    def _is_announcement(self, text):
        t = text.lower()
        return any(trig in t for trig in self.auto_announcement_triggers)

    def _tokenize(self, text):
        # Clean Custom Emojis
        text = re.sub(r'<a?:[^:]+:\d+>', ' ', text.lower())
        # Clean Punctuation
        text = re.sub(r'[\W_]', ' ', text)
        
        words = []
        for w in text.split():
            if w.isdigit(): continue
            if w not in self.allowed_slang and (w in self.full_stop_list or len(w) < 2):
                continue
            words.append(w)
        return words

    def _load_dynamic_blocklist(self, db):
        try:
            # Block Discord Names
            d_names = db.execute(select(DiscordMessage.author_name).distinct()).scalars().all()
            # Block WOM Names
            w_names = db.execute(select(WOMSnapshot.username).distinct()).scalars().all()
            
            all_names = set(d_names + w_names)
            for n in all_names:
                if not n: continue
                norm = n.lower()
                self.full_stop_list.add(norm)
                # Split parts "party_marty" -> "party", "marty"
                parts = re.split(r'[\W_]', norm)
                for p in parts:
                    if len(p) > 2: self.full_stop_list.add(p)
        except Exception as e:
            logger.error(f"Failed to load dynamic blocklist: {e}")

analyzer = TextAnalyzer()
