"""Card enum, dataclasses, and type definitions for the Sushi Go protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Card(Enum):
    """All card types in Sushi Go. Values are 3-letter protocol codes."""
    TEMPURA = "TMP"
    SASHIMI = "SSH"
    DUMPLING = "DMP"
    MAKI_1 = "MK1"
    MAKI_2 = "MK2"
    MAKI_3 = "MK3"
    EGG_NIGIRI = "EGG"
    SALMON_NIGIRI = "SAL"
    SQUID_NIGIRI = "SQD"
    PUDDING = "PUD"
    WASABI = "WAS"
    CHOPSTICKS = "CHP"

    @property
    def code(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        return _CARD_NAMES[self]

    @property
    def is_nigiri(self) -> bool:
        return self in (Card.EGG_NIGIRI, Card.SALMON_NIGIRI, Card.SQUID_NIGIRI)

    @property
    def maki_count(self) -> int:
        return {Card.MAKI_1: 1, Card.MAKI_2: 2, Card.MAKI_3: 3}.get(self, 0)

    @property
    def nigiri_points(self) -> int:
        return {Card.EGG_NIGIRI: 1, Card.SALMON_NIGIRI: 2, Card.SQUID_NIGIRI: 3}.get(self, 0)

    @classmethod
    def from_code(cls, code: str) -> Card:
        """Parse a 3-letter code like 'TMP' -> Card.TEMPURA."""
        try:
            return cls(code)
        except ValueError:
            raise ValueError(f"Unknown card code: {code}")

    @classmethod
    def from_name(cls, name: str) -> Card:
        """Parse a display name like 'Tempura' or 'Salmon Nigiri' -> Card."""
        card = _NAME_TO_CARD.get(name)
        if card is None:
            raise ValueError(f"Unknown card name: {name}")
        return card


_CARD_NAMES: dict[Card, str] = {
    Card.TEMPURA: "Tempura",
    Card.SASHIMI: "Sashimi",
    Card.DUMPLING: "Dumpling",
    Card.MAKI_1: "Maki Roll (1)",
    Card.MAKI_2: "Maki Roll (2)",
    Card.MAKI_3: "Maki Roll (3)",
    Card.EGG_NIGIRI: "Egg Nigiri",
    Card.SALMON_NIGIRI: "Salmon Nigiri",
    Card.SQUID_NIGIRI: "Squid Nigiri",
    Card.PUDDING: "Pudding",
    Card.WASABI: "Wasabi",
    Card.CHOPSTICKS: "Chopsticks",
}

_NAME_TO_CARD: dict[str, Card] = {name: card for card, name in _CARD_NAMES.items()}


@dataclass(frozen=True)
class HandCard:
    """A card in the player's hand with its index."""
    index: int
    card: Card


@dataclass
class RoundScore:
    """Breakdown of points scored in a round."""
    maki_points: int = 0
    tempura_points: int = 0
    sashimi_points: int = 0
    dumpling_points: int = 0
    nigiri_points: int = 0
    total: int = 0


@dataclass
class PlayerStatus:
    """Player status within a game (from STATUS response)."""
    name: str
    has_submitted: bool = False
    puddings: int = 0
    maki_count: int = 0


@dataclass
class GameStatus:
    """Full game status (from STATUS response)."""
    game_id: str
    phase: str
    round: int
    turn: int
    players: list[PlayerStatus] = field(default_factory=list)
    your_played_cards: list[str] = field(default_factory=list)
    your_puddings: int = 0
    your_chopsticks: int = 0
    your_wasabi_slots: int = 0


@dataclass
class GameInfo:
    """Summary info for a game (from REST API / GAMES list)."""
    id: str
    player_count: int
    max_players: int
    status: str


@dataclass
class TournamentInfo:
    """Summary info for a tournament."""
    id: str
    player_count: int
    max_players: int
    match_size: int
    status: str


@dataclass
class TournamentMatchInfo:
    """Info about an assigned tournament match."""
    tournament_id: str
    match_token: str
    round: int
    opponent: str | None = None
