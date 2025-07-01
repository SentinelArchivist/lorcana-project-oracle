class MockCard:
    """A mock card object for testing that can be initialized with kwargs."""
    def __init__(self, name="Mock Card", **kwargs):
        self.id = kwargs.get('id', 1)
        self.name = name
        self.color = kwargs.get('color', 'Amber')
        self.cost = kwargs.get('cost', 1)
        self.inkable = kwargs.get('inkable', True)
        self.type = kwargs.get('type', 'Character')
        self.strength = kwargs.get('strength', 1)
        self.willpower = kwargs.get('willpower', 1)
        self.lore = kwargs.get('lore', 1)
        self.move_cost = kwargs.get('move_cost', None)
        self.text = kwargs.get('text', '')
        self.set_name = kwargs.get('set_name', 'The First Chapter')
        self.set_id = kwargs.get('set_id', 'TFC')
        self.rarity = kwargs.get('rarity', 'Common')
        self.artist = kwargs.get('artist', 'Test Artist')
        self.image_url = kwargs.get('image_url', '')
        self.api_id = kwargs.get('api_id', '1')
        self.threat_score = kwargs.get('threat_score', 3)
        self.parsed_abilities = kwargs.get('parsed_abilities', [])
        self.keywords = kwargs.get('keywords', set())

    @property
    def base_name(self):
        """Extracts the base name of the character from the full card name."""
        if ' - ' in self.name:
            return self.name.split(' - ')[0]
        return self.name

    def __repr__(self):
        return f"MockCard(name='{self.name}', cost={self.cost})"
