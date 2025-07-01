import requests
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db')
API_URL = "https://api.lorcana-api.com/cards/all.json"

def fetch_and_store_cards(verbose=False):
    """Fetches all card data from the Lorcana API and stores it in the database."""
    print("Fetching card data from API...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Raise an exception for bad status codes
        cards_data = response.json()
        print(f"Successfully fetched {len(cards_data)} cards.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Storing card data in the database...")
    newly_added_count = 0
    for card in cards_data:
        # For locations, if Move_Cost is missing from the API, default to 1.
        move_cost = card.get('Move_Cost')
        if card.get('Type') == 'Location' and move_cost is None:
            move_cost = 1
            if verbose:
                print(f"INFO: Location '{card.get('Name')}' is missing Move_Cost from API. Defaulting to {move_cost}.")

        # Using UPSERT to insert new cards or update existing ones based on api_id.
        cursor.execute('''
            INSERT INTO Cards (api_id, name, set_id, set_name, image_url, type, color, inkable, cost, lore, strength, willpower, move_cost, rarity, artist, text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(api_id) DO UPDATE SET
                name=excluded.name,
                set_id=excluded.set_id,
                set_name=excluded.set_name,
                image_url=excluded.image_url,
                type=excluded.type,
                color=excluded.color,
                inkable=excluded.inkable,
                cost=excluded.cost,
                lore=excluded.lore,
                strength=excluded.strength,
                willpower=excluded.willpower,
                move_cost=excluded.move_cost,
                rarity=excluded.rarity,
                artist=excluded.artist,
                text=excluded.text
        ''', (
            card.get('Unique_ID'), card.get('Name'), card.get('Set_ID'), card.get('Set_Name'), card.get('Image'), card.get('Type'),
            card.get('Color'), card.get('Inkable'), card.get('Cost'), card.get('Lore'), card.get('Strength'),
            card.get('Willpower'), move_cost, card.get('Rarity'), card.get('Artist'), card.get('Body_Text')
        ))
        if cursor.rowcount > 0:
            newly_added_count += 1

    conn.commit()

    # Debugging: Verify the total number of cards in the table.
    cursor.execute("SELECT COUNT(*) FROM Cards")
    count = cursor.fetchone()[0]
    print(f"Total cards in database after update: {count}")
    
    print(f"Database update complete. Added {newly_added_count} new cards.")
    conn.close()

if __name__ == '__main__':
    fetch_and_store_cards(verbose=True)
