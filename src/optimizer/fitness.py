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

    # GameState constructor expects deck_cards lists, not Player objects, and also the all_cards map.
    game = GameState(
        player1_deck=candidate_deck_cards, 
        player2_deck=meta_deck_cards, 
        all_cards=worker_all_cards_map, 
        verbose=False
    )
    game.run_simulation()
    
    # The winner is one of the Player objects created inside the GameState instance.
    return (meta_deck_name, 1 if game.winner == game.player1 else 0)

def calculate_fitness(candidate_deck_cards, meta_decks, all_cards_map, detailed_report=False):
    """
    Calculates the fitness of a candidate deck by simulating games against a meta in parallel.
    The fitness score is the overall win percentage, adjusted for deck consistency.

    Args:
        candidate_deck_cards (list): A list of Card objects for the candidate deck.
        meta_decks (list): A list of Deck objects representing the meta.
        all_cards_map (dict): A map of all card API IDs to Card objects.
        detailed_report (bool): If True, returns a dictionary with detailed stats. 
                                Otherwise, returns a single float fitness score.

    Returns:
        float or dict: The fitness score or a dictionary with detailed results.
    """
    # Convert card objects to simple IDs for serialization
    candidate_deck_ids = [card.api_id for card in candidate_deck_cards]
    
    # Prepare arguments for multiprocessing
    tasks = []
    for meta_deck in meta_decks:
        meta_deck_ids = [card.api_id for card in meta_deck.cards]
        for _ in range(GAMES_PER_MATCHUP):
            tasks.append((candidate_deck_ids, meta_deck_ids, meta_deck.name))

    # Run simulations in parallel
    results = []
    # Disable tqdm for non-detailed reports to speed up GA runs, and use the faster pool.map
    use_tqdm = detailed_report 
    with Pool(processes=cpu_count(), initializer=init_worker, initargs=(all_cards_map,)) as pool:
        if use_tqdm:
            results = list(tqdm(pool.imap(run_single_game, tasks), total=len(tasks), desc="  Simulating Final Games", leave=False, ncols=100))
        else:
            # Using map is faster when we don't need a progress bar
            results = pool.map(run_single_game, tasks)

    total_wins = sum(win for _, win in results)
    total_games = len(results)

    raw_win_rate = (total_wins / total_games) if total_games > 0 else 0
    
    # --- Consistency Score Calculation ---
    card_counts = Counter(card.name for card in candidate_deck_cards)
    
    c4_cards = sum(4 for count in card_counts.values() if count == 4)
    c3_cards = sum(3 for count in card_counts.values() if count == 3)
    c2_cards = sum(2 for count in card_counts.values() if count == 2)
    c1_cards = sum(1 for count in card_counts.values() if count == 1)

    consistency_score = (1.0 * c4_cards + 0.8 * c3_cards + 0.6 * c2_cards + 0.3 * c1_cards) / 60.0
    consistency_score = max(0.0, min(consistency_score, 1.0))

    final_fitness = raw_win_rate * consistency_score
    
    if detailed_report:
        win_counts = Counter()
        games_played = Counter()
        for meta_deck_name, win in results:
            games_played[meta_deck_name] += 1
            if win:
                win_counts[meta_deck_name] += 1

        win_rates_by_meta_deck = {
            name: (win_counts[name] / games_played[name]) if games_played[name] > 0 else 0
            for name in games_played
        }
        
        return {
            "final_fitness": final_fitness,
            "raw_win_rate": raw_win_rate,
            "consistency_score": consistency_score,
            "win_rates_by_meta_deck": win_rates_by_meta_deck
        }
    
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

        fitness_details = calculate_fitness(candidate_deck_cards, meta_decks, all_cards_map, detailed_report=True)
        print(f"\nCalculated Fitness: {fitness_details['final_fitness']:.4f}")
        print(f"  - Raw Win Rate: {fitness_details['raw_win_rate']:.2%}")
        print(f"  - Consistency Score: {fitness_details['consistency_score']:.2%}")
        print("  - Win Rates vs Meta:")
        for deck, rate in fitness_details['win_rates_by_meta_deck'].items():
            print(f"    - {deck}: {rate:.2%}")
    else:
        print("Could not load cards or meta decks. Fitness calculation aborted.")
