import pytest
import random
import os
import sys
from collections import Counter

# No sys.path manipulation needed when running pytest from the project root

from src.optimizer.runner import run_ga, on_crossover, on_mutation, is_deck_valid, get_deck_inks
from tests.test_utils import MockCard, MockDeck
from src.game_engine.card import Card
from unittest.mock import patch, MagicMock

# --- Test Fixtures and Mock Data ---

@pytest.fixture(scope="module")
def all_cards_map():
    """Creates a diverse mock map of all possible cards for testing."""
    cards = []
    inks = ["Amber", "Amethyst", "Emerald", "Ruby", "Sapphire", "Steel"]
    for i in range(200): # Create 200 unique cards
        card_ink = random.choice(inks)
        cards.append(MockCard(api_id=f"test_{i}", name=f"Test Card {i}", color=card_ink, cost=random.randint(1, 8), inkable=random.choice([True, False])))
    # Add some inkless cards
    for i in range(200, 210):
        cards.append(MockCard(api_id=f"test_{i}", name=f"Test Card {i} Inkless", color=None, cost=random.randint(1, 8), inkable=False))
    return {card.api_id: card for card in cards}

@pytest.fixture
def mock_ga_instance(all_cards_map):
    """Mocks the PyGAD instance and populates global variables needed by the optimizer functions."""
    class MockGA:
        def __init__(self):
            self.gene_space = range(len(all_cards_map))

    # This is a bit of a hack, but it's the simplest way to test the standalone functions
    # that rely on global state. A better long-term solution would be to refactor them into a class.
    from src.optimizer import runner
    runner.all_cards_map = all_cards_map
    runner.api_id_to_idx = {api_id: i for i, api_id in enumerate(all_cards_map.keys())}
    runner.idx_to_api_id = {i: api_id for i, api_id in enumerate(all_cards_map.keys())}
    return MockGA()

def create_mock_deck_solution(all_cards_map, inks, size=60):
    """Helper to create a valid random deck solution for testing."""
    deck_cards = []
    card_pool = [c for c in all_cards_map.values() if c.color in inks or c.color is None]
    card_counts = Counter()
    while len(deck_cards) < size:
        card = random.choice(card_pool)
        if card_counts[card.api_id] < 4:
            deck_cards.append(card)
            card_counts[card.api_id] += 1
    
    api_id_to_idx = {api_id: i for i, api_id in enumerate(all_cards_map.keys())}
    return [api_id_to_idx[c.api_id] for c in deck_cards]

# --- Optimizer Tests ---

def test_deck_validity_checker():
    """Tests the is_deck_valid helper function."""
    # Valid deck (60 cards, 2 inks)
    cards = [MockCard(api_id='1', name='c1', color='Amber')] * 30 + [MockCard(api_id='2', name='c2', color='Ruby')] * 30
    assert is_deck_valid(cards) == True

    # Invalid deck (> 60 cards)
    cards = [MockCard(api_id='1', name='c1', color='Amber')] * 61
    assert is_deck_valid(cards) == False

    # Invalid deck (3 inks)
    cards = [MockCard(api_id='1', name='c1', color='Amber')] * 20 + \
            [MockCard(api_id='2', name='c2', color='Ruby')] * 20 + \
            [MockCard(api_id='3', name='c3', color='Emerald')] * 20
    assert is_deck_valid(cards) == False

def test_on_crossover(mock_ga_instance, all_cards_map):
    """Ensures the custom crossover function produces valid offspring decks."""
    parent1 = create_mock_deck_solution(all_cards_map, ["Amber", "Amethyst"])
    parent2 = create_mock_deck_solution(all_cards_map, ["Ruby", "Sapphire"])
    parents = [parent1, parent2]

    offspring = on_crossover(parents, (1, 60), mock_ga_instance)

    assert len(offspring) == 1
    offspring_solution = offspring[0]
    assert len(offspring_solution) == 60

    # Convert solution back to cards to validate
    idx_to_api_id = {i: api_id for i, api_id in enumerate(all_cards_map.keys())}
    offspring_cards = [all_cards_map[idx_to_api_id[gene]] for gene in offspring_solution]

    assert is_deck_valid(offspring_cards) == True
    card_counts = Counter(c.name for c in offspring_cards)
    assert all(count <= 4 for count in card_counts.values())

def test_on_mutation(mock_ga_instance, all_cards_map):
    """Ensures the custom mutation function produces valid offspring decks."""
    parent_solution = create_mock_deck_solution(all_cards_map, ["Emerald", "Steel"])
    offspring_to_mutate = [parent_solution]

    mutated_offspring = on_mutation(offspring_to_mutate, mock_ga_instance)

    assert len(mutated_offspring) == 1
    mutated_solution = mutated_offspring[0]
    assert len(mutated_solution) == 60

    # Convert solution back to cards to validate
    idx_to_api_id = {i: api_id for i, api_id in enumerate(all_cards_map.keys())}
    mutated_cards = [all_cards_map[idx_to_api_id[gene]] for gene in mutated_solution]

    assert is_deck_valid(mutated_cards) == True
    card_counts = Counter(c.name for c in mutated_cards)
    assert all(count <= 4 for count in card_counts.values())


@patch('src.optimizer.runner.calculate_fitness')
@patch('src.optimizer.runner.generate_population')
def test_run_ga_with_early_stopping_and_progress(mock_generate_population, mock_calculate_fitness, all_cards_map):
    """Tests the full run_ga loop with progress bar, early stopping, and interruption."""
    # Setup for mocking
    card_api_ids = list(all_cards_map.keys())
    idx_to_api_id = {i: api_id for i, api_id in enumerate(card_api_ids)}

    # Mock what generate_population returns: a list of decks (list of lists of Card objects)
    mock_solution = create_mock_deck_solution(all_cards_map, ['Amber', 'Amethyst'])
    mock_deck_of_cards = [all_cards_map[idx_to_api_id[gene]] for gene in mock_solution]
    mock_generate_population.return_value = [mock_deck_of_cards] * 15 # population_size

    # Mock fitness to control the outcome for early stopping, accounting for elitism (1 parent saved).
    # 15 for initial pop + 14 for each of the 11 generations in the run loop.
    mock_calculate_fitness.side_effect = [0.8] * 15 + [0.7] * (14 * 11)

    mock_meta_decks = [MockDeck(name=f"Meta Deck {i}", cards=[]) for i in range(3)]

    # 1. Test Early Stopping
    best_deck = run_ga(all_cards_map, mock_meta_decks, num_generations=50)

    assert best_deck is not None
    assert len(best_deck.cards) == 60
    # GA runs for 1 (initial) + 11 (loop) = 12 generations.
    # Due to elitism=1 (default), calls are 15 (initial) + 14 * 11 (loop) = 169
    assert mock_calculate_fitness.call_count == 169

    # 2. Test Keyboard Interrupt
    mock_calculate_fitness.reset_mock()
    mock_generate_population.reset_mock()
    mock_generate_population.return_value = [mock_deck_of_cards] * 15
    mock_calculate_fitness.side_effect = None
    mock_calculate_fitness.return_value = 0.6  # Constant fitness

    with patch('pygad.GA.run', side_effect=KeyboardInterrupt) as mock_run:
        best_deck_interrupted = run_ga(all_cards_map, mock_meta_decks, num_generations=20)
        assert best_deck_interrupted is not None
        assert len(best_deck_interrupted.cards) == 60
        mock_run.assert_called_once()
