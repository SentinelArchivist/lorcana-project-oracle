import pytest
import sqlite3
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from game_engine.card import Card
from game_engine.deck import Deck, load_meta_decks

@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary SQLite database for testing data functions."""
    db_path = tmp_path / "test_lorcana.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Cards table with a schema that matches the Card class
    cursor.execute("""
    CREATE TABLE Cards (
        id INTEGER PRIMARY KEY,
        api_id TEXT UNIQUE,
        name TEXT,
        color TEXT,
        cost INTEGER,
        inkable INTEGER,
        type TEXT,
        strength INTEGER,
        willpower INTEGER,
        lore INTEGER,
        move_cost INTEGER,
        text TEXT,
        set_name TEXT,
        set_id TEXT,
        rarity TEXT,
        artist TEXT,
        image_url TEXT,
        ThreatScore REAL
    )
    """)
    # Insert mock card data
    mock_cards = [
        (1, 'test_01', 'Mickey Mouse', 'Amber', 1, 1, 'Character', 1, 1, 1, None, 'Support', 'The First Chapter', 'TFC', 'Common', 'Artist A', '', 3.0),
        (2, 'test_02', 'Goofy', 'Emerald', 2, 1, 'Character', 2, 2, 1, None, '', 'The First Chapter', 'TFC', 'Common', 'Artist B', '', 3.0),
        (3, 'test_03', 'Be Prepared', 'Ruby', 7, 0, 'Action', 0, 0, 0, None, 'Banish all characters.', 'The First Chapter', 'TFC', 'Rare', 'Artist C', '', 5.0),
        (4, 'test_04', 'Magic Mirror', 'Sapphire', 2, 1, 'Item', 0, 0, 0, None, 'Ward', 'The First Chapter', 'TFC', 'Uncommon', 'Artist D', '', 4.0)
    ]
    cursor.executemany("INSERT INTO Cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", mock_cards)

    # Create Card_Abilities table (needed by load_all_cards)
    cursor.execute("""
    CREATE TABLE Card_Abilities (
        id INTEGER PRIMARY KEY,
        card_id INTEGER,
        ability_type TEXT,
        ability_text TEXT,
        trigger TEXT
    )
    """)

    # Create decks and deck_contents tables
    cursor.execute("CREATE TABLE decks (id INTEGER PRIMARY KEY, name TEXT, source TEXT, source_url TEXT)")
    cursor.execute("CREATE TABLE Deck_Cards (deck_id INTEGER, card_id INTEGER, quantity INTEGER)")

    # Insert mock meta deck data
    cursor.execute("INSERT INTO decks VALUES (?, ?, ?, ?)", (1, 'Test Meta Deck', 'test_source', 'http://test.com'))
    mock_deck_contents = [
        (1, 1, 4), # test_01 -> Mickey Mouse
        (1, 2, 4), # test_02 -> Goofy
        (1, 3, 2)  # test_03 -> Be Prepared
    ]
    cursor.executemany("INSERT INTO Deck_Cards VALUES (?,?,?)", mock_deck_contents)

    conn.commit()
    conn.close()
    return str(db_path)

def test_load_all_cards(temp_db):
    """Tests that Card.load_all_cards correctly loads all cards from the database."""
    all_cards = Card.load_all_cards(temp_db)
    assert isinstance(all_cards, dict)
    assert len(all_cards) == 4
    assert 'test_01' in all_cards
    assert all_cards['test_01'].name == 'Mickey Mouse'
    assert all_cards['test_03'].inkable == False

def test_load_meta_decks(temp_db):
    """Tests that load_meta_decks correctly loads and constructs deck objects."""
    all_cards = Card.load_all_cards(temp_db)
    meta_decks = load_meta_decks(temp_db, all_cards)

    assert isinstance(meta_decks, list)
    assert len(meta_decks) == 1
    
    deck = meta_decks[0]
    assert isinstance(deck, Deck)
    assert deck.name == 'Test Meta Deck'
    
    # The deck should have 10 cards total (4 + 4 + 2)
    assert len(deck.cards) == 10
    
    card_names = [c.name for c in deck.cards]
    assert card_names.count('Mickey Mouse') == 4
    assert card_names.count('Goofy') == 4
    assert card_names.count('Be Prepared') == 2
