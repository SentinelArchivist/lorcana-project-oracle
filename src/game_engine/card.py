import sqlite3
import re

class Card:
    """Represents a single Lorcana card with all its attributes from the database."""
    def __init__(self, db_row):
        # db_row is a sqlite3.Row object (dictionary-like)
        self.id = db_row['id']
        self.name = db_row['name']
        self.color = db_row['color']
        self.cost = db_row['cost']
        self.inkable = db_row['inkable']
        self.type = db_row['type']
        self.strength = db_row['strength']
        self.willpower = db_row['willpower']
        self.lore = db_row['lore']
        self.move_cost = db_row['move_cost']
        self.text = db_row['text']
        self.set_name = db_row['set_name']
        self.set_id = db_row['set_id']
        self.rarity = db_row['rarity']
        self.artist = db_row['artist']
        self.image_url = db_row['image_url']
        self.api_id = db_row['api_id']
        self.threat_score = db_row['ThreatScore'] or 3

        self.parsed_abilities = []  # This will be populated by load_all_cards
        self.keywords = set()  # This will be populated by load_all_cards

        if isinstance(self.type, str):
            self.type = self.type.strip()

    def __repr__(self):
        return f"Card(name='{self.name}', cost={self.cost}, type='{self.type}')"

    @property
    def base_name(self):
        """Extracts the base name of the character from the full card name."""
        if ' - ' in self.name:
            return self.name.split(' - ')[0]
        return self.name

    @staticmethod
    def load_all_cards(db_path):
        """Loads all cards and their abilities from the database, keyed by api_id."""
        cards = {}
        # We need a temporary map from db id to api_id to link abilities
        id_to_api_id_map = {}
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # First, load all cards
            cursor.execute("SELECT * FROM Cards")
            for row in cursor.fetchall():
                card = Card(row)
                if card.api_id:
                    cards[card.api_id] = card
                    id_to_api_id_map[card.id] = card.api_id

            # Then, load all abilities and attach them to the cards
            cursor.execute("SELECT * FROM Card_Abilities")
            for ability_row in cursor.fetchall():
                db_card_id = ability_row['card_id']
                if db_card_id in id_to_api_id_map:
                    api_id = id_to_api_id_map[db_card_id]
                    ability_dict = dict(ability_row)
                    cards[api_id].parsed_abilities.append(ability_dict)
                    # If the ability is a keyword, add it to our set for easy lookup
                    if ability_dict.get('ability_type') == 'keyword' and ability_dict.get('ability_text'):
                        cards[api_id].keywords.add(ability_dict['ability_text'].lower())
            
            print(f"Successfully loaded {len(cards)} cards and their abilities.")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
        return cards

