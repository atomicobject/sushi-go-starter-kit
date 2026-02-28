"""Game state tracker that updates from server messages."""

from __future__ import annotations

from dataclasses import dataclass, field

from .protocol import (
    GameEndMessage,
    GameStartMessage,
    HandMessage,
    OkMessage,
    PlayerJoinedMessage,
    PlayerLeftMessage,
    PlayerOrderMessage,
    RejoinedMessage,
    RoundEndMessage,
    RoundStartMessage,
    ServerMessage,
    StatusMessage,
    TournamentCompleteMessage,
    TournamentMatchAssignedMessage,
    TournamentWelcomeMessage,
    TurnResultMessage,
    WaitingMessage,
    WelcomeMessage,
)
from .types import Card, HandCard, RoundScore


@dataclass
class GameState:
    """Tracks the full game state by processing server messages."""

    game_id: str = ""
    player_id: int = -1
    rejoin_token: str = ""
    player_name: str = ""

    phase: str = "lobby"  # lobby, playing, ended
    round: int = 0
    turn: int = 0
    player_count: int = 0
    max_players: int = 0
    move_timeout_ms: int = 0

    hand: list[HandCard] = field(default_factory=list)
    players: list[str] = field(default_factory=list)
    player_order: list[str] = field(default_factory=list)

    # Per-round tracking
    last_plays: list[tuple[str, list[Card]]] = field(default_factory=list)
    round_scores: dict[int, dict[str, RoundScore]] = field(default_factory=dict)

    # End-of-game
    final_scores: dict[str, int] = field(default_factory=dict)
    winners: list[str] = field(default_factory=list)
    next_game_id: str | None = None
    tournament_winner: str | None = None

    # Tournament
    tournament_id: str = ""
    match_token: str = ""
    tournament_round: int = 0
    tournament_opponent: str | None = None

    def update(self, msg: ServerMessage) -> None:
        """Update state from a parsed server message."""
        match msg:
            case WelcomeMessage(game_id=gid, player_id=pid, rejoin_token=tok):
                self.game_id = gid
                self.player_id = pid
                self.rejoin_token = tok
                self.phase = "lobby"

            case RejoinedMessage(game_id=gid, player_id=pid):
                self.game_id = gid
                self.player_id = pid

            case PlayerJoinedMessage(player_name=name, player_count=pc, max_players=mp):
                self.player_count = pc
                self.max_players = mp
                if name not in self.players:
                    self.players.append(name)

            case PlayerLeftMessage(player_name=name):
                if name in self.players:
                    self.players.remove(name)
                    self.player_count = len(self.players)

            case GameStartMessage(player_count=pc, move_timeout_ms=timeout):
                self.player_count = pc
                self.move_timeout_ms = timeout
                self.phase = "playing"
                self.round = 0
                self.turn = 0

            case PlayerOrderMessage(players=p):
                self.player_order = list(p)

            case RoundStartMessage(round=r):
                self.round = r
                self.turn = 0
                self.last_plays = []

            case HandMessage(cards=cards):
                self.hand = list(cards)
                self.turn += 1

            case WaitingMessage():
                pass

            case TurnResultMessage(plays=plays):
                self.last_plays = plays

            case RoundEndMessage(round=r, scores=scores):
                self.round_scores[r] = scores

            case GameEndMessage(
                final_scores=fs, winners=w, next_game_id=nid, tournament_winner=tw
            ):
                self.final_scores = fs
                self.winners = w
                self.next_game_id = nid
                self.tournament_winner = tw
                self.phase = "ended"

            case StatusMessage(status=s):
                self.game_id = s.game_id
                self.phase = s.phase
                self.round = s.round
                self.turn = s.turn

            case TournamentWelcomeMessage(tournament_id=tid):
                self.tournament_id = tid

            case TournamentMatchAssignedMessage(
                tournament_id=tid, match_token=mt, round=r, opponent=opp
            ):
                self.tournament_id = tid
                self.match_token = mt
                self.tournament_round = r
                self.tournament_opponent = opp
                # Reset game state for new match
                self.phase = "lobby"
                self.round = 0
                self.turn = 0
                self.hand = []
                self.last_plays = []
                self.round_scores = {}
                self.final_scores = {}
                self.winners = []
                self.next_game_id = None

            case TournamentCompleteMessage(tournament_id=tid, winner=w):
                self.tournament_winner = w

            case _:
                pass
