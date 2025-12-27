import random
import logging

logger = logging.getLogger(__name__)

class AIInsightGenerator:
    def __init__(self, members):
        """
        members: list of dicts containing player stats
        """
        self.members = members
        self.pool = []

    def generate_all(self):
        """Run all generator methods to populate the pool."""
        self.pool = []
        
        # Generator registry
        generators = [
            self.gen_xp_milestones,
            self.gen_boss_milestones,
            self.gen_ratios,
            self.gen_activity_streaks,
            self.gen_outliers,
            self.gen_clan_wide,
            self.gen_boss_specifics,
            self.gen_fun_trivia,
            self.gen_rookie_watch,
            self.gen_fallbacks # Ensure we always have content
        ]
        
        for gen in generators:
            try:
                insights = gen()
                if insights:
                    self.pool.extend(insights)
            except Exception as e:
                logger.error(f"Error in {gen.__name__}: {e}")
        
        # Post-Process: Assign Images
        for card in self.pool:
            if 'image' not in card:
                card['image'] = self._get_image_for_card(card.get('title', ''), card.get('message', ''), card.get('type', ''))

        # Post-Process: Validate
        self.pool = [c for c in self.pool if self._validate_card(c)]
                
        # Shuffle for randomness
        random.shuffle(self.pool)
        return self.pool

    def get_selection(self, count=9):
        """Get a random selection of unique insights."""
        if not self.pool:
            self.generate_all()
            
        # Deduplicate titles/messages slightly to avoid repetition? 
        # For now, just take top N after shuffle.
        return self.pool[:count]

    def _fmt(self, num):
        if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
        if num >= 1_000: return f"{num/1_000:.1f}k"
        return str(num)
        
    def _validate_card(self, card):
        required = ["type", "title", "message", "icon", "image"]
        return all(key in card and isinstance(card[key], str) for key in required)

    def _get_image_for_card(self, title, message, card_type):
        """
        Intelligently assigns an asset image based on text content.
        """
        text = (title + " " + message).lower()
        
        # 1. Bosses (Simple heuristic match)
        known_bosses = [
            "cox", "tob", "toa", "zulrah", "vorkath", "hydra", "muspah", "nex", "nightmare", 
            "corporeal beast", "jad", "zuk", "barrows", "gw", "gauntlet", "cg", "leviathan", 
            "whisperer", "vardorvis", "duke", "scurrius", "moons", "araxxor", "hueycoatl",
            "calvarion", "venenatis", "vet'ion", "callisto", "chaos elemental", "chaos fanatic",
            "crazy archaeologist", "scorpia", "wintertodt", "tempoross", "zalcano", "mole",
            "sarachnis", "kbd", "thermy", "cerberus", "sire", "kraken", "smoke devil"
        ]
        
        # Map common aliases to filenames
        boss_map = {
            "cox": "chambers_of_xeric.png",
            "tob": "theatre_of_blood.png",
            "toa": "tombs_of_amascut.png",
            "gw": "god_wars_dungeon.png",
            "cg": "the_corrupted_gauntlet.png",
            "gauntlet": "the_gauntlet.png",
            "jad": "tztok_jad.png",
            "zuk": "tzkal_zuk.png"
        }

        for boss in known_bosses:
            if boss in text:
                img = boss_map.get(boss)
                if not img:
                    # Try to form standard filename: boss_name.png
                    img = f"boss_{boss.replace(' ', '_')}.png"
                return img

        # 2. Skills
        skills = [
            "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic", "cooking", 
            "woodcutting", "fletching", "fishing", "firemaking", "crafting", "smithing", "mining", 
            "herblore", "agility", "thieving", "slayer", "farming", "runecrafting", "hunter", 
            "construction", "sailing"
        ]
        for skill in skills:
            if skill in text:
                return f"skill_{skill}.png"

        # 3. Ranks / Roles
        roles = ["owner", "deputy", "admin", "moderator", "advisor", "captain", "recruiter", 
                 "cleric", "prophet", "scout", "fighter", "ranger", "magician", "artisan", "novice"]
        for role in roles:
            if role in text:
                return f"rank_{role}.png"
        
        # 4. Fallbacks by Type
        if card_type == 'fun':
            return "boss_pet_rock.png"
        elif card_type in ['milestone', 'achievement']:
            return "rank_legend.png"
        elif card_type == 'outlier':
            return "rank_dragon.png"
        elif card_type == 'forecast':
            return "rank_oracle.png"
            
        return "rank_minion.png"

    # --- GENERATORS ---

    def gen_fallbacks(self):
        """Always provide some generic content if pool is low."""
        insights = []
        # Only add if we suspect we might be short, or just add them as filler.
        
        facts = [
            "Did you know? The Clan Stats system tracks over 50 data points per member.",
            "Tip: Check the 'Outliers' tab to see who is carrying the clan.",
            "System: Data is refreshed automatically after every harvest cycle.",
            "Community: Join the Discord voice channels for live bossing events!"
        ]
        
        for f in facts:
            insights.append({
                "type": "system",
                "title": "Clan Fact",
                "message": f"ℹ️ {f}",
                "icon": "fa-info-circle"
            })
            
        if self.members:
            insights.append({
                "type": "system",
                "title": "Member Count",
                "message": f"👥 We are currently {len(self.members)} members strong.",
                "icon": "fa-users"
            })
            
        return insights

    def gen_xp_milestones(self):
        """Check for users crossing simple numeric thresholds."""
        insights = []
        benchmarks = [10_000_000, 25_000_000, 50_000_000, 100_000_000, 200_000_000, 500_000_000, 1_000_000_000]
        
        for m in self.members:
            curr = m.get('total_xp', 0)
            gain = m.get('xp_7d', 0)
            if gain <= 0: continue
            
            start = curr - gain
            for b in benchmarks:
                if start < b <= curr:
                    insights.append({
                        "type": "milestone",
                        "title": "XP Milestone",
                        "message": f"🎉 {m['username']} just crossed {self._fmt(b)} Total XP!",
                        "icon": "fa-medal"
                    })
        return insights

    def gen_boss_milestones(self):
        insights = []
        benchmarks = [500, 1000, 2500, 5000, 10000, 25000]
        
        for m in self.members:
            curr = m.get('total_boss', 0)
            gain = m.get('boss_7d', 0)
            if gain <= 0: continue
            
            start = curr - gain
            for b in benchmarks:
                if start < b <= curr:
                    insights.append({
                        "type": "milestone",
                        "title": "Boss Kills Milestone",
                        "message": f"⚔️ {m['username']} has slain over {self._fmt(b)} bosses!",
                        "icon": "fa-skull-crossbones"
                    })
        return insights

    def gen_forecasts(self):
        """Predicts future milestones based on current velocity."""
        insights = []
        milestones = [10_000_000, 25_000_000, 50_000_000, 100_000_000, 200_000_000, 500_000_000, 1_000_000_000]
        
        for m in self.members:
            xp_7d = m.get('xp_7d', 0)
            if xp_7d <= 0: continue
            
            # Daily velocity
            xp_per_day = xp_7d / 7
            current_xp = m.get('total_xp', 0)
            
            # Find next milestone
            next_milestone = None
            for ms in milestones:
                if current_xp < ms:
                    next_milestone = ms
                    break
            
            if next_milestone:
                needed = next_milestone - current_xp
                days = needed / xp_per_day
                
                if days < 7: # Imminent (within a week)
                     insights.append({
                        "type": "forecast",
                        "title": "Milestone Forecast",
                        "message": f"🔮 At this rate, {m['username']} will hit {self._fmt(next_milestone)} XP in {int(days) + 1} days.",
                        "icon": "fa-crystal-ball"
                    })
        return insights

    def gen_ratios(self):
        """Efficiency metrics."""
        insights = []
        # Efficiency Expert (High XP / Msg)
        talkers = [m for m in self.members if m.get('msgs_7d', 0) > 20]
        if talkers:
            top = max(talkers, key=lambda x: x['xp_7d']/(x['msgs_7d'] or 1))
            ratio = top['xp_7d']/top['msgs_7d']
            insights.append({
                "type": "analysis",
                "title": "Efficiency Expert",
                "message": f"🧠 {top['username']} gains {int(ratio/1000)}k XP for every message sent.",
                "icon": "fa-brain"
            })
            
        # Combat Focus (Boss / XP ratio) - who bosses without skilling?
        bossers = [m for m in self.members if m.get('boss_7d', 0) > 20]
        if bossers:
            top = max(bossers, key=lambda x: x['boss_7d']/(x['xp_7d'] or 1)) # Be careful of 0 XP
            insights.append({
                "type": "trend",
                "title": "Combat Function Only",
                "message": f"⚔️ {top['username']} is purely combat focused this week.",
                "icon": "fa-fist-raised"
            })
        return insights

    def gen_activity_streaks(self):
        insights = []
        # High activity 30d
        active = [m for m in self.members if m.get('msgs_30d', 0) > 500]
        if active:
            # Pick a random one if multiple
            u = random.choice(active)
            insights.append({
                "type": "health",
                "title": "Social Butterfly",
                "message": f"🦋 {u['username']} is carrying the chat with {u['msgs_30d']} msgs this month.",
                "icon": "fa-comments"
            })
            
        # Silent Grinder
        silent = [m for m in self.members if m.get('msgs_7d', 0) == 0 and m.get('xp_7d', 0) > 1_000_000]
        if silent:
            u = random.choice(silent)
            insights.append({
                "type": "analysis",
                "title": "Silent but Deadly",
                "message": f"🤫 {u['username']} gained {self._fmt(u['xp_7d'])} XP in total silence.",
                "icon": "fa-ghost"
            })
        return insights

    def gen_outliers(self):
        insights = []
        if not self.members: return []

        # XP Variance
        # Let's do: "Top Gainer" absolute
        top_xp = max(self.members, key=lambda x: x.get('xp_7d', 0))
        if top_xp.get('xp_7d', 0) > 2_000_000:
            insights.append({
                "type": "trend",
                "title": "Weekly Top Gainer",
                "message": f"🚀 {top_xp['username']} is rocketing up with {self._fmt(top_xp['xp_7d'])} XP.",
                "icon": "fa-arrow-up"
            })
            
        top_boss = max(self.members, key=lambda x: x.get('boss_7d', 0))
        if top_boss.get('boss_7d', 0) > 50:
            insights.append({
                "type": "trend",
                "title": "Boss Slayer",
                "message": f"👹 {top_boss['username']} ended {top_boss['boss_7d']} boss lives this week.",
                "icon": "fa-skull"
            })
        return insights
    
    def gen_clan_wide(self):
        insights = []
        if not self.members: return []
        
        total_xp = sum(m.get('xp_7d', 0) for m in self.members)
        if total_xp > 50_000_000:
            insights.append({
                "type": "milestone",
                "title": "Clan Velocity",
                "message": f"🌍 The clan gained {self._fmt(total_xp)} XP collectively this week.",
                "icon": "fa-globe"
            })
            
        total_kills = sum(m.get('boss_7d', 0) for m in self.members)
        if total_kills > 500:
            insights.append({
                "type": "milestone",
                "title": "Mass Extinction",
                "message": f"☠️ We killed {total_kills} bosses as a group this week.",
                "icon": "fa-users"
            })
        return insights
        
    def gen_boss_specifics(self):
        """Attempts to look at favorite bosses."""
        insights = []
        # Group by fav boss
        fav_counts = {}
        for m in self.members:
            fav = m.get('favorite_boss')
            if fav and fav != 'None':
                fav_counts[fav] = fav_counts.get(fav, 0) + 1
                # Individual shoutout
                if m.get('boss_7d', 0) > 20: # If active bosser
                    insights.append({
                        "type": "analysis",
                        "title": f"{(fav or 'Boss').title()} Expert",
                        "message": f"🎯 {m['username']} is focusing hard on {fav}.",
                        "icon": "fa-crosshairs"
                    })

        # Most popular fav boss
        if fav_counts:
            popular = max(fav_counts, key=fav_counts.get)
            if fav_counts[popular] > 2:
                insights.append({
                    "type": "trend",
                    "title": "Crowd Favorite",
                    "message": f"❤️ {popular} is the current favorite boss of {fav_counts[popular]} members.",
                    "icon": "fa-heart"
                })
        return insights
        
    def gen_fun_trivia(self):
        insights = []
        if not self.members: return []

        # Longest Name
        longest = max(self.members, key=lambda x: len(x['username']))
        insights.append({
            "type": "fun",
            "title": "Alphabet Hoarder",
            "message": f"🔤 {longest['username']} has the longest name in the clan.",
            "icon": "fa-font"
        })
        
        # Newest Member
        newest = min(self.members, key=lambda x: x.get('days_in_clan', 9999))
        if newest['days_in_clan'] < 7:
            insights.append({
                "type": "fun",
                "title": "Fresh Meat",
                "message": f"👶 {newest['username']} is our newest member ({newest['days_in_clan']} days). Say hi!",
                "icon": "fa-baby-carriage"
            })
            
        # Oldest Member (Veterans)
        oldest = max(self.members, key=lambda x: x.get('days_in_clan', 0))
        if oldest['days_in_clan'] > 365:
            insights.append({
                "type": "fun",
                "title": "The Ancient One",
                "message": f"👴 {oldest['username']} has been here for {oldest['days_in_clan']} days.",
                "icon": "fa-scroll"
            })
        return insights
        
    def gen_rookie_watch(self):
        insights = []
        # Rookies (< 30 days) with high gains
        rookies = [m for m in self.members if m.get('days_in_clan', 99) < 30]
        for r in rookies:
            if r.get('xp_7d', 0) > 1_000_000:
                insights.append({
                    "type": "trend",
                    "title": "Rising Star",
                    "message": f"⭐ Rookie {r['username']} is smashing it with {self._fmt(r['xp_7d'])} XP.",
                    "icon": "fa-star"
                })
        return insights
