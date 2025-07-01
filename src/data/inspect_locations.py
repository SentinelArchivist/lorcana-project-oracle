import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db')

def inspect_location_data():
    """Inspects location card data in the database."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("--- Checking Specific Locations ---")
        locations_to_check = ["McDuck Manor - Scrooge's Mansion", "The Library - A Gift for Belle"]
        for loc_name in locations_to_check:
            print(f"\nChecking: {loc_name}")
            cursor.execute("""
                SELECT c.id, c.move_cost, c.lore, c.text 
                FROM Cards c 
                WHERE c.name = ? AND c.type = 'Location'
            """, (loc_name,))
            card_data = cursor.fetchone()

            if card_data:
                card_id, move_cost, lore, text = card_data
                print(f"  - Move Cost: {move_cost}")
                print(f"  - Passive Lore: {lore}")
                print(f"  - Card Text: {text}")

                cursor.execute("SELECT trigger, effect, value FROM Card_Abilities WHERE card_id = ?", (card_id,))
                abilities = cursor.fetchall()
                if abilities:
                    print("  - Parsed Abilities:")
                    for ability in abilities:
                        print(f"    - Trigger: {ability[0]}, Effect: {ability[1]}, Value: {ability[2]}")
                else:
                    print("  - Parsed Abilities: None")
            else:
                print(f"  - Location not found in database.")

        print("\n--- Verifying All Locations Have a Move Cost ---")
        cursor.execute("SELECT name, move_cost FROM Cards WHERE type = 'Location' AND move_cost IS NULL")
        locations_with_null_cost = cursor.fetchall()

        if not locations_with_null_cost:
            print("Success: All locations in the database have a non-null move_cost.")
        else:
            print("Warning: The following locations have a NULL move_cost:")
            for loc in locations_with_null_cost:
                print(f"  - {loc[0]}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    inspect_location_data()
