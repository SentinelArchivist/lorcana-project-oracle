class BoardCharacter:
    """Represents a character or location card that is in play on the board."""
    def __init__(self, card, owner):
        if card.type not in ('Character', 'Location'):
            raise ValueError("Only character or location cards can be in play.")
        self.card = card
        self.owner = owner
        self.damage = 0
        self.is_exerted = False
        # This flag is true for the turn the character is played.
        # It prevents questing/challenging unless the character has Rush.
        self.is_newly_played = True
        self.temp_strength_boost = 0
        self.location = None # None if not at a location, otherwise reference to location

    @property
    def is_ready(self):
        """A character is ready if it is not exerted."""
        return not self.is_exerted

    def exert(self):
        """Exerts the character."""
        self.is_exerted = True

    def ready(self):
        """Readies the character at the start of the turn."""
        self.is_exerted = False
        self.is_newly_played = False
        self.temp_strength_boost = 0

    @property
    def remaining_willpower(self):
        if self.card.willpower is None:
            return float('inf')
        return self.card.willpower - self.damage

    @property
    def strength(self):
        """Returns the current strength of the character, including any temporary boosts."""
        base_strength = self.card.strength or 0
        return base_strength + self.temp_strength_boost

    @property
    def is_banished(self):
        return self.remaining_willpower <= 0

    def can_quest(self):
        """A character can quest if it's ready and its ink isn't drying (not newly played)."""
        return self.is_ready and not self.is_newly_played and self.location is None

    def can_challenge(self):
        """A character can challenge if it's ready and not newly played, unless it has Rush."""
        has_rush = 'rush' in self.card.keywords
        return self.is_ready and (not self.is_newly_played or has_rush)

    def __repr__(self):
        return f"BoardCharacter(name='{self.card.name}', str={self.strength}, will={self.remaining_willpower}/{self.card.willpower}, exerted={self.is_exerted})"
