"""ao_games — Python SDK for the Sushi Go game server."""

from ._version import __version__
from .bot import Bot, run_bot, run_tournament_bot
from .errors import (
    ConnectionError,
    ErrorCode,
    ProtocolError,
    SushiGoError,
    TimeoutError,
)
from .game import AsyncGameClient, GameClient
from .rest import AsyncRestClient, RestClient
from .state import GameState
from .types import (
    Card,
    GameInfo,
    GameStatus,
    HandCard,
    PlayerStatus,
    RoundScore,
    TournamentInfo,
    TournamentMatchInfo,
)

__all__ = [
    "__version__",
    # Bot framework
    "Bot",
    "run_bot",
    "run_tournament_bot",
    # Game clients
    "GameClient",
    "AsyncGameClient",
    "GameState",
    # REST clients
    "RestClient",
    "AsyncRestClient",
    # Types
    "Card",
    "HandCard",
    "RoundScore",
    "PlayerStatus",
    "GameStatus",
    "GameInfo",
    "TournamentInfo",
    "TournamentMatchInfo",
    # Errors
    "SushiGoError",
    "ProtocolError",
    "ConnectionError",
    "TimeoutError",
    "ErrorCode",
]
