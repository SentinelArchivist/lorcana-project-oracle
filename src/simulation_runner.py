import sqlite3
import os
from collections import defaultdict

from .game_engine.card import Card
from .game_engine.player import Player
from .game_engine.game_state import GameState

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'lorcana.db')

def get_deck_ids():
    """Fetches all deck IDs from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Decks ORDER BY RANDOM() LIMIT 2")
        decks = cursor.fetchall()
        conn.close()
        if len(decks) < 2:
            print("Error: Not enough decks in the database to run a simulation.")
            return None, None
        return decks[0], decks[1]
    except sqlite3.Error as e:
        print(f"Database error while fetching deck IDs: {e}")
        return None, None

def get_deck_by_name(deck_name):
    """Fetches a single deck's info from the database by name."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Decks WHERE name = ?", (deck_name,))
        deck = cursor.fetchone()
        conn.close()
        if not deck:
            print(f"Error: Deck with name '{deck_name}' not found.")
            return None
        return deck
    except sqlite3.Error as e:
        print(f"Database error while fetching deck by name: {e}")
        return None

def load_deck(deck_id, all_cards_map):
    """Loads a single deck from the database given a deck_id."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.api_id, dc.quantity
            FROM Deck_Cards dc
            JOIN Cards c ON dc.card_id = c.id
            WHERE dc.deck_id = ?
        """, (deck_id,))
        deck_data = cursor.fetchall()
        conn.close()

        deck_list = []
        for api_id, quantity in deck_data:
            card = all_cards_map.get(api_id)
            if card:
                deck_list.extend([card] * quantity)
            else:
                print(f"Warning: Card with api_id {api_id} not found in all_cards_map.")
        
        return deck_list
    except sqlite3.Error as e:
        print(f"Database error while loading deck {deck_id}: {e}")
        return []

def main():
    """Main function to set up and run a batch of game simulations."""
    print("--- Project Oracle: Simulation Runner ---")

    # 1. Load all cards from the database
    all_cards = Card.load_all_cards(DB_PATH)
    if not all_cards:
        print("Failed to load card data. Exiting.")
        return

    # 2. Get two specific decks from the database that have locations
    deck1_info = get_deck_by_name("Aggressive Hamster")
    deck2_info = get_deck_by_name("Ruby Sapphire")
    if not deck1_info or not deck2_info:
        return
    
    deck1_id, deck1_name = deck1_info
    deck2_id, deck2_name = deck2_info
    print(f"Player 1 will be using: {deck1_name}")
    print(f"Player 2 will be using: {deck2_name}")

    # 3. Load the card lists for each deck
    deck1_cards = load_deck(deck1_id, all_cards)
    deck2_cards = load_deck(deck2_id, all_cards)

    if len(deck1_cards) < 60 or len(deck2_cards) < 60:
        print("One or both decks have fewer than 60 cards. Simulation cannot proceed.")
        return

    # 4. Run a series of simulations to gather statistics
    num_simulations = 20
    win_counts = defaultdict(int)

    print(f"\n--- Running {num_simulations} Simulations ---")

    # Run a single verbose simulation for debugging
    print("\n--- Running 1 Verbose Simulation for Debugging ---")
    game = GameState(deck1_cards, deck2_cards, all_cards, verbose=True)
    winner = game.run_simulation()
    if winner:
        winner_name = deck1_name if winner.name == 'Player 1' else deck2_name
        print(f"--- Verbose Simulation Winner: {winner_name} ---")

    print(f"\n--- Running {num_simulations} Batch Simulations ---")
    for i in range(num_simulations):
        # Create a new GameState for each simulation to ensure they are independent
        game = GameState(deck1_cards, deck2_cards, all_cards, verbose=False)
        winner = game.run_simulation()
        if winner:
            # The winner object is a Player instance. We need to map it back to the deck name.
            if winner.name == 'Player 1':
                win_counts[deck1_name] += 1
            else:
                win_counts[deck2_name] += 1
        else:
            win_counts["Draw"] += 1
        
        # Print progress
        print(f"  Completed simulation {i + 1}/{num_simulations}...")

    # 5. Print the results
    print("\n--- Simulation Results ---")
    print(f"Total simulations: {num_simulations}")
    for deck_name, wins in win_counts.items():
        win_percentage = (wins / num_simulations) * 100
        print(f"  - {deck_name}: {wins} wins ({win_percentage:.2f}%)")

if __name__ == '__main__':
    main()
