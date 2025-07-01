# This module contains the functions that execute the game logic for parsed card abilities.

class AbilityResolver:
    @staticmethod
    def resolve_ability(ability, source_card, owner, target=None):
        """Central function to resolve any given ability.""""""Central function to resolve any given ability."""
        effect = ability['effect']
        value = ability['value']

        if owner.game_state.verbose:
            print(f"RESOLVING ABILITY: {effect}({value}) for {owner.name} from card {source_card.name}")

        if effect == 'DrawCard':
            AbilityResolver.resolve_draw_card(owner, int(value))
        elif effect == 'DealDamage':
            if target:
                AbilityResolver.resolve_deal_damage(target, int(value), owner.game_state.verbose)
            else:
                if owner.game_state.verbose:
                    print(f"Warning: DealDamage effect requires a target, but none was provided.")
        elif effect == 'GainLore':
            AbilityResolver.resolve_gain_lore(owner, int(value))
        # More effects will be added here
        else:
            if owner.game_state.verbose:
                print(f"Warning: Unknown ability effect '{effect}' encountered.")

    @staticmethod
    def resolve_draw_card(player, num_cards):
        """Resolves the DrawCard effect."""
        if player.game_state.verbose:
            print(f"  -> {player.name} draws {num_cards} card(s).")
        player.draw_card(num_cards)

    @staticmethod
    def resolve_deal_damage(target_character, damage_amount, verbose=False):
        """Resolves the DealDamage effect.""""""Resolves the DealDamage effect."""
        if verbose:
            print(f"  -> Dealing {damage_amount} damage to {target_character.card.name}.")
        target_character.damage += damage_amount
        if target_character.is_banished and verbose:
            print(f"    -> {target_character.card.name} was banished!")

    @staticmethod
    def resolve_gain_lore(player, lore_amount):
        """Resolves the GainLore effect.""""""Resolves the GainLore effect."""
        if player.game_state.verbose:
            print(f"  -> {player.name} gains {lore_amount} lore.")
        player.lore += lore_amount

