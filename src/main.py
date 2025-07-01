import sys
from .ui.main_app import main as run_ui

def main():
    """Main function to run the application."""
    # The application now runs the GUI by default.
    run_ui()

# def run_cli_optimizer():
#     """Original command-line function to run the fitness evaluation."""
#     print("--- Starting Project Oracle: Fitness Evaluation ---")
#     db_path = os.path.join(project_root, 'lorcana.db')
#
#     # Load all cards and decks
#     all_cards = Card.load_all_cards(db_path)
#     if not all_cards:
#         print("Failed to load cards. Exiting.")
#         return
#     print(f"Successfully loaded {len(all_cards)} cards and their abilities.")
#
#     meta_decks = load_meta_decks(db_path, all_cards)
#     if not meta_decks:
#         print("Failed to load meta decks. Exiting.")
#         return
#
#     # Run the genetic algorithm to find the best deck
#     print("\n--- Starting Genetic Algorithm for Deck Optimization ---")
#     best_deck = run_ga(all_cards, meta_decks, num_generations=10)
#
#     print("\n--- Genetic Algorithm Finished ---")
#     print(f"Best deck found: {best_deck.name}")
#     card_counts = {}
#     for card in best_deck.cards:
#         card_counts[card.name] = card_counts.get(card.name, 0) + 1
#
#     for card_name, count in sorted(card_counts.items()):
#         print(f"  {count}x {card_name}")

if __name__ == "__main__":
    main()
