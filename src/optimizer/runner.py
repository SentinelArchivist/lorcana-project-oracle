import pygad
import random
import os
import sys
import numpy as np
from collections import Counter
import configparser

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.card import Card
from game_engine.deck import load_meta_decks
from optimizer.fitness import calculate_fitness
from optimizer.deck_generator import generate_population, INK_COLORS

# --- Global Variables for GA --- 
all_cards_map = None
meta_decks = None
api_id_to_idx = {}
idx_to_api_id = {}

def get_deck_inks(deck_cards):
    """Identifies the two primary ink colors in a deck."""
    inks = {card.color for card in deck_cards if card.color is not None}
    return list(inks)

def is_deck_valid(deck_cards):
    """Checks if a deck is valid (60 cards, <= 2 inks)."""
    if len(deck_cards) != 60:
        return False
    inks = {card.color for card in deck_cards if card.color is not None}
    if len(inks) > 2:
        return False
    return True

def fitness_func(ga_instance, solution, solution_idx):
    """Fitness function wrapper for PyGAD."""
    candidate_deck_cards = [all_cards_map[idx_to_api_id[idx]] for idx in solution]
    
    # Failsafe: if the solution is invalid, return a very low fitness
    if not is_deck_valid(candidate_deck_cards):
        return -999

    # Use a lower number of games for faster iteration during evolution
    calculate_fitness.GAMES_PER_MATCHUP = 5 
    
    # Pass the global all_cards_map to the fitness function for worker initialization
    fitness = calculate_fitness(candidate_deck_cards, meta_decks, all_cards_map)
    return fitness

def on_crossover(parents, offspring_size, ga_instance):
    """    Performs crossover, creating a blend of two parents. 
    Crucially, it ensures all offspring are valid before returning them.
    """
    offspring = []
    idx = 0
    while len(offspring) < offspring_size[0]:
        parent1_solution = parents[idx % len(parents)]
        parent2_solution = parents[(idx + 1) % len(parents)]
        idx += 1

        parent1_cards = [all_cards_map[idx_to_api_id[gene]] for gene in parent1_solution]
        parent2_cards = [all_cards_map[idx_to_api_id[gene]] for gene in parent2_solution]

        offspring_inks = get_deck_inks(parent1_cards)
        if len(offspring_inks) > 2: offspring_inks = random.sample(offspring_inks, 2)
        if not offspring_inks: offspring_inks = random.sample(INK_COLORS, 2)

        combined_pool = [card for card in parent1_cards + parent2_cards if card.color in offspring_inks or card.color is None]
        random.shuffle(combined_pool)
        
        offspring_deck = []
        card_counts = Counter()
        for card in combined_pool:
            if len(offspring_deck) >= 60: break
            if card_counts[card.name] < 4:
                offspring_deck.append(card)
                card_counts[card.name] += 1

        # Backfill and trim to ensure exactly 60 cards
        valid_fill_pool = [c for c in all_cards_map.values() if c.color in offspring_inks or c.color is None]
        while len(offspring_deck) < 60:
            candidate = random.choice(valid_fill_pool)
            if card_counts[candidate.name] < 4:
                offspring_deck.append(candidate)
                card_counts[candidate.name] += 1
        while len(offspring_deck) > 60:
            offspring_deck.pop(random.randrange(len(offspring_deck)))

        # CRITICAL VALIDATION STEP
        if is_deck_valid(offspring_deck):
            new_solution = [api_id_to_idx[c.api_id] for c in offspring_deck]
            offspring.append(new_solution)
        # If not valid, the loop continues and a new offspring is generated from the next parents.

    return np.array(offspring)

def get_valid_card_pool(deck_cards):
    """Helper function to get a pool of cards with the same ink colors as the deck."""
    inks = get_deck_inks(deck_cards)
    if not inks: inks = random.sample(INK_COLORS, 2)
    return [card for card in all_cards_map.values() if card.color in inks or card.color is None]

def on_mutation(offspring, ga_instance):
    """    Performs structurally-aware mutation on offspring, ensuring they remain valid.
    If a mutation results in an invalid deck, the change is reverted.
    """
    mutated_offspring = []
    for solution in offspring:
        original_deck_cards = [all_cards_map[idx_to_api_id[gene]] for gene in solution]
        
        # If the deck is somehow invalid before mutation, don't touch it
        if not is_deck_valid(original_deck_cards):
            mutated_offspring.append(solution)
            continue

        deck_cards = original_deck_cards.copy()
        valid_pool = get_valid_card_pool(deck_cards)
        unique_valid_pool = list({c.name: c for c in valid_pool}.values())
        card_counts = Counter(c.name for c in deck_cards)

        mutation_type = random.choices(['swap_playset', 'consolidate_slot', 'tech_swap'], weights=[0.4, 0.4, 0.2], k=1)[0]

        if mutation_type == 'swap_playset':
            playsets = [name for name, count in card_counts.items() if count == 4]
            if playsets:
                name_to_swap = random.choice(playsets)
                possible_new = [c for c in unique_valid_pool if c.name not in card_counts]
                if possible_new:
                    new_card = random.choice(possible_new)
                    deck_cards = [c for c in deck_cards if c.name != name_to_swap]
                    deck_cards.extend([new_card] * 4)

        elif mutation_type == 'consolidate_slot':
            two_ofs = [name for name, count in card_counts.items() if count == 2]
            if len(two_ofs) >= 2:
                names_to_remove = random.sample(two_ofs, 2)
                possible_new = [c for c in unique_valid_pool if c.name not in card_counts]
                if possible_new:
                    new_card = random.choice(possible_new)
                    deck_cards = [c for c in deck_cards if c.name not in names_to_remove]
                    deck_cards.extend([new_card] * 4)

        elif mutation_type == 'tech_swap':
            tech_cards = [name for name, count in card_counts.items() if count in [1, 2]]
            if tech_cards:
                name_to_swap = random.choice(tech_cards)
                card_to_swap = next(c for c in deck_cards if c.name == name_to_swap)
                possible_new = [c for c in unique_valid_pool if c.name != name_to_swap]
                if possible_new:
                    new_card = random.choice(possible_new)
                    deck_cards.remove(card_to_swap)
                    deck_cards.append(new_card)

        # If mutation resulted in an invalid deck, revert to the original
        if not is_deck_valid(deck_cards):
            deck_cards = original_deck_cards

        mutated_offspring.append([api_id_to_idx[card.api_id] for card in deck_cards])

    return np.array(mutated_offspring)


if __name__ == '__main__':
    print("--- Project Oracle: Initializing ---")
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db'))
    all_cards_map = Card.load_all_cards(db_path)
    meta_decks = load_meta_decks(db_path, all_cards_map)

    if not all_cards_map or not meta_decks:
        print("Fatal: Could not load data. Aborting.")
        sys.exit(1)

    # Create mappings between string api_id and integer index
    card_api_ids = list(all_cards_map.keys())
    api_id_to_idx = {api_id: i for i, api_id in enumerate(card_api_ids)}
    idx_to_api_id = {i: api_id for i, api_id in enumerate(card_api_ids)}

    config = configparser.ConfigParser()
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
    config.read(config_path)

    ga_config = config['genetic_algorithm']
    population_size = ga_config.getint('population_size', 20)

    print("\n--- Generating Initial Population ---")
    initial_population_decks = generate_population(size=population_size, all_cards_map=all_cards_map)
    initial_population = [[api_id_to_idx[card.api_id] for card in deck] for deck in initial_population_decks]

    ga_instance = pygad.GA(
        num_generations=ga_config.getint('num_generations', 10),
        num_parents_mating=ga_config.getint('num_parents_mating', 5),
        initial_population=initial_population,
        fitness_func=fitness_func,
        crossover_type=on_crossover,
        mutation_type=on_mutation,
        mutation_percent_genes=ga_config.getint('mutation_percent_genes', 5),
        gene_space=range(len(all_cards_map)),
        allow_duplicate_genes=True
    )

    print("\n--- Starting Genetic Algorithm ---")
    ga_instance.run()
    print("--- Genetic Algorithm Finished ---")

    solution, solution_fitness, solution_idx = ga_instance.best_solution()
    print(f"\nBest solution fitness: {solution_fitness}")
    print("\n--- Oracle's Strongest Deck ---")
    best_deck_cards = [all_cards_map[idx_to_api_id[gene]] for gene in solution]
    card_name_counts = Counter(c.name for c in best_deck_cards)
    for name, count in sorted(card_name_counts.items()):
        print(f"{count}x {name}")
