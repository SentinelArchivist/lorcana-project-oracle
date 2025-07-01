import unittest
import os
from collections import deque

# Add the src directory to the Python path to allow for absolute imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.game_engine.card import Card
from src.game_engine.player import Player
from src.game_engine.game_state import GameState
from src.game_engine.board_character import BoardCharacter
from src.game_engine.board_location import BoardLocation

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'lorcana.db')

class TestLocationTriggers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load all card data once for all tests."""
        cls.all_cards = Card.load_all_cards(DB_PATH)
        if not cls.all_cards:
            raise unittest.SkipTest("Failed to load card data. Skipping tests.")

    def setUp(self):
        """Set up a fresh game state for each test."""
        # Create dummy decks for two players
        self.player1_deck = []
        self.player2_deck = []

        self.game = GameState(self.player1_deck, self.player2_deck, self.all_cards, verbose=False)
        self.player1 = self.game.player1
        self.player2 = self.game.player2

    def test_on_banishment_at_location_trigger(self):
        """Tests if a card is drawn when a character is banished at a location with the ability."""
        print("\n--- Running Test: OnBanishmentAtLocation Trigger ---")
        # Get specific cards needed for the test
        the_library_card = next((c for c in self.all_cards.values() if c.name == "The Library - A Gift for Belle"), None)
        lilo_card = next((c for c in self.all_cards.values() if c.name == "Lilo - Making a Wish"), None)
        maui_card = next((c for c in self.all_cards.values() if c.name == "Maui - Hero to All"), None)

        self.assertIsNotNone(the_library_card, "'The Library' card not found")
        self.assertIsNotNone(lilo_card, "'Lilo' card not found")
        self.assertIsNotNone(maui_card, "'Maui' card not found")

        # 1. Setup Player 1's board
        self.player1.locations_in_play.append(BoardLocation(the_library_card, self.player1))
        the_library_location = self.player1.locations_in_play[0]

        p1_character = BoardCharacter(lilo_card, self.player1)
        p1_character.location = the_library_location # Move character to the location
        self.player1.characters_in_play.append(p1_character)

        # 2. Setup Player 2's board
        p2_character = BoardCharacter(maui_card, self.player2)
        p2_character.is_newly_played = False # Allow challenging
        self.player2.characters_in_play.append(p2_character)

        # 3. Player 1 starts with an empty hand and will draw from the ability
        self.player1.hand.clear()
        initial_hand_size = 0

        # Add a dummy card to the deck to be drawn
        dummy_card = next(iter(self.all_cards.values()))
        self.player1.deck.append(dummy_card)

        # 4. Execute the challenge
        # Exert the target so it can be challenged
        p1_character.exert()
        self.player2.challenge(p2_character, p1_character)

        # 5. Check for banishment and trigger
        self.assertTrue(p1_character.is_banished, "Player 1's character should be banished")
        self.game.check_and_banish_characters()

        # 6. Verify the outcome
        self.assertEqual(len(self.player1.characters_in_play), 0, "Player 1's character should be removed from play")
        self.assertEqual(len(self.player1.hand), initial_hand_size + 1, "Player 1 should have drawn a card from The Library's ability")
        print("SUCCESS: Player 1 drew a card after character banishment at The Library.")

if __name__ == '__main__':
    unittest.main()
