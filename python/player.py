class Player:
    """Represents a player in the game."""

    def __init__(self, name: str):
        self.name = name # Cards that the person has played
        self.played_cards: list[str] = []  # Cards currently in the player's hand
        self.current_hand: list[str] = []    # {1: 5, 2: 12, 3: 18}
        self.points_by_round: dict[int, int] = {}
        self.pudding_count: int = 0

    def add_played_card(self, card_name: str):
        """Add a card to this player's played cards."""
        self.played_cards.append(card_name)
        if card_name == "Pudding":
            self.pudding_count += 1

    def set_current_hand(self, hand: list[str]):
        """Update the hand this player currently holds."""
        self.current_hand = hand.copy()

    def has_chopsticks(self) -> bool:
        """Check if player has chopsticks in their tableau."""
        return "Chopsticks" in self.played_cards

    def has_unused_wasabi(self) -> bool:
        """Check if player has a wasabi without a nigiri on it."""
        wasabi_count = self.played_cards.count("Wasabi")
        nigiri_count = sum(
            1 for card in self.played_cards
            if card in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri")
        )
        return wasabi_count > nigiri_count

    def reset_round(self):
        """Reset player state for a new round (keeps puddings)."""
        self.played_cards = [card for card in self.played_cards if card == "Pudding"]
        self.current_hand = []