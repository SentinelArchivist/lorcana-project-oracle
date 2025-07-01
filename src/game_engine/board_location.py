"""
This module defines the BoardLocation class, which represents a location card in play.
"""

class BoardLocation:
    """Represents a single location card on the board."""
    def __init__(self, card, player):
        self.card = card
        self.owner = player
        self.willpower = card.willpower
        self.damage = 0

    def __repr__(self):
        return f"BoardLocation(name='{self.card.name}', will='{self.willpower - self.damage}/{self.willpower}')"
