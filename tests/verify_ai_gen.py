
import unittest
import sys
import os
import random

# Add project root to path
sys.path.append(os.getcwd())

from core.ai_concepts import AIInsightGenerator

class TestAIHelper(unittest.TestCase):
    def setUp(self):
        # Mock Members Data
        self.mock_members = [
             {
                "username": "PlayerOne", "role": "Owner", "xp_7d": 15000000, "boss_7d": 50, 
                "total_xp": 200000000, "total_boss": 5000, "days_in_clan": 400,
                "msgs_7d": 500, "msgs_30d": 2000
            },
            {
                "username": "Nooblet", "role": "Minion", "xp_7d": 200, "boss_7d": 0, 
                "total_xp": 50000, "total_boss": 0, "days_in_clan": 5,
                "msgs_7d": 10, "msgs_30d": 10
            },
            {
                "username": "SilentKiller", "role": "General", "xp_7d": 5000000, "boss_7d": 200, 
                "total_xp": 150000000, "total_boss": 2500, "days_in_clan": 600,
                "msgs_7d": 0, "msgs_30d": 0
            }
        ]
        
    def test_generator_runs_without_crash(self):
        """Ensure generate_all runs without errors."""
        gen = AIInsightGenerator(self.mock_members)
        insights = gen.generate_all()
        self.assertIsInstance(insights, list)
        
    def test_structure(self):
        """Ensure all generated items have required keys."""
        gen = AIInsightGenerator(self.mock_members)
        insights = gen.generate_all()
        
        required_keys = ["type", "title", "message", "icon", "image"]
        for i, card in enumerate(insights):
            for key in required_keys:
                self.assertIn(key, card, f"Card {i} missing key: {key}")
                self.assertIsInstance(card[key], str, f"Card {i} key {key} is not string")
            
            # Additional check for image
            if card['image']:
                self.assertTrue(card['image'].endswith('.png'), f"Image {card['image']} not numeric or invalid format")
                
    def test_empty_input(self):
        """Ensure generator handles empty lists gracefully."""
        gen = AIInsightGenerator([])
        base_insights = gen.generate_all() # Should ideally produce some generic clan ones or empty
        
        # We expect at least NO crash. returning empty list is fine for now.
        self.assertIsInstance(base_insights, list)

    def test_forecasts(self):
        """Ensure forecasts are generated for high velocity users."""
        gen = AIInsightGenerator(self.mock_members)
        # Mock high XP gain for PlayerOne to trigger forecast
        # Set total XP to 490M (Close to 500M milestone)
        self.mock_members[0]['total_xp'] = 490_000_000
        # Set XP/week to 20M (approx 2.8M/day)
        # Needed: 10M. Days = 10 / 2.8 = ~3.5 days.
        self.mock_members[0]['xp_7d'] = 20_000_000
        
        insights = gen.gen_forecasts()
        self.assertTrue(len(insights) > 0, "Should have generated a forecast")
        self.assertEqual(insights[0]['type'], 'forecast')

    def test_selection_limits(self):
        gen = AIInsightGenerator(self.mock_members)
        selection = gen.get_selection(count=2)
        self.assertLessEqual(len(selection), 2)
        
if __name__ == '__main__':
    unittest.main()
