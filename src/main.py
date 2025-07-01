import sys
import os
import random

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.game_engine.card import Card
from src.game_engine.deck import Deck, load_meta_decks
from src.optimizer.fitness import evaluate_fitness
from src.optimizer.genetic_algorithm import run_ga

def main():
    """Main function to run the fitness evaluation."""
    print("--- Starting Project Oracle: Fitness Evaluation ---")
    db_path = os.path.join(project_root, 'lorcana.db')

    # Load all cards and decks
    all_cards = Card.load_all_cards(db_path)
    if not all_cards:
        print("Failed to load cards. Exiting.")
        return
    print(f"Successfully loaded {len(all_cards)} cards and their abilities.")

    meta_decks = load_meta_decks(db_path, all_cards)
    if not meta_decks:
        print("Failed to load meta decks. Exiting.")
        return
    # The load_meta_decks function already prints the count

    # Run the genetic algorithm to find the best deck
    print("\n--- Starting Genetic Algorithm for Deck Optimization ---")
    best_deck = run_ga(all_cards, meta_decks, num_generations=10) # Small number of generations for a test run

    print("\n--- Genetic Algorithm Finished ---")
    print(f"Best deck found: {best_deck.name}")
    # Print card counts in the best deck
    card_counts = {}
    for card in best_deck.cards:
        card_counts[card.name] = card_counts.get(card.name, 0) + 1
    
    for card_name, count in sorted(card_counts.items()):
        print(f"  {count}x {card_name}")

if __name__ == "__main__":
    main()
