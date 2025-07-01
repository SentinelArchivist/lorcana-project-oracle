import random
import sys
import os
from collections import Counter

# Add the src directory to the Python path to allow for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.card import Card

INK_COLORS = ["Amber", "Amethyst", "Emerald", "Ruby", "Sapphire", "Steel"]


def generate_random_deck(all_cards_map):
    """
    Generates a single random, structurally-sound, and legal 60-card deck.
    This new logic prioritizes 4-of playsets to create more consistent decks.
    """
    deck = []
    card_counts = Counter()

    # 1. Randomly select two ink colors
    chosen_inks = random.sample(INK_COLORS, 2)
    # print(f"Generating a new {chosen_inks[0]}/{chosen_inks[1]} deck...") # Too verbose for GA

    # 2. Filter the card pool to the chosen inks (plus colorless cards)
    available_cards = [card for card in all_cards_map.values() if card.color in chosen_inks or card.color is None]
    
    # Ensure the list of available cards is unique by name to avoid duplicates in selection
    unique_cards_by_name = {card.name: card for card in available_cards}
    unique_available_cards = list(unique_cards_by_name.values())
    random.shuffle(unique_available_cards)

    # 3. Build the deck with a focus on playsets (4-ofs)
    # Aim for around 10-12 playsets and fill the rest
    num_playsets_to_add = 12 
    
    for card in unique_available_cards:
        if len(deck) + 4 <= 60 and num_playsets_to_add > 0:
            deck.extend([card] * 4)
            card_counts[card.name] += 4
            num_playsets_to_add -= 1
        
        if num_playsets_to_add == 0:
            break

    # 4. Fill the remaining slots to reach 60 cards
    # This part can add 1-ofs, 2-ofs, or 3-ofs to complete the deck
    while len(deck) < 60:
        candidate_card = random.choice(unique_available_cards)
        
        # Add card if we haven't reached its 4-copy limit
        if card_counts[candidate_card.name] < 4:
            deck.append(candidate_card)
            card_counts[candidate_card.name] += 1
            
    # 5. If we overfilled (e.g., last add was a playset that pushed it > 60), trim it down.
    # This is less likely with the new logic but good to have as a safeguard.
    while len(deck) > 60:
        removed_card = deck.pop()
        card_counts[removed_card.name] -= 1

    return deck

def generate_population(size, all_cards_map):
    """Generates a population of random decks."""
    return [generate_random_deck(all_cards_map) for _ in range(size)]

if __name__ == '__main__':
    # Example of how to use the generator
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db'))
    all_cards_map = Card.load_all_cards(db_path)

    if all_cards_map:
        # Generate one sample deck to show the new structure
        print("\n--- Sample Generated Deck (New Logic) ---")
        sample_deck = generate_random_deck(all_cards_map)
        
        # Verify ink consistency
        inks = {c.color for c in sample_deck if c.color is not None}
        print(f"Deck Inks: {list(inks)}")
        
        # Print decklist
        card_name_counts = Counter(c.name for c in sample_deck)
        for name, count in sorted(card_name_counts.items()):
            print(f"{count}x {name}")
        print(f"Total cards: {len(sample_deck)}")
