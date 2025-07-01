import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db')

def clear_deck_data():
    """Deletes all records from the Decks and Deck_Cards tables to allow for a fresh scrape."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Clearing existing deck data...")
        cursor.execute("DELETE FROM Deck_Cards")
        cursor.execute("DELETE FROM Decks")
        # Reset the auto-increment counter for the Decks table for cleanliness
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Decks'")
        conn.commit()
        print("Deck data cleared successfully.")
    except sqlite3.Error as e:
        print(f"Database error while clearing deck data: {e}")
    finally:
        if conn:
            conn.close()

def create_database():
    """Creates the SQLite database and the required tables if they don't exist."""
    print(f"Ensuring database exists at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Cards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        color TEXT,
        cost INTEGER,
        inkable BOOLEAN,
        type TEXT,
        strength INTEGER,
        willpower INTEGER,
        lore INTEGER,
        move_cost INTEGER, -- For Locations
        text TEXT,
        set_name TEXT,
        set_id TEXT,
        rarity TEXT,
        artist TEXT,
        image_url TEXT,
        api_id INTEGER UNIQUE,
        ThreatScore INTEGER DEFAULT 3
    )
    ''')

    # Add columns to existing databases if they are missing
    try:
        cursor.execute("PRAGMA table_info(Cards)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'ThreatScore' not in columns:
            print("Adding 'ThreatScore' column to Cards table...")
            cursor.execute("ALTER TABLE Cards ADD COLUMN ThreatScore INTEGER DEFAULT 3")
            print("'ThreatScore' column added successfully.")
        if 'move_cost' not in columns:
            print("Adding 'move_cost' column to Cards table for Locations...")
            cursor.execute("ALTER TABLE Cards ADD COLUMN move_cost INTEGER")
            print("'move_cost' column added successfully.")
    except sqlite3.Error as e:
        print(f"Database error while altering Cards table: {e}")

    # Create Decks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Decks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_url TEXT,
        date TEXT
    )
    ''')

    # Create Deck_Cards linking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Deck_Cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deck_id INTEGER,
        card_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (deck_id) REFERENCES Decks(id),
        FOREIGN KEY (card_id) REFERENCES Cards(id)
    )
    ''')

    # Create Card_Abilities table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Card_Abilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER,
        trigger TEXT, -- e.g., 'OnPlay', 'OnChallenge', 'Activate'
        effect TEXT, -- e.g., 'DrawCard', 'DealDamage', 'ApplyKeyword'
        target TEXT, -- e.g., 'ChosenCharacter', 'Self', 'OpponentPlayer'
        value TEXT, -- e.g., 1, 2, 'Rush'
        FOREIGN KEY (card_id) REFERENCES Cards(id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

if __name__ == '__main__':
    create_database()
