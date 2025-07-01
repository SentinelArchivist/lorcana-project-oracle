import random
from collections import deque
from .board_character import BoardCharacter
from .board_location import BoardLocation
from .ability_resolver import AbilityResolver
from . import card

class Player:
    """Represents a player in the game, managing their deck, hand, and game state."""
    def __init__(self, name, deck_cards):
        self.name = name
        self.deck = deque(deck_cards)
        self.hand = []
        self.inkwell_ready = []
        self.inkwell_exerted = []
        self.characters_in_play = []
        self.locations_in_play = []
        self.discard_pile = []
        self.lore = 0
        self.game_state = None  # This will be set by the GameState object
        self.has_inked_this_turn = False
        self.has_lost = False
        self.shuffle_deck()

    def __repr__(self):
        return f"Player(name='{self.name}', lore={self.lore}, ink={self.get_available_ink()}/{self.total_ink}, hand={len(self.hand)}, board={len(self.characters_in_play)}, locations={len(self.locations_in_play)})"

    def set_game_state(self, game_state):
        """Sets a reference to the main game state for context."""
        self.game_state = game_state

    @property
    def opponent(self):
        """Returns the opponent player."""
        if not self.game_state:
            return None
        return self.game_state.player2 if self == self.game_state.player1 else self.game_state.player1

    @property
    def total_ink(self):
        return len(self.inkwell_ready) + len(self.inkwell_exerted)
        
    def get_available_ink(self):
        """Returns the amount of ink available to use."""
        return len(self.inkwell_ready)

    def get_ready_characters(self):
        """Returns characters that can quest or perform other actions."""
        return [c for c in self.characters_in_play if c.is_ready]
        
    def get_characters_that_can_challenge(self):
        """Returns characters that can challenge this turn."""
        return [c for c in self.characters_in_play if c.can_challenge()]

    def get_exerted_characters(self):
        """Returns exerted characters, which are valid challenge targets."""
        return [c for c in self.characters_in_play if c.is_exerted]

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def draw_card(self, num_cards=1):
        for _ in range(num_cards):
            if self.deck:
                self.hand.append(self.deck.popleft())
            else:
                if self.game_state and self.game_state.verbose:
                    print(f"{self.name}'s deck is empty! Cannot draw.")
                return False
        return True

    def initial_draw(self):
        self.draw_card(7)
        if self.game_state and self.game_state.verbose:
            print(f"{self.name} drew their starting hand of 7 cards.")

    def ready_turn(self):
        """Readies all exerted cards, reset flags, and gain passive lore from locations."""
        # Gain lore from locations
        for location in self.locations_in_play:
            # For each character at the location, gain the location's lore value
            lore_gain = sum(location.card.lore for character in self.characters_in_play if character.location == location)
            if lore_gain > 0:
                self.lore += lore_gain
                if self.game_state and self.game_state.verbose:
                    print(f"{self.name} gains {lore_gain} lore from {location.card.name}. Total lore: {self.lore}")

        self.inkwell_ready.extend(self.inkwell_exerted)
        self.inkwell_exerted.clear()
        self.has_inked_this_turn = False
        
        for char in self.characters_in_play:
            char.ready()

        if self.game_state and self.game_state.verbose:
            print(f"{self.name} readied their cards. Ink: {self.get_available_ink()}, Characters: {len(self.characters_in_play)}")

    def exert_ink(self, cost):
        """Exerts a number of ink cards. Returns True on success."""
        if self.get_available_ink() < cost:
            return False
        for _ in range(cost):
            card = self.inkwell_ready.pop()
            self.inkwell_exerted.append(card)
        return True

    def play_to_inkwell(self, card_from_hand):
        if card_from_hand not in self.hand or not card_from_hand.inkable:
            return False
        self.hand.remove(card_from_hand)
        self.inkwell_ready.append(card_from_hand)
        if self.game_state and self.game_state.verbose:
            print(f"{self.name} played {card_from_hand.name} to their inkwell.")
        return True

    def play_character(self, card_from_hand, shift_target=None, ability_target=None):
        """Plays a character from the hand to the board, with optional Shift and ability targeting."""
        if card_from_hand.type != 'Character' or card_from_hand not in self.hand:
            return False

        play_cost = card_from_hand.cost
        is_shift_play = False

        if 'shift' in card_from_hand.keywords and shift_target:
            if shift_target.card.base_name == card_from_hand.base_name:
                play_cost = card_from_hand.keywords.get('shift', card_from_hand.cost)
                is_shift_play = True

        if self.exert_ink(play_cost):
            self.hand.remove(card_from_hand)
            new_character = BoardCharacter(card_from_hand, self)

            if is_shift_play and shift_target:
                new_character.is_newly_played = shift_target.is_newly_played
                new_character.damage = shift_target.damage
                self.characters_in_play.remove(shift_target)
                if self.game_state and self.game_state.verbose:
                    print(f"{self.name} shifted {new_character.card.name} onto {shift_target.card.name} for {play_cost} ink.")
            else:
                if self.game_state and self.game_state.verbose:
                    print(f"{self.name} played {new_character.card.name} for {play_cost} ink.")

            # Bodyguard enters exerted if you have other characters. This check is done *before* adding the new character.
            if 'bodyguard' in new_character.card.keywords and self.characters_in_play:
                new_character.is_exerted = True
            
            self.characters_in_play.append(new_character)

            for ability in card_from_hand.parsed_abilities:
                if ability['trigger'] == 'OnPlay':
                    AbilityResolver.resolve_ability(ability, card_from_hand, self, target=ability_target)
            return True
        return False

    def quest(self, character_in_play):
        """Exerts a ready character to gain lore."""
        if not character_in_play.can_quest():
            return False
        
        lore_gained = character_in_play.card.lore
        self.lore += lore_gained
        character_in_play.exert()
        if self.game_state and self.game_state.verbose:
            print(f"{self.name}'s {character_in_play.card.name} quests for {lore_gained} lore. Total lore: {self.lore}")
        return True

    def challenge(self, attacker, defender):
        """An attacking character challenges a defending character."""
        if not attacker.can_challenge() or not defender.is_exerted:
            return
        
        if 'evasive' in defender.card.keywords and 'evasive' not in attacker.card.keywords:
            return

        attacker.exert()
        
        # Calculate effective strength for the challenge
        attacker_strength = attacker.strength
        if 'challenger' in attacker.card.keywords:
            attacker_strength += attacker.card.keywords.get('challenger', 0)

        defender_strength = defender.strength

        # Apply damage, accounting for Resist
        damage_to_defender = max(0, attacker_strength - defender.resist_value)
        defender.damage += damage_to_defender
        attacker.damage += defender_strength
        
        if self.game_state and self.game_state.verbose:
            print(f"{self.name}'s {attacker.card.name} challenges {defender.card.name}!")
            print(f"  -> {defender.card.name} takes {attacker_strength} damage. {defender.remaining_willpower} willpower left.")
            print(f"  -> {attacker.card.name} takes {defender_strength} damage. {attacker.remaining_willpower} willpower left.")

    def banish_character(self, character):
        """Removes a character from play and moves them to the discard pile."""
        if character in self.characters_in_play:
            self.characters_in_play.remove(character)
            self.discard_pile.append(character.card)
            if self.game_state and self.game_state.verbose:
                print(f"{self.name}'s {character.card.name} was banished.")
        return True

    def play_location(self, card_from_hand):
        """Plays a Location card from the hand to the board."""
        if card_from_hand.type != 'Location' or card_from_hand not in self.hand:
            return False
        
        if self.exert_ink(card_from_hand.cost):
            self.hand.remove(card_from_hand)
            new_location = BoardLocation(card_from_hand, self)  # self is the player
            self.locations_in_play.append(new_location)
            if self.game_state and self.game_state.verbose:
                print(f"{self.name} played new location: {card_from_hand.name} for {card_from_hand.cost} ink.")
            return True
        return False

    def move_character_to_location(self, character, location):
        """Moves a character to a location if the player can pay the move cost."""
        move_cost = location.card.move_cost
        if character not in self.characters_in_play or location not in self.locations_in_play:
            return False
        if self.get_available_ink() < move_cost:
            return False
        if character.location is not None:
            return False

        if self.exert_ink(move_cost):
            character.location = location
            character.exert()  # Moving to a location exerts the character
            if self.game_state and self.game_state.verbose:
                print(f"{self.name} moved {character.card.name} to {location.card.name} for {move_cost} ink.")
            return True
        return False
    # --- AI Action Methods ---

    def ai_ink_card(self, opponent):
        """Smarter AI logic for deciding which card to play to the inkwell using score_play evaluation."""
        if self.has_inked_this_turn:
            return

        inkable_cards = [c for c in self.hand if c.inkable]
        if not inkable_cards:
            return

        # --- New Inking Strategy: Score every inkable card and ink the worst one. ---
        # This uses the same logic that decides what to play, ensuring we keep our best options.
        card_scores = []
        for card in inkable_cards:
            # We pass a cost_override of 0 because we're not checking if we can PLAY it,
            # just evaluating its potential value in the current game state.
            play_option = self.score_play(card, opponent, cost_override=0)
            card_scores.append((card, play_option['score']))

        if not card_scores:
            return

        # Find the card with the lowest score. This is our worst card and the best to ink.
        # If scores are tied, ink the one with the higher cost as a tie-breaker.
        card_scores.sort(key=lambda x: (x[1], -x[0].cost))
        
        best_card_to_ink = card_scores[0][0]

        if best_card_to_ink:
            if self.game_state.verbose:
                print(f"{self.name}'s AI is inking {best_card_to_ink.name}.")
            self.play_to_inkwell(best_card_to_ink)
            self.has_inked_this_turn = True

    def ai_play_turn(self, opponent):
        """Orchestrates the AI's entire main phase logic."""
        if self.game_state.verbose:
            print(f"--- {self.name}: Main Phase ---")

        self.ai_ink_card(opponent)
        self.ai_play_cards(opponent)
        self.ai_move_characters_to_locations()
        self.ai_character_actions(opponent)

        if self.game_state.verbose:
            print(f"--- {self.name}: End of Main Phase ---")

    def ai_play_cards(self, opponent):
        """Smarter AI logic for playing cards, including choosing targets and singing songs."""
        while True:
            best_play = {'card': None, 'score': 1.0, 'target': None, 'singer': None} # Score > 1 to play

            # 1. Evaluate all possible plays from hand
            for card in self.hand:
                # A. Evaluate playing the card normally (paying ink)
                if self.get_available_ink() >= card.cost:
                    play_option = self.score_play(card, opponent)
                    if play_option['score'] > best_play['score']:
                        best_play.update(play_option)

                # B. Evaluate singing the card (if it's a song)
                if "Song" in card.type:
                    for singer in self.get_ready_characters():
                        if singer.singer_value >= card.cost:  # Can this character sing this song?
                            play_option = self.score_play(card, opponent, cost_override=0)
                            # The cost of singing is losing the singer's quest/challenge action
                            play_option['score'] -= (singer.card.lore or 0)
                            if play_option['score'] > best_play['score']:
                                best_play.update(play_option)
                                best_play['singer'] = singer

            # 2. Execute the best play found
            if best_play['card']:
                card_to_play = best_play['card']
                target = best_play.get('target')
                singer = best_play.get('singer')

                if self.game_state.verbose:
                    play_details = f"playing {card_to_play.name}"
                    if singer: play_details = f"singing {card_to_play.name} with {singer.card.name}"
                    if target: play_details += f" targeting {target.card.name}"
                    print(f"{self.name}'s AI considers {play_details} (Score: {best_play['score']:.2f}) - Ink: {self.get_available_ink()}")

                success = False
                if card_to_play.type == 'Character':
                    success = self.play_character(card_to_play)
                elif card_to_play.type == 'Location':
                    success = self.play_location(card_to_play)
                elif card_to_play.type in ('Action', 'Action - Song'):
                    success = self.play_action(card_to_play, ability_target=target, singer=singer)

                if not success:
                    if self.game_state.verbose:
                        print(f"AI play failed for {card_to_play.name}. Stopping further plays.")
                    break  # Stop if a play fails
            else:
                break  # No more good plays found

    def play_action(self, card_from_hand, ability_target=None, singer=None):
        """Plays an Action or Song card, with an option to sing it."""
        # Ward Check: Opponent's effects cannot target a character with Ward.
        if ability_target and hasattr(ability_target, 'card') and 'ward' in ability_target.card.keywords and ability_target.owner != self:
            if self.game_state.verbose:
                print(f"{self.name} cannot target {ability_target.card.name} because it has Ward.")
            return False # Action fails before any cost is paid

        if card_from_hand.type not in ('Action', 'Action - Song') or card_from_hand not in self.hand:
            return False

        play_cost = card_from_hand.cost
        can_sing = False
        if singer and "Song" in card_from_hand.type and singer.is_ready and singer.singer_value >= play_cost:
            can_sing = True
            play_cost = 0

        if can_sing:
            singer.exert()
            if self.game_state.verbose:
                print(f"{self.name}'s {singer.card.name} sings {card_from_hand.name}.")
            payment_successful = True
        else:
            payment_successful = self.exert_ink(play_cost)

        if payment_successful:
            # Check if the target is valid before proceeding
            if ability_target:
                # New Ward Check: Opponent's effects cannot target a character with Ward.
                if hasattr(ability_target, 'card') and 'ward' in ability_target.card.keywords and ability_target.owner != self:
                    if self.game_state.verbose:
                        print(f"{self.name} cannot target {ability_target.card.name} because it has Ward.")
                    return False

                if not self.game_state.is_valid_target(ability_target, card_from_hand, self):
                    if self.game_state.verbose:
                        print(f"{self.name} failed to play {card_from_hand.name}: Invalid target.")
                    return False

            self.hand.remove(card_from_hand)
            self.discard_pile.append(card_from_hand)
            if self.game_state.verbose and not can_sing:
                print(f"{self.name} played action: {card_from_hand.name} for {play_cost} ink.")
            
            for ability in card_from_hand.parsed_abilities:
                AbilityResolver.resolve_ability(ability, card_from_hand, self, target=ability_target)
            return True
        return False

    def find_best_threat(self, opponent, damage=None):
        """
        Finds the most threatening character to target, with awareness of game-ending threats.
        """
        targets = opponent.characters_in_play
        best_target = None
        highest_threat_score = -1
        desperation_mode = opponent.lore >= 15

        for target in targets:
            threat_score = (target.card.lore or 0) * 3 + (target.card.strength or 0)
            can_banish_with_damage = damage is not None and target.remaining_willpower <= damage

            # In desperation mode, removing any character that can quest is a high priority.
            if desperation_mode and (target.card.lore or 0) > 0:
                # If this character's quest wins them the game, it's the #1 priority.
                if opponent.lore + (target.card.lore or 0) >= 20:
                    threat_score += 500  # Overwhelming priority to prevent loss
                else:
                    threat_score += 50   # Still a very high priority

            # Bonus for being able to banish the target with the damage from an action.
            if can_banish_with_damage:
                threat_score += 15

            if threat_score > highest_threat_score:
                highest_threat_score = threat_score
                best_target = target
        
        return best_target, highest_threat_score

    def score_play(self, card, opponent, cost_override=None):
        """Scores a potential card play based on context, returning a dict with score and target."""
        play_cost = cost_override if cost_override is not None else card.cost
        best_option = {'score': 0, 'target': None, 'card': card}

        if play_cost > self.get_available_ink() and cost_override is None:
            return best_option

        score = 0
        # --- Character Evaluation ---
        if card.type == "Character":
            # Base score from stats
            score = (card.strength or 0) + (card.willpower or 0) + (card.lore or 0)

            # Proactive Play Bonus: Encourage playing a character if the board is empty.
            if not self.characters_in_play:
                score += 2  # Small bonus to get something on the board

            # Add a bonus based on the opponent's board presence. Playing a character is more valuable
            # when needing to respond to threats.
            opponent_threat = sum((c.card.strength or 0) + (c.card.lore or 0) for c in opponent.characters_in_play)
            score += opponent_threat * 0.5  # Add 50% of opponent's threat to our score

            # Strategic keywords are more valuable when there's a board to interact with
            if 'rush' in card.keywords: score += opponent_threat * 0.5 # Rush is for immediate trades
            if 'evasive' in card.keywords: score += 2
            if 'ward' in card.keywords: score += 3
            if 'bodyguard' in card.keywords:
                # Bodyguard is valuable to protect high-lore characters or against a big board
                if any(c.card.lore >= 2 for c in self.characters_in_play):
                    score += 4
                score += opponent_threat * 0.3

        # --- Location Evaluation ---
        elif card.type == "Location":
            score = (card.lore or 0) * 5 + (card.willpower or 0)

        # --- Action/Song Evaluation ---
        elif card.type in ("Action", "Action - Song"):
            score = 1.0  # Base score for any action to ensure it's considered
            for ability in card.parsed_abilities:
                effect = ability.get('effect')
                if effect == 'DrawCard':
                    card_draw_bonus = max(0, 6 - len(self.hand))
                    score += int(ability.get('value', 1)) * card_draw_bonus
                elif effect == 'BanishCharacter':
                    # Prioritize board wipes against a wide board
                    if ability.get('target') == 'all' and len(opponent.characters_in_play) >= 3:
                        return {'score': 100.0, 'target': None, 'card': card}  # This is the best possible play

                    best_target, highest_threat = self.find_best_threat(opponent)
                    if best_target:
                        score += highest_threat
                        best_option['target'] = best_target
                elif effect == 'DealDamage':
                    best_target, highest_threat = self.find_best_threat(opponent, damage=int(ability.get('value', 1)))
                    if best_target:
                        score += highest_threat
                        best_option['target'] = best_target
        
        if score > 0:
            best_option['score'] = score / (play_cost + 1) # Normalize by cost
        
        return best_option

    def ai_move_characters_to_locations(self):
        """Smarter AI logic for moving characters to locations."""
        if not self.locations_in_play:
            return

        for char in self.get_ready_characters()[:]:
            if char.location: continue

            best_location = None
            questing_score = char.card.lore or 0
            best_move_score = -1

            for loc in self.locations_in_play:
                move_cost = loc.card.move_cost
                if move_cost is None or self.get_available_ink() < move_cost:
                    continue

                move_score = (loc.card.lore or 0) * 3 - move_cost
                for ability in loc.card.parsed_abilities:
                    if ability['trigger'] == 'OnBanishmentAtLocation' and ability['effect'] == 'DrawCard':
                        card_draw_bonus = max(0, 4 - len(self.hand))
                        move_score += card_draw_bonus * 2

                if move_score > best_move_score:
                    best_move_score = move_score
                    best_location = loc

            if best_location and best_move_score > questing_score:
                if self.game_state.verbose:
                    print(f"{self.name}'s AI is moving {char.card.name} to {best_location.card.name} (Score: {best_move_score:.2f} vs Questing: {questing_score}) - Ink: {self.get_available_ink()}")
                self.move_character_to_location(char, best_location)

    def ai_character_actions(self, opponent):
        """AI logic for questing or challenging, with strategic awareness of game state."""
        # Desperation mode: If opponent is building a strong lead, prioritize stopping them.
        desperation_mode = opponent.lore >= 10

        for char in self.get_ready_characters()[:]:
            if not char.is_ready: continue

            best_challenge_option = {'target': None, 'score': -1}
            if char.can_challenge():
                possible_targets = opponent.get_exerted_characters()
                for target in possible_targets:
                    can_banish = (char.strength or 0) >= target.remaining_willpower
                    will_be_banished = (target.strength or 0) >= char.remaining_willpower
                    score = 0

                    if desperation_mode and can_banish and (target.card.lore or 0) > 0:
                        score = 100 + (target.card.lore or 0)
                    elif not desperation_mode:
                        if can_banish and (target.card.lore or 0) >= 2:
                            score = 20 + (target.card.lore or 0)
                            if not will_be_banished: score += 5
                        elif can_banish and not will_be_banished:
                            score = 15 + (target.card.lore or 0)
                        elif can_banish and will_be_banished:
                            score = 10 + (target.card.lore or 0) - (char.card.lore or 0)

                    if score > best_challenge_option['score']:
                        best_challenge_option['score'] = score
                        best_challenge_option['target'] = target

            # Reckless characters MUST challenge if a target is available.
            is_reckless = 'reckless' in char.card.keywords
            if is_reckless and best_challenge_option['target']:
                if self.game_state.verbose:
                    print(f"{self.name}'s AI is forced to make a RECKLESS challenge with {char.card.name} against {best_challenge_option['target'].card.name}.")
                self.challenge(char, best_challenge_option['target'])
                continue  # Move to the next character

            # Normal decision logic
            challenge_threshold = 50 if desperation_mode else (char.card.lore or 0) + 2
            if best_challenge_option['score'] > challenge_threshold:
                if self.game_state.verbose:
                    mode = "DESPERATE" if desperation_mode else "strategic"
                    print(f"{self.name}'s AI is making a {mode} challenge with {char.card.name} against {best_challenge_option['target'].card.name} (Score: {best_challenge_option['score']}) - Ink: {self.get_available_ink()}")
                self.challenge(char, best_challenge_option['target'])
            elif char.can_quest():
                # In desperation mode, DON'T quest if you could have challenged a threat.
                if desperation_mode and best_challenge_option['score'] > 0:
                    continue
                if self.game_state.verbose:
                    print(f"{self.name}'s AI is questing with {char.card.name} for {char.card.lore} lore.")
                self.quest(char)



