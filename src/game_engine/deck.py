import sqlite3
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.card import Card

class Deck:
    """Represents a deck of cards."""
    def __init__(self, name, cards, source_url=None):
        self.name = name
        self.cards = cards  # List of Card objects
        self.source_url = source_url

    def __repr__(self):
        return f"Deck(name='{self.name}', card_count={len(self.cards)})"

def load_meta_decks(db_path, all_cards_map):
    """Loads all metagame decks from the database."""
    meta_decks = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all decks from the Decks table
        cursor.execute("SELECT id, name, source_url FROM Decks")
        deck_rows = cursor.fetchall()

        for deck_row in deck_rows:
            deck_id, deck_name, source_url = deck_row
            
            # For each deck, get its card list from Deck_Cards
            cursor.execute("""
                SELECT c.api_id, dc.quantity 
                FROM Deck_Cards dc
                JOIN Cards c ON dc.card_id = c.id
                WHERE dc.deck_id = ?
            """, (deck_id,))
            
            card_rows = cursor.fetchall()
            
            deck_cards = []
            for api_id, quantity in card_rows:
                if api_id in all_cards_map:
                    # Add the card 'quantity' times
                    deck_cards.extend([all_cards_map[api_id]] * quantity)
            
            if deck_cards:
                deck = Deck(name=deck_name, cards=deck_cards, source_url=source_url)
                meta_decks.append(deck)

        conn.close()
        print(f"Successfully loaded {len(meta_decks)} meta decks.")
        return meta_decks

    except sqlite3.Error as e:
        print(f"Database error while loading meta decks: {e}")
        return []
