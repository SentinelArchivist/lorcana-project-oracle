import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db')

# Define simple keywords that map directly to abilities.
# This handles abilities listed in the 'abilities' column of the Cards table.
KEYWORD_ABILITIES = {
    'Rush': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Rush'},
    'Evasive': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Evasive'},
    'Ward': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Ward'},
    'Bodyguard': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Bodyguard'},
    'Support': {'trigger': 'OnQuest', 'effect': 'Support', 'target': 'ChosenCharacter', 'value': None}, # Value is dynamic
    'Challenger': {'trigger': 'OnChallenge', 'effect': 'ModifyStrength', 'target': 'Self', 'value': None}, # Value is dynamic
    'Reckless': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Reckless'},
    'Resist': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Resist'}, # Value is dynamic
    'Singer': {'trigger': 'Passive', 'effect': 'ApplyKeyword', 'target': 'Self', 'value': 'Singer'} # Value is dynamic
}

def parse_text_abilities(card_id, card_text):
    """Parses the main text box of a card for more complex, regex-matchable abilities."""
    abilities = []
    if not card_text: return abilities

    # Location Ability: "Whenever a character is banished while here, you may draw a card."
    # This is a specific trigger that should be checked before more generic ones.
    banish_draw_match = re.search(r'whenever a character is banished while here, you may\s+draw (\d+|a) card', card_text, re.IGNORECASE)
    if banish_draw_match:
        value = 1 if banish_draw_match.group(1).lower() == 'a' else int(banish_draw_match.group(1))
        abilities.append((card_id, 'OnBanishmentAtLocation', 'DrawCard', 'Player', str(value)))
        # Return now because we've found the most specific ability and don't want generic matches.
        return abilities

    # Example 1: Draw card effect
    # Pattern: "draw a card", "draw 2 cards"
    draw_match = re.search(r'draw (\d+|a) card', card_text, re.IGNORECASE)
    if draw_match:
        value = 1 if draw_match.group(1).lower() == 'a' else int(draw_match.group(1))
        trigger = 'OnPlay' # Assumption, needs more context
        if 'when you play this character' in card_text.lower():
            trigger = 'OnPlay'
        elif 'when this character quests' in card_text.lower():
            trigger = 'OnQuest'
        abilities.append((card_id, trigger, 'DrawCard', 'Self', str(value)))

    # Example 2: Deal damage effect
    # Pattern: "deal 2 damage to chosen character"
    damage_match = re.search(r'deal (\d+) damage to chosen character', card_text, re.IGNORECASE)
    if damage_match:
        value = int(damage_match.group(1))
        trigger = 'OnPlay' # Assumption
        abilities.append((card_id, trigger, 'DealDamage', 'ChosenCharacter', str(value)))
        
    return abilities

def populate_card_abilities():
    """Parses all card text to populate the Card_Abilities table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Clearing existing data from Card_Abilities table...")
    cursor.execute("DELETE FROM Card_Abilities")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Card_Abilities'")

    print("Fetching all cards to parse for abilities...")
    # We no longer need the 'abilities' column
    cursor.execute("SELECT id, text FROM Cards")
    all_cards = cursor.fetchall()

    print(f"Parsing abilities for {len(all_cards)} cards...")
    parsed_abilities = []
    
    for card_id, card_text in all_cards:
        if not card_text:
            continue
            
        # Use a set to avoid adding duplicate abilities for the same card
        card_specific_abilities = set()

        # 1. Parse keywords from the card_text
        for keyword, ability_template in KEYWORD_ABILITIES.items():
            # This regex looks for the keyword, and an optional "+ NUMBER" part
            pattern = re.compile(rf'\b{re.escape(keyword)}(?:\s*\+\s*(\d+))?\b', re.IGNORECASE)
            match = pattern.search(card_text)
            
            if match:
                ability_data = ability_template.copy()
                
                # Handle dynamic values like Challenger +X
                value_from_text = match.group(1)
                if value_from_text:
                    ability_data['value'] = value_from_text
                
                # Create a tuple to add to the set (dictionaries are not hashable)
                ability_tuple = (card_id, ability_data['trigger'], ability_data['effect'], ability_data['target'], ability_data['value'])
                card_specific_abilities.add(ability_tuple)

        # 2. Parse more complex abilities from the main text box
        text_abilities = parse_text_abilities(card_id, card_text)
        for ability in text_abilities:
            card_specific_abilities.add(tuple(ability))
            
        parsed_abilities.extend(list(card_specific_abilities))

    print(f"Found {len(parsed_abilities)} abilities to insert.")
    if parsed_abilities:
        # The executemany now expects a list of tuples, which we have.
        cursor.executemany(
            "INSERT INTO Card_Abilities (card_id, trigger, effect, target, value) VALUES (?, ?, ?, ?, ?)",
            parsed_abilities
        )
        print("Successfully populated Card_Abilities table.")
    else:
        print("No abilities were parsed.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    populate_card_abilities()
