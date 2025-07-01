import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import re
import time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'lorcana.db')
BASE_URL = "https://mushureport.com"
TOP_DECKS_URL = f"{BASE_URL}/top-decks/"

def normalize_card_name(name):
    """Normalizes a card name for more reliable matching."""
    if not name:
        return ""
    # Lowercase, replace dashes/apostrophes, remove other punctuation, and trim whitespace.
    name = name.lower()
    # Replace various dash-like characters with a standard hyphen-minus
    name = name.replace('–', '-').replace('—', '-').replace('‐', '-')
    name = name.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    # This regex removes punctuation except for apostrophes and hyphens.
    name = re.sub(r'[^\w\s\'-]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_card_id_from_map(normalized_map, card_name):
    """Looks up a card ID from a pre-computed map of normalized names."""
    normalized_name = normalize_card_name(card_name)
    
    # Direct lookup
    if normalized_name in normalized_map:
        return normalized_map[normalized_name]
        
    # Handle names with subtitles like "Card Name - Subtitle"
    # This is a common pattern for Lorcana cards.
    if "-" in normalized_name:
        simple_name = normalized_name.split("-")[0].strip()
        if simple_name in normalized_map:
            return normalized_map[simple_name]
            
    return None

def scrape_deck_details(deck_url):
    """Scrapes the card list from an individual deck detail page by finding and parsing the deck table."""
    print(f"  -> Scraping details from: {deck_url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(deck_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    -> Failed to fetch deck details: {e}")
        return None

    soup = BeautifulSoup(response.content, 'lxml')
    cards = []
    deck_table = None

    # Find the table containing the decklist by looking for characteristic headers.
    all_tables = soup.find_all('table')
    for table in all_tables:
        # The presence of 'Qty' and 'Card Name' in the headers is a strong indicator.
        header_texts = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if 'qty' in header_texts and 'card name' in header_texts:
            deck_table = table
            break

    if deck_table:
        header_texts = [th.get_text(strip=True).lower() for th in deck_table.find_all('th')]
        try:
            name_index = header_texts.index('card name')
            qty_index = header_texts.index('qty')
        except ValueError:
            print(f"    -> Warning: Could not find 'Card Name' or 'Qty' column index in the identified table on {deck_url}.")
            return None

        # Iterate through all rows in the table, skipping the header row [1:]
        for row in deck_table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) > max(name_index, qty_index):
                card_name = cols[name_index].get_text(strip=True)
                quantity_text = cols[qty_index].get_text(strip=True)
                
                # The name might be inside an 'a' tag, let's get it cleanly.
                if cols[name_index].find('a'):
                    card_name = cols[name_index].find('a').get_text(strip=True)
                
                if card_name and quantity_text.isdigit():
                    cards.append((card_name, int(quantity_text)))
    
    if not cards:
        print(f"    -> Warning: No cards found on page {deck_url} using table parsing strategy. The site's structure may have changed.")
        
    return cards

def scrape_and_store_decks():
    """Scrapes top decks from Mushu Report and stores them in the database."""
    print("Scraping metagame decks from Mushu Report...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Debugging: Check how many cards are in the database from the scraper's perspective.
    cursor.execute("SELECT COUNT(*) FROM Cards")
    count = cursor.fetchone()[0]
    print(f"Scraper sees {count} cards in the database.")

    # Build a map of normalized card names to card IDs for efficient, robust matching.
    print("Building a normalized card name map for matching...")
    cursor.execute("SELECT id, name FROM Cards")
    all_cards = cursor.fetchall()
    # Create a map of {normalized_name: card_id}
    card_map = {}
    # We need a reverse map to find the name from an ID for logging collisions
    id_to_name = {card_id: name for card_id, name in all_cards if name}

    for card_id, name in all_cards:
        if not name:
            continue
        normalized = normalize_card_name(name)
        if normalized in card_map:
            existing_id = card_map[normalized]
            print(f"[Collision] Normalized name '{normalized}' for card '{name}' (ID: {card_id}) conflicts with existing card '{id_to_name.get(existing_id, 'Unknown')}' (ID: {existing_id}). Overwriting.")
        card_map[normalized] = card_id
    
    print(f"Map built with {len(card_map)} entries.")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(TOP_DECKS_URL, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {TOP_DECKS_URL}: {e}")
        conn.close()
        return

    soup = BeautifulSoup(response.content, 'lxml')

    # Find all links pointing to deck detail pages
    deck_links = soup.select('a[href*="/deck-details/"]')
    
    print(f"Found {len(deck_links)} deck links. Processing up to 25.")
    decks_added = 0
    
    # Limit to the first 25 decks to avoid being overwhelming
    for link in deck_links[:25]:
        deck_name = link.get_text(strip=True)
        deck_url = link['href']
        
        # Ensure URL is absolute
        if not deck_url.startswith('http'):
            deck_url = f"{BASE_URL}{deck_url}"

        print(f"Processing deck: '{deck_name}'")
        
        # Check if deck already exists
        cursor.execute("SELECT id FROM Decks WHERE source_url = ?", (deck_url,))
        if cursor.fetchone():
            print(f"  -> Deck already in database. Skipping.")
            continue

        card_list = scrape_deck_details(deck_url)
        
        if card_list:
            try:
                # Add deck to Decks table
                cursor.execute("INSERT INTO Decks (name, source_url, date) VALUES (?, ?, date('now'))", (deck_name, deck_url))
                deck_id = cursor.lastrowid

                for card_name, quantity in card_list:
                    card_id = get_card_id_from_map(card_map, card_name)
                    if card_id:
                        cursor.execute("INSERT INTO Deck_Cards (deck_id, card_id, quantity) VALUES (?, ?, ?)", (deck_id, card_id, quantity))
                    else:
                        print(f"    -> Warning: Card '{card_name}' not found in database. Skipping.")
                
                conn.commit()
                decks_added += 1
                print(f"  -> Successfully added '{deck_name}' to database.")

            except Exception as e:
                print(f"  -> Error processing deck '{deck_name}': {e}")
                conn.rollback()
        
        # Be a good web citizen and pause between requests
        time.sleep(1)

    conn.close()
    if decks_added > 0:
        print(f"Successfully added {decks_added} new decks to the database.")
    else:
        print("No new decks were added. They may already be in the database or the website structure has changed.")

if __name__ == '__main__':
    scrape_and_store_decks()
