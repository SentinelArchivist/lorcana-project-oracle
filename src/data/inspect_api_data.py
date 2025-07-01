import requests
import json

API_URL = "https://api.lorcana-api.com/cards/all.json"

def inspect_single_card_from_api(card_name_to_find):
    """Fetches all card data and prints the raw data for a specific card."""
    print(f"Fetching card data from API to find '{card_name_to_find}'...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        cards_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return

    found_card = None
    for card in cards_data:
        if card.get('Name') == card_name_to_find:
            found_card = card
            break
    
    if found_card:
        print(f"\n--- Raw API Data for: {card_name_to_find} ---")
        print(json.dumps(found_card, indent=2))
        
        if 'Move_Cost' in found_card and found_card['Move_Cost'] is not None:
            print(f"\nSUCCESS: 'Move_Cost' is present and has value: {found_card['Move_Cost']}")
        else:
            print(f"\nFAILURE: 'Move_Cost' is missing or null.")

    else:
        print(f"Could not find card '{card_name_to_find}' in the API response.")

if __name__ == '__main__':
    print("--- Checking a card that successfully updated ---")
    inspect_single_card_from_api("McDuck Manor - Scrooge's Mansion")
    print("\n-------------------------------------------------")
    print("--- Checking a card that failed to update ---")
    inspect_single_card_from_api("Hundred Acre Island - Pooh's Home")
