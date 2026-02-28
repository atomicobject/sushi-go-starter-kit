"""Protocol message parsing and command formatting.

Handles the text-based TCP protocol between client and server.
Server messages are newline-delimited text; this module provides pure functions
to parse them into typed dataclasses and to format client commands.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .errors import ErrorCode, ProtocolError
from .types import (
    Card,
    GameInfo,
    GameStatus,
    HandCard,
    PlayerStatus,
    RoundScore,
    TournamentMatchInfo,
)

# ---------------------------------------------------------------------------
# Server message dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OkMessage:
    details: str | None = None


@dataclass(frozen=True)
class WelcomeMessage:
    game_id: str
    player_id: int
    rejoin_token: str


@dataclass(frozen=True)
class RejoinedMessage:
    game_id: str
    player_id: int


@dataclass(frozen=True)
class CreatedMessage:
    game_id: str


@dataclass(frozen=True)
class PlayerJoinedMessage:
    player_name: str
    player_count: int
    max_players: int


@dataclass(frozen=True)
class PlayerLeftMessage:
    player_name: str


@dataclass(frozen=True)
class GameStartMessage:
    player_count: int
    move_timeout_ms: int


@dataclass(frozen=True)
class PlayerOrderMessage:
    players: list[str]


@dataclass(frozen=True)
class RoundStartMessage:
    round: int


@dataclass(frozen=True)
class HandMessage:
    cards: list[HandCard]


@dataclass(frozen=True)
class WaitingMessage:
    players: list[str]


@dataclass(frozen=True)
class TurnResultMessage:
    """PLAYED message: each entry is (player_name, [Card, ...])."""
    plays: list[tuple[str, list[Card]]]


@dataclass
class RoundEndMessage:
    round: int
    scores: dict[str, RoundScore]


@dataclass
class GameEndMessage:
    final_scores: dict[str, int]
    winners: list[str]
    next_game_id: str | None = None
    tournament_winner: str | None = None


@dataclass(frozen=True)
class StatusMessage:
    status: GameStatus


@dataclass(frozen=True)
class GamesListMessage:
    games: list[GameInfo]


@dataclass(frozen=True)
class TournamentWelcomeMessage:
    tournament_id: str
    player_count: int
    max_players: int
    rejoin_token: str


@dataclass(frozen=True)
class TournamentRejoinedMessage:
    tournament_id: str
    player_name: str
    current_match_token: str | None = None


@dataclass(frozen=True)
class TournamentPlayerJoinedMessage:
    tournament_id: str
    player_name: str
    player_count: int
    max_players: int


@dataclass(frozen=True)
class TournamentMatchAssignedMessage:
    tournament_id: str
    match_token: str
    round: int
    opponent: str | None = None


@dataclass(frozen=True)
class TournamentCompleteMessage:
    tournament_id: str
    winner: str


type ServerMessage = (
    OkMessage
    | WelcomeMessage
    | RejoinedMessage
    | CreatedMessage
    | PlayerJoinedMessage
    | PlayerLeftMessage
    | GameStartMessage
    | PlayerOrderMessage
    | RoundStartMessage
    | HandMessage
    | WaitingMessage
    | TurnResultMessage
    | RoundEndMessage
    | GameEndMessage
    | StatusMessage
    | GamesListMessage
    | TournamentWelcomeMessage
    | TournamentRejoinedMessage
    | TournamentPlayerJoinedMessage
    | TournamentMatchAssignedMessage
    | TournamentCompleteMessage
)

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Pattern to split "0:Tempura 1:Sashimi 2:Salmon Nigiri" into tokens.
# Each token starts with <digit>: and extends until the next <digit>: or end.
_HAND_TOKEN_RE = re.compile(r"(\d+):(.+?)(?=\s+\d+:|$)")


def _parse_hand(payload: str) -> list[HandCard]:
    cards: list[HandCard] = []
    for m in _HAND_TOKEN_RE.finditer(payload):
        idx = int(m.group(1))
        name = m.group(2).strip()
        cards.append(HandCard(index=idx, card=Card.from_name(name)))
    return cards


def _parse_played(payload: str) -> list[tuple[str, list[Card]]]:
    """Parse 'Alice:TMP; Bob:MK3,WAS'."""
    plays: list[tuple[str, list[Card]]] = []
    for entry in payload.split("; "):
        entry = entry.strip()
        if not entry:
            continue
        name, codes_str = entry.split(":", 1)
        cards = [Card.from_code(c.strip()) for c in codes_str.split(",") if c.strip()]
        plays.append((name, cards))
    return plays


def _parse_round_score(d: dict) -> RoundScore:
    return RoundScore(
        maki_points=d.get("maki_points", 0),
        tempura_points=d.get("tempura_points", 0),
        sashimi_points=d.get("sashimi_points", 0),
        dumpling_points=d.get("dumpling_points", 0),
        nigiri_points=d.get("nigiri_points", 0),
        total=d.get("total", 0),
    )


def _parse_game_end(payload: str) -> GameEndMessage:
    """Parse 'GAME_END {...} WINNER:Alice,Bob [NEXT:id] [TOURNAMENT_WINNER:name]'."""
    # Find JSON object
    json_start = payload.index("{")
    depth = 0
    json_end = json_start
    for i, ch in enumerate(payload[json_start:], json_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_end = i
                break
    json_str = payload[json_start : json_end + 1]
    final_scores: dict[str, int] = json.loads(json_str)

    rest = payload[json_end + 1 :].strip()

    winners: list[str] = []
    next_game_id: str | None = None
    tournament_winner: str | None = None

    for part in rest.split():
        if part.startswith("WINNER:"):
            winners = part[len("WINNER:") :].split(",")
        elif part.startswith("NEXT:"):
            next_game_id = part[len("NEXT:") :]
        elif part.startswith("TOURNAMENT_WINNER:"):
            tournament_winner = part[len("TOURNAMENT_WINNER:") :]

    return GameEndMessage(
        final_scores=final_scores,
        winners=winners,
        next_game_id=next_game_id,
        tournament_winner=tournament_winner,
    )


def _parse_status_json(payload: str) -> GameStatus:
    d = json.loads(payload)
    players = [
        PlayerStatus(
            name=p["name"],
            has_submitted=p.get("has_submitted", False),
            puddings=p.get("puddings", 0),
            maki_count=p.get("maki_count", 0),
        )
        for p in d.get("players", [])
    ]
    return GameStatus(
        game_id=d["game_id"],
        phase=d["phase"],
        round=d["round"],
        turn=d["turn"],
        players=players,
        your_played_cards=d.get("your_played_cards", []),
        your_puddings=d.get("your_puddings", 0),
        your_chopsticks=d.get("your_chopsticks", 0),
        your_wasabi_slots=d.get("your_wasabi_slots", 0),
    )


def _parse_games_list(payload: str) -> list[GameInfo]:
    items = json.loads(payload)
    return [
        GameInfo(
            id=g["id"],
            player_count=g["player_count"],
            max_players=g["max_players"],
            status=g["status"],
        )
        for g in items
    ]


def parse_server_message(line: str) -> ServerMessage:
    """Parse a single line from the server into a typed message."""
    line = line.strip()
    if not line:
        raise ValueError("Empty message")

    keyword, _, payload = line.partition(" ")

    match keyword:
        case "OK":
            return OkMessage(details=payload if payload else None)

        case "ERROR":
            raise ProtocolError.from_line(line)

        case "WELCOME":
            parts = payload.split()
            return WelcomeMessage(
                game_id=parts[0],
                player_id=int(parts[1]),
                rejoin_token=parts[2],
            )

        case "REJOINED":
            parts = payload.split()
            return RejoinedMessage(game_id=parts[0], player_id=int(parts[1]))

        case "CREATED":
            return CreatedMessage(game_id=payload.strip())

        case "JOINED":
            # "PlayerName 2/4"
            parts = payload.rsplit(None, 1)
            player_name = parts[0]
            count, max_p = parts[1].split("/")
            return PlayerJoinedMessage(
                player_name=player_name,
                player_count=int(count),
                max_players=int(max_p),
            )

        case "LEFT":
            return PlayerLeftMessage(player_name=payload.strip())

        case "GAME_START":
            parts = payload.split()
            return GameStartMessage(
                player_count=int(parts[0]),
                move_timeout_ms=int(parts[1]),
            )

        case "PLAYER_ORDER":
            players = payload.strip().split(",") if payload.strip() else []
            return PlayerOrderMessage(players=players)

        case "ROUND_START":
            return RoundStartMessage(round=int(payload.strip()))

        case "HAND":
            return HandMessage(cards=_parse_hand(payload))

        case "WAITING":
            return WaitingMessage(players=payload.split())

        case "PLAYED":
            return TurnResultMessage(plays=_parse_played(payload))

        case "ROUND_END":
            parts = payload.split(None, 1)
            round_num = int(parts[0])
            scores_raw: dict[str, dict] = json.loads(parts[1])
            scores = {name: _parse_round_score(s) for name, s in scores_raw.items()}
            return RoundEndMessage(round=round_num, scores=scores)

        case "GAME_END":
            return _parse_game_end(payload)

        case "STATUS":
            return StatusMessage(status=_parse_status_json(payload))

        case "GAMES":
            return GamesListMessage(games=_parse_games_list(payload))

        case "TOURNAMENT_WELCOME":
            parts = payload.split()
            count, max_p = parts[1].split("/")
            return TournamentWelcomeMessage(
                tournament_id=parts[0],
                player_count=int(count),
                max_players=int(max_p),
                rejoin_token=parts[2],
            )

        case "TOURNAMENT_REJOINED":
            parts = payload.split()
            return TournamentRejoinedMessage(
                tournament_id=parts[0],
                player_name=parts[1],
                current_match_token=parts[2] if len(parts) > 2 else None,
            )

        case "TOURNAMENT_JOINED":
            parts = payload.split()
            count, max_p = parts[2].split("/")
            return TournamentPlayerJoinedMessage(
                tournament_id=parts[0],
                player_name=parts[1],
                player_count=int(count),
                max_players=int(max_p),
            )

        case "TOURNAMENT_MATCH":
            parts = payload.split()
            opponent: str | None = parts[3] if len(parts) > 3 else None
            if opponent == "BYE":
                opponent = None
            return TournamentMatchAssignedMessage(
                tournament_id=parts[0],
                match_token=parts[1],
                round=int(parts[2]),
                opponent=opponent,
            )

        case "TOURNAMENT_COMPLETE":
            parts = payload.split()
            return TournamentCompleteMessage(
                tournament_id=parts[0],
                winner=parts[1],
            )

        case _:
            raise ValueError(f"Unknown server message keyword: {keyword}")


# ---------------------------------------------------------------------------
# Command formatting
# ---------------------------------------------------------------------------


def format_join(game_id: str, player_name: str) -> str:
    return f"JOIN {game_id} {player_name}"


def format_rejoin(token: str) -> str:
    return f"REJOIN {token}"


def format_ready() -> str:
    return "READY"


def format_play(card_index: int) -> str:
    return f"PLAY {card_index}"


def format_chopsticks(card_index1: int, card_index2: int) -> str:
    return f"CHOPSTICKS {card_index1} {card_index2}"


def format_status() -> str:
    return "STATUS"


def format_games() -> str:
    return "GAMES"


def format_leave() -> str:
    return "LEAVE"


def format_help() -> str:
    return "HELP"


def format_tourney(tournament_id: str, player_name: str) -> str:
    return f"TOURNEY {tournament_id} {player_name}"


def format_tjoin(match_token: str) -> str:
    return f"TJOIN {match_token}"
