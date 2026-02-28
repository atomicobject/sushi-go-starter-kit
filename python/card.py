class Card:
    """Represents a Sushi Go card type."""

    def __init__(self, name: str, shorthand: str = ""):
        self.name = name
        self.shorthand = shorthand if shorthand else name[0]