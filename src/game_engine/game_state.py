from .card import Card
from .player import Player
from .board_character import BoardCharacter
from .board_location import BoardLocation
from .ability_resolver import AbilityResolver

class GameState:
    """Manages the overall state of the game, including players, turns, and win conditions."""
    def __init__(self, player1_deck, player2_deck, all_cards, verbose=True):
        self.all_cards = all_cards
        self.player1 = Player("Player 1", player1_deck)
        self.player2 = Player("Player 2", player2_deck)
        self.players = [self.player1, self.player2]
        self.current_turn = 0
        self.active_player_index = 0
        self.game_over = False
        self.winner = None
        self.verbose = verbose

        # Give each player a reference to this game state
        for p in self.players:
            p.set_game_state(self)

    @property
    def active_player(self):
        return self.players[self.active_player_index]

    @property
    def opponent(self):
        return self.players[1 - self.active_player_index]

    def start_game(self):
        """Starts the game, including initial draws."""
        if self.verbose:
            print("--- Starting Game ---")
        for player in self.players:
            player.initial_draw()
        self.current_turn = 1
        self.print_board_state()
        self.run_turn_phases()

    def next_turn(self):
        """Advances the game to the next turn."""
        self.check_for_winner()
        if self.game_over:
            return

        self.active_player_index = 1 - self.active_player_index
        if self.active_player_index == 0:
            self.current_turn += 1
        
        self.print_board_state()
        self.run_turn_phases()

    def run_turn_phases(self):
        """Runs through the standard phases of a single player's turn."""
        self.active_player.ready_turn()
        # Set Phase (not implemented)
        if not self.active_player.draw_card(1):
            self.active_player.has_lost = True
        self.check_for_winner()

    def check_and_banish_characters(self):
        """Checks for and removes any banished characters from both players' boards."""
        for player in self.players:
            # We iterate over a copy of the list because we're modifying it in the loop
            for character in player.characters_in_play[:]:
                if character.is_banished:
                    # This is the global trigger point for any effects that happen upon banishment.
                    # Check if the character was at a location, as some locations have abilities that
                    # trigger when a character is banished there (e.g., 'The Library').
                    if character.location:
                        for ability in character.location.card.parsed_abilities:
                            if ability['trigger'] == 'OnBanishmentAtLocation':
                                # The owner of the ability is the owner of the location card.
                                ability_owner = character.location.owner
                                if self.verbose:
                                    print(f"TRIGGER: {character.card.name} banishment at {character.location.card.name} triggers {ability['effect']}.")
                                AbilityResolver.resolve_ability(ability, character.location.card, ability_owner)
                    
                    # After checking for triggers, officially banish the character from play.
                    player.banish_character(character)

    def check_for_winner(self):
        """Checks if any player has met a win or loss condition."""
        if self.game_over:
            return
        for p in self.players:
            if p.lore >= 20:
                self.game_over = True
                self.winner = p
                return
            if p.has_lost:
                self.game_over = True
                self.winner = p.opponent
                return

    def print_board_state(self):
        """Prints a summary of the current board state."""
        if not self.verbose:
            return
        print(f"\n--- Turn {self.current_turn}: {self.active_player.name}'s Turn ---")
        for p in self.players:
            print(f"  {p.name} Lore: {p.lore}, Hand: {len(p.hand)}")
            print(f"  {p.name} Board: {[str(c) for c in p.characters_in_play]}")
            print(f"  {p.name} Locations: {[str(l) for l in p.locations_in_play]}")
            print(f"  {p.name} Ink: Ready({len(p.inkwell_ready)}), Exerted({len(p.inkwell_exerted)})")

    def run_simulation(self):
        """Runs a simulation loop until a winner is found or the turn limit is reached."""
        self.start_game()

        while not self.game_over and self.current_turn <= 20:
            self.active_player.ai_play_turn(self.opponent)
            self.check_and_banish_characters()
            self.next_turn()

        # Final check for winner if turn limit is reached
        if not self.winner:
            self.check_for_winner()
            
        # If still no winner, decide by lore
        if not self.winner and not self.game_over:
             if self.players[0].lore > self.players[1].lore:
                 self.winner = self.players[0]
             elif self.players[1].lore > self.players[0].lore:
                 self.winner = self.players[1]
             self.game_over = True # Mark game as over due to turn limit

        if self.verbose:
            print("\n--- Game Over ---")
            if self.winner:
                print(f"Winner: {self.winner.name} with {self.winner.lore} lore.")
            else:
                print("Result: It's a draw!")
            self.print_board_state()

        return self.winner
