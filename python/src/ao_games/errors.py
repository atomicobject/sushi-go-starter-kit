"""Error types for the Sushi Go protocol."""

from enum import IntEnum


class ErrorCode(IntEnum):
    """Error codes matching the server protocol (E001-E018)."""
    INVALID_COMMAND = 1
    NOT_YOUR_TURN = 2
    INVALID_CARD_INDEX = 3
    NO_CHOPSTICKS = 4
    GAME_NOT_FOUND = 5
    GAME_ALREADY_STARTED = 6
    NAME_TAKEN = 7
    ALREADY_SUBMITTED = 8
    DUPLICATE_INDEX = 9
    GAME_FULL = 10
    PLAYER_NOT_FOUND = 11
    GAME_ENDED = 12
    NOT_IN_GAME = 13
    INTERNAL_ERROR = 14
    TOURNAMENT_NOT_FOUND = 15
    TOURNAMENT_FULL = 16
    TOURNAMENT_ALREADY_STARTED = 17
    INVALID_TOURNAMENT_PLAYER_COUNT = 18

    @property
    def code_str(self) -> str:
        """E.g. 'E001'."""
        return f"E{self.value:03d}"

    @property
    def default_message(self) -> str:
        return _DEFAULT_MESSAGES[self]

    @classmethod
    def from_code_str(cls, code: str) -> "ErrorCode":
        """Parse 'E001' -> ErrorCode.INVALID_COMMAND."""
        if code.startswith("E") and len(code) == 4:
            return cls(int(code[1:]))
        raise ValueError(f"Invalid error code format: {code}")


_DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_COMMAND: "Invalid command format",
    ErrorCode.NOT_YOUR_TURN: "Not your turn or game not ready",
    ErrorCode.INVALID_CARD_INDEX: "Invalid card index",
    ErrorCode.NO_CHOPSTICKS: "No chopsticks available",
    ErrorCode.GAME_NOT_FOUND: "Game not found",
    ErrorCode.GAME_ALREADY_STARTED: "Game has already started",
    ErrorCode.NAME_TAKEN: "Name already taken",
    ErrorCode.ALREADY_SUBMITTED: "Already submitted move this turn",
    ErrorCode.DUPLICATE_INDEX: "Cannot use same card index twice",
    ErrorCode.GAME_FULL: "Game is full",
    ErrorCode.PLAYER_NOT_FOUND: "Player not found",
    ErrorCode.GAME_ENDED: "Game has ended",
    ErrorCode.NOT_IN_GAME: "Not in a game",
    ErrorCode.INTERNAL_ERROR: "Internal server error",
    ErrorCode.TOURNAMENT_NOT_FOUND: "Tournament not found",
    ErrorCode.TOURNAMENT_FULL: "Tournament is full",
    ErrorCode.TOURNAMENT_ALREADY_STARTED: "Tournament has already started",
    ErrorCode.INVALID_TOURNAMENT_PLAYER_COUNT: "Invalid tournament player count (must be 4-50)",
}


class SushiGoError(Exception):
    """Base exception for the Sushi Go SDK."""


class ProtocolError(SushiGoError):
    """Error received from the server with an error code."""

    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code.code_str} {message}")

    @classmethod
    def from_line(cls, line: str) -> "ProtocolError":
        """Parse 'ERROR E001 Invalid command format'."""
        parts = line.split(None, 2)
        if len(parts) < 3 or parts[0] != "ERROR":
            raise ValueError(f"Not an error line: {line}")
        code = ErrorCode.from_code_str(parts[1])
        return cls(code, parts[2])


class ConnectionError(SushiGoError):
    """Connection-level error."""


class TimeoutError(SushiGoError):
    """Operation timed out."""
