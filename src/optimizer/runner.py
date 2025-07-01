import pygad
import random
import os
import numpy as np
from collections import Counter
import configparser

from ..game_engine.card import Card
from ..game_engine.deck import Deck, load_meta_decks
from .fitness import calculate_fitness
from .deck_generator import generate_population, INK_COLORS

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


def run_ga(all_cards, meta_decks_tuple, num_generations=10, progress_queue=None):
    """Runs the genetic algorithm to optimize a deck."""
    global all_cards_map, meta_decks, api_id_to_idx, idx_to_api_id
    all_cards_map = all_cards
    meta_decks = meta_decks_tuple

    card_api_ids = list(all_cards_map.keys())
    api_id_to_idx = {api_id: i for i, api_id in enumerate(card_api_ids)}
    idx_to_api_id = {i: api_id for i, api_id in enumerate(card_api_ids)}

    config = configparser.ConfigParser()
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'))
    config.read(config_path)

    ga_config = config['genetic_algorithm']
    population_size = ga_config.getint('population_size', 20)

    initial_population_decks = generate_population(size=population_size, all_cards_map=all_cards_map)
    initial_population = [[api_id_to_idx[card.api_id] for card in deck] for deck in initial_population_decks]

    # --- State and callback setup ---
    early_stopping_patience = ga_config.getint('early_stopping_patience', 10)
    best_fitness_so_far = -999.0
    generations_without_improvement = 0

    def on_generation_callback(ga_instance):
        nonlocal best_fitness_so_far, generations_without_improvement

        current_gen_best_fitness = np.max(ga_instance.last_generation_fitness)

        if current_gen_best_fitness > best_fitness_so_far:
            best_fitness_so_far = current_gen_best_fitness
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1

        if progress_queue:
            progress_queue.put({
                "type": "progress",
                "current": ga_instance.generations_completed,
                "total": num_generations,
                "best_fitness": best_fitness_so_far
            })

        if generations_without_improvement >= early_stopping_patience:
            print(f"\nEarly stopping triggered after {ga_instance.generations_completed} generations.")
            return "stop"

    ga_instance = pygad.GA(
        num_generations=num_generations,
        num_parents_mating=ga_config.getint('num_parents_mating', 5),
        initial_population=initial_population,
        fitness_func=fitness_func,
        on_generation=on_generation_callback,
        crossover_type=on_crossover,
        mutation_type=on_mutation,
        mutation_percent_genes=ga_config.getint('mutation_percent_genes', 5),
        gene_space=range(len(all_cards_map)),
        allow_duplicate_genes=True
    )

    try:
        ga_instance.run()
    except KeyboardInterrupt:
        print("\nGA interrupted by user. Returning best solution found so far.")
    finally:
        pass

    solution, solution_fitness, solution_idx = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)
    best_deck_cards = [all_cards_map[idx_to_api_id[gene]] for gene in solution]
    
    best_deck = Deck(name="Optimized Deck", cards=best_deck_cards)
    return best_deck
