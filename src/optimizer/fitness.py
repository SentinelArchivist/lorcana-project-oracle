import sys
import os
from collections import Counter
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import configparser

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.game_state import GameState
from game_engine.player import Player

config = configparser.ConfigParser()
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
config.read(config_path)

sim_config = config['simulation']
GAMES_PER_MATCHUP = sim_config.getint('games_per_matchup', 20)

# --- Worker Setup for Multiprocessing ---
worker_all_cards_map = None

def init_worker(all_cards_map_data):
    """Initializes the worker process with the global card map."""
    global worker_all_cards_map
    worker_all_cards_map = all_cards_map_data

def run_single_game(args):
    """Worker function for multiprocessing. Runs a single game simulation."""
    candidate_deck_ids, meta_deck_ids, meta_deck_name = args
    
    # Reconstruct card lists from IDs using the worker's global map
    candidate_deck_cards = [worker_all_cards_map[api_id] for api_id in candidate_deck_ids]
    meta_deck_cards = [worker_all_cards_map[api_id] for api_id in meta_deck_ids]

    player1 = Player(name="Candidate Deck", deck_cards=candidate_deck_cards)
    player2 = Player(name=meta_deck_name, deck_cards=meta_deck_cards)
    game = GameState(player1, player2, verbose=False) # Turn off verbose logging in workers
    game.run_simulation()
    return (meta_deck_name, 1 if game.winner == player1 else 0)

def calculate_fitness(candidate_deck_cards, meta_decks, all_cards_map):
    """
    Calculates the fitness of a candidate deck by simulating games against a meta in parallel.
    The fitness score is the overall win percentage, adjusted for deck consistency.
    """
    # Convert card objects to simple IDs for serialization
    candidate_deck_ids = [card.api_id for card in candidate_deck_cards]
    
    # Prepare arguments for multiprocessing
    tasks = []
    for meta_deck in meta_decks:
        meta_deck_ids = [card.api_id for card in meta_deck.cards]
        for _ in range(GAMES_PER_MATCHUP):
            tasks.append((candidate_deck_ids, meta_deck_ids, meta_deck.name))

    # Run simulations in parallel with a progress bar
    results = []
    with Pool(processes=cpu_count(), initializer=init_worker, initargs=(all_cards_map,)) as pool:
        # Using imap to get results as they are completed, which works well with tqdm
        results = list(tqdm(pool.imap(run_single_game, tasks), total=len(tasks), desc="  Simulating Games", leave=False, ncols=100))

    total_wins = sum(win for _, win in results)
    total_games = len(results)

    raw_win_rate = (total_wins / total_games) if total_games > 0 else 0
    
    # --- New Consistency Score Calculation as per specification ---
    card_counts = Counter(card.name for card in candidate_deck_cards)
    
    c4_cards = sum(4 for count in card_counts.values() if count == 4)
    c3_cards = sum(3 for count in card_counts.values() if count == 3)
    c2_cards = sum(2 for count in card_counts.values() if count == 2)
    c1_cards = sum(1 for count in card_counts.values() if count == 1)

    # Formula: Consistency Score = (1.0 * c4 + 0.8 * c3 + 0.6 * c2 + 0.3 * c1) / 60
    consistency_score = (1.0 * c4_cards + 0.8 * c3_cards + 0.6 * c2_cards + 0.3 * c1_cards) / 60.0
    
    # Ensure consistency score is between 0.0 and 1.0
    consistency_score = max(0.0, min(consistency_score, 1.0))

    final_fitness = raw_win_rate * consistency_score
    
    # This function is called for every individual in the population,
    # so we should avoid printing too much. The GA main loop will print the best fitness.
    
    return final_fitness

if __name__ == '__main__':
    # Example of how to use the fitness calculator
    from optimizer.deck_generator import generate_population
    from game_engine.card import Card
    from game_engine.deck import load_meta_decks

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db'))
    all_cards_map = Card.load_all_cards(db_path)
    meta_decks = load_meta_decks(db_path, all_cards_map)

    if all_cards_map and meta_decks:
        # Generate one random deck to test
        print("\n--- Running Standalone Fitness Calculation Example ---")
        candidate_deck_cards = generate_population(1, all_cards_map)[0]
        
        print("\nGenerated Candidate Deck:")
        for name, count in Counter(c.name for c in candidate_deck_cards).items():
            print(f"  {count}x {name}")

        fitness = calculate_fitness(candidate_deck_cards, meta_decks, all_cards_map)
        print(f"\nCalculated Fitness: {fitness:.4f}")
    else:
        print("Could not load cards or meta decks. Fitness calculation aborted.")
