from player import Player
from card import Card
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GameState:
    """Tracks the current state of the entire game."""

    game_id: str
    player_id: int
    my_name: str = ""
    num_players: int = 0
    round: int = 1
    turn: int = 1
    players: dict[str, Player] = field(default_factory=dict)

    # Initial deck composition (card name -> count)
    INITIAL_DECK: dict[str, int] = field(default_factory=lambda: {
        "Tempura": 14,
        "Sashimi": 14,
        "Dumpling": 14,
        "Maki Roll (1)": 6,
        "Maki Roll (2)": 12,
        "Maki Roll (3)": 8,
        "Egg Nigiri": 5,
        "Salmon Nigiri": 10,
        "Squid Nigiri": 5,
        "Pudding": 10,
        "Wasabi": 6,
        "Chopsticks": 4,
    })

    def add_player(self, name: str) -> Player:
        """Add a new player to the game."""
        if name not in self.players:
            self.players[name] = Player(name)
        return self.players[name]

    def get_player(self, name: str) -> Optional[Player]:
        """Get a player by name."""
        return self.players.get(name)

    def get_my_player(self) -> Optional[Player]:
        """Get the Player object representing this bot."""
        return self.players.get(self.my_name)

    def get_cards_remaining(self) -> dict[str, int]:
        """Calculate how many of each card type haven't been seen yet."""
        remaining = self.INITIAL_DECK.copy()

        # Subtract all played cards from all players
        for player in self.players.values():
            for card in player.played_cards:
                if card in remaining:
                    remaining[card] -= 1

        # Subtract cards in my current hand
        my_player = self.get_my_player()
        if my_player:
            for card in my_player.current_hand:
                if card in remaining:
                    remaining[card] -= 1

        return remaining

    def reset_round(self):
        """Reset game state for a new round."""
        self.turn = 1
        for player in self.players.values():
            player.reset_round()