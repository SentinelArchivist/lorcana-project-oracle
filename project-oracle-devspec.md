Project Oracle: A Development Specification
[Persona]
Act as an expert principal software architect and data scientist with extensive experience in game theory, trading card game (TCG) analytics, and machine learning. Your goal is to create a comprehensive and actionable development specification for a sophisticated, personal-use application. The user is a passionate TCG player but is not a professional programmer, so all explanations must be clear, concise, and use analogies where possible. The final output should be detailed enough for a hypothetical AI agentic coder to execute the tasks.
[Primary Objective]
Design a full software specification for a personal desktop application, codenamed "Project Oracle," whose primary function is to analyze the Disney Lorcana TCG and rapidly generate and test new deck concepts to identify a locally-optimized, high-potential deck against a few key metagame archetypes. The definition of "strongest" is the deck with the highest simulated win rate against a small, representative metagame, found within a few minutes of runtime.
[Project Requirements and Context]
1. Game: Disney Lorcana
2. Format: Core Constructed (using all officially released cards).
3. End Goal: A functional specification document, broken down into manageable stages and tasks. This is for a personal-use app and will not be published.
4. Key Challenge: The program must go beyond simple data aggregation. It needs to create a game simulation environment to test matchups and employ a machine learning model to intelligently evolve and optimize decklists through a rapid, limited series of simulated games.
[Required Output Structure]
Introduction: The Project Vision
* High-Level Overview: Project Oracle is a personal tool that will discover a powerful Disney Lorcana deck concept. It will achieve this by first creating a complete digital library of all cards and a few top-tier decks. Then, it will build a "Rules Master" that can simulate games between any two decks at high speed. Finally, it will use a form of artificial intelligence to invent, test, and evolve a small population of new deck ideas over a few dozen "generations," constantly breeding the winners and discarding the losers, until the top-performing deck in this rapid-fire tournament is identified.
* Core Concepts Explained:
    * API (Application Programming Interface): Think of this as a direct, clean data pipeline from a website to our application. Instead of "scraping" or "copy-pasting" from the visual part of a site, an API allows our program to request and receive raw, perfectly structured data. It's the most reliable way to get information.
    * Game Simulation Engine: This is a computer program that knows every rule of Lorcana. It doesn't need graphics; it just needs two decklists. It will play out a full game by making logical, text-based moves for both sides according to the game's rules until a winner is determined. It's like a hyper-fast, automated judge that can report the outcome of a match in a fraction of a second.
    * Genetic Algorithm: This is our "Breeder" AI. Imagine each decklist is a creature with its own DNA (the 60 cards in it). We start with a population of decks. The "Fitness Function" is how we measure their strength—we make them play against a gauntlet of known powerful decks in the simulation engine, and their win rate is their fitness score. The "fittest" decks (highest win rates) are "selected" to "breed." Breeding, or "crossover," involves creating new "offspring" decks by mixing and matching cards from the successful parent decks. To keep things from getting stale, we introduce "mutation" by randomly swapping a few cards in the new decks. This process repeats for a limited number of "generations" to find a strong result quickly.
Stage 1: Data Acquisition and Management (The Library)
* Goal: To gather and store all necessary Lorcana data in a structured way.
* Tasks:
    1. Acquire Card Data via API: Connect to a public Lorcana API to get all official card data. The best source for this is lorcana-api.com or lorcast.com/api. These provide free, structured access to card names, costs, ink colors, stats, and crucially, parsed card abilities and keywords. This is vastly superior to web scraping. The program should fetch data for all released sets.
    2. Scrape Metagame Decklists: Program a simple web scraper to gather top-performing decklists from tournament result websites. The primary targets are mushureport.com/top-decks and lorcana.gg. The scraper will look for a small, curated list of 3-5 representative "pillar" metagame decks (e.g., one top aggro, one top control, one top midrange deck) and save them.
    3. Design the Database Schema: Plan how to store this data. This requires four tables (or files):
        * Cards: A table with columns for CardName, InkColor, Cost, Strength, Willpower, Lore, CardText, Set, CardID, etc.
        * Card_Abilities: A new table that translates raw CardText into machine-readable logic. This is the most critical data step for project success. It will have columns like CardID, Trigger (e.g., 'OnPlay', 'OnChallenge', 'Activate'), Effect (e.g., 'DrawCard', 'DealDamage', 'ApplyKeyword'), Target (e.g., 'ChosenCharacter', 'Self', 'OpponentPlayer'), and Value (e.g., 1, 2, 'Rush'). Example: The text "Deal 2 damage to chosen character" would be stored as: CardID: [Card's ID], Trigger: 'OnPlay', Target: 'ChosenCharacter', Effect: 'DealDamage', Value: 2.
        * Decks: A table with columns for DeckName, SourceURL (where it came from), and Date.
        * Deck_Cards: A linking table that connects Decks and Cards, with columns for DeckID, CardID, and Quantity.
    4. Populate the Database: Write the scripts to perform tasks 1 and 2 and populate the Cards, Decks, and Deck_Cards tables. Following this, perform the crucial data-entry task of manually translating the CardText of every ability-driven card into the structured format of the Card_Abilities table.
* Outcome: A local, well-organized database containing every Lorcana card, a collection of 3-5 top-tier "pillar" decks, and a complete, machine-readable translation of all card abilities. This small gauntlet is the testing ground for our AI's creations.
Stage 2: The Game Logic Engine (The Rules Master)
* Goal: To create a system that understands and can execute the rules of a Disney Lorcana game, guided by competent player logic.
* Tasks:
    * Program Game Phases: Code the logic for the turn structure: Ready (unexerting cards), Set (checking for inkable cards), Draw, and the Main Phase where all actions occur.
    * Implement Card Actions: This is the most complex task. Create functions for:
        * Inking a card.
        * Playing a character, item, or action.
        * Questing with characters.
        * Initiating a challenge and calculating damage.
        * Activating special abilities. This requires a system to parse the CardText from our database and translate it into game actions (e.g., if text contains "Rush," allow this character to challenge the turn it's played).
    * Implement Player Logic (The 'Brain'): To ensure decks are judged on their potential, not on poor play, the simulator needs a decision-making model. This will be a heuristic-based AI—a set of smart "rules of thumb" to guide its actions, rather than random choices. The goal is a consistent and competent player, not a perfect one. The logic should prioritize actions based on a weighted system:
        1. Win Condition: If questing results in reaching 20 lore, this is the highest priority action.
        2. Board Control: Evaluate potential challenges. Prioritize removing high-lore enemy characters or those that present a major threat. Favorable trades (banishing a strong enemy character while losing a weaker one) are preferred.
        3. Resource Development: Decide what card to ink. The best candidate is often an unplayable high-cost card in the early game or a card that is redundant in the current hand.
        4. Value Plays: Evaluate playing characters vs. actions. Prioritize actions that generate card advantage or significantly improve the board state (like board wipes or removing key opposing cards).
    * Define State and Conditions: The engine must track the entire game state at all times (each player's lore, cards in hand, cards in play, inkwell, etc.). It must also constantly check for win/loss conditions (a player reaches 20 lore, or a player must draw a card but their deck is empty).
* Outcome: A functional "black box" that can take two decklists from our database as input, simulate a full game between them using intelligent, heuristic-driven play for both sides, and output a result: "Player 1 Wins" or "Player 2 Wins."
Stage 3: The Deck Generator and Genetic Algorithm (The Breeder)
* Goal: To rapidly create, test, and evolve new, legal (max 2 inks) deck combinations automatically.
* Tasks:
    1. Population Generation: Write a function that creates an initial "population" of 20-30 random, but legal (60 cards, max 4 of any card name, max 2 ink colors) decklists using cards from our Cards database.
    2. Fitness Function: Create the core evaluation logic. For each deck in the current population, this function will:
        * Simulate 3-5 games against each of the pillar metagame decks (from Stage 1). This accepts some statistical variance for the sake of speed.
        * Calculate the overall win percentage. This percentage is the deck's "fitness score."
    3. Selection & Crossover (Ink-Aware): Implement the "breeding" logic. The program will select the top 20% of decks from the population based on their fitness score. When creating "offspring," the process must respect the two-ink limit.
    4. Mutation: For each new offspring deck, introduce a small chance (e.g., 5%) of a random mutation.
    5. Generation Limit: The entire process will be hard-limited to a maximum of 10-20 generations to ensure the program completes in a matter of minutes.
* Outcome: A self-improving loop that runs for a short, fixed duration. After selection, crossover, and mutation, a new generation of decks is created and the fitness process repeats until the generation limit is reached, producing a "best effort" deck within the time constraint.
Stage 4: Analysis and User Interface (The Oracle's Vision)
* Goal: To present the findings to the user in a clear and useful way.
* Tasks:
    * Design a Simple UI: The interface doesn't need to be fancy. It should have:
        * A "Start/Stop" button for the genetic algorithm.
        * A text area or log that shows the current generation number and the highest fitness score achieved so far.
        * A main display area to show the full 60-card decklist of the current "fittest" deck.
    * Specify Key Outputs: The main display should show:
        * The full decklist of the champion deck.
        * Its overall win rate (fitness score).
        * A breakdown of its win rate against specific top-tier meta decks (e.g., "72% vs. Amber/Steel Steelsong," "58% vs. Ruby/Sapphire Pawpsicles").
    * (Advanced Feature) Core Package Analysis: As a bonus, the program could analyze the top 100 decks from the final generation and identify "card packages" (groups of 3-5 cards that almost always appear together), presenting these as key strategic cores.
* Outcome: A user-friendly interface that lets the user run the experiment and clearly presents the final, optimized decklist and the data that proves its strength.
[Technical Recommendations]
* Programming Language: Python. It is the industry standard for data science, AI, and rapid prototyping, with a vast ecosystem of libraries that make every stage of this project easier.
* Data Acquisition/Management:
    * requests: For making the API calls to lorcana-api.com.
    * BeautifulSoup4 and requests: For scraping the metagame decklists.
    * pandas: For organizing card and deck data in memory.
    * sqlite3 (built into Python): For simple, file-based database storage.
* Genetic Algorithm: PyGAD. A powerful, well-documented Python library specifically designed for building genetic algorithms. It handles the complex parts (selection, crossover, mutation) so you can focus on the Lorcana-specific logic (the fitness function).
* User Interface: Tkinter (built into Python) or PySimpleGUI. Both are excellent for creating simple, functional desktop applications without a steep learning curve. PySimpleGUI is particularly beginner-friendly.
[Final Actionable Task List]
1. Setup: Install Python and the required libraries: requests, beautifulsoup4, pandas, pygad, and pysimplegui.
2. API Integration & Scraping (Stage 1): Write scripts to call the lorcana-api.com endpoint and parse mushureport.com/top-decks for 3-5 pillar decks, saving the raw data into a temporary location.
3. Define and Populate Database (Stage 1): Create the full SQLite database with the four-table schema defined above. Populate the Cards, Decks, and Deck_Cards tables from the saved data.
4. Crucial: Create Structured Ability Data (Stage 1): Manually review the CardText for each card and populate the Card_Abilities table by translating the text into the defined Trigger, Effect, Target, Valueformat. This deterministic step is essential.
5. Build the Game Engine (Stage 2): Create the Python classes and functions that represent the game state, turn loop, and basic actions (play, quest, challenge).
6. Implement the Ability System (Stage 2): Build the library of functions that correspond to the Effecttags in the Card_Abilities table. The game engine will call these functions based on game triggers.
7. Develop Player Logic Heuristics (Stage 2): Inside the game engine, code the heuristic-based "Brain" to make intelligent decisions for inking, questing, and challenging.
8. Develop the Fitness Function (Stage 3): Write the function that takes a single decklist, runs it through the game engine against the 3-5 pillar meta decks for 3-5 games each, and returns a win rate.
9. Implement the Genetic Algorithm (Stage 3): Use the PyGAD library. Define the parameters for a small population (20-30), a low generation count (10-20), and implement the custom, ink-aware crossover and mutation functions.
10. Design the UI (Stage 4): Use PySimpleGUI to create a window with a start button, a text area for logs, and a display for the best decklist.
11. Integrate and Test: Connect all the pieces. The UI button should trigger the rapid genetic algorithm. Run the full program and begin the search for a high-potential deck.