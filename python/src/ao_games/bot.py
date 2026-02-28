"""Bot framework for Sushi Go.

Provides the Bot ABC and run_bot() / run_tournament_bot() helpers.
Implementing a bot requires only ~15 lines of code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .connection import SyncConnection
from .protocol import (
    GameEndMessage,
    GameStartMessage,
    HandMessage,
    RoundEndMessage,
    RoundStartMessage,
    TournamentCompleteMessage,
    TournamentMatchAssignedMessage,
    TurnResultMessage,
    format_join,
    format_play,
    format_chopsticks,
    format_ready,
    format_tjoin,
    format_tourney,
    parse_server_message,
)
from .state import GameState
from .types import HandCard


class Bot(ABC):
    """Abstract base class for Sushi Go bots.

    Override choose_card() at minimum. Optional hooks provide lifecycle events.
    """

    @abstractmethod
    def choose_card(self, hand: list[HandCard], state: GameState) -> int | tuple[int, int]:
        """Pick a card to play.

        Args:
            hand: Current hand of cards.
            state: Current game state.

        Returns:
            Card index (int) to play, or a tuple of two indices for chopsticks.
        """
        ...

    def on_game_start(self, state: GameState) -> None:
        """Called when the game starts."""

    def on_round_start(self, round_num: int, state: GameState) -> None:
        """Called at the start of each round."""

    def on_turn_result(self, plays: list[tuple[str, list]], state: GameState) -> None:
        """Called when turn results are revealed."""

    def on_round_end(self, round_num: int, state: GameState) -> None:
        """Called at the end of each round."""

    def on_game_end(self, state: GameState) -> None:
        """Called when the game ends."""

    def on_tournament_match(self, state: GameState) -> None:
        """Called when assigned a new tournament match."""

    def on_tournament_complete(self, winner: str, state: GameState) -> None:
        """Called when the tournament is over."""


def _recv_message(conn: SyncConnection):
    """Read lines from the connection, skipping the server welcome banner."""
    while True:
        line = conn.recv_line()
        try:
            return parse_server_message(line)
        except ValueError:
            continue


def _run_game_loop(bot: Bot, conn: SyncConnection, state: GameState) -> GameState:
    """Internal: run the message loop for a single game."""
    while True:
        msg = _recv_message(conn)
        state.update(msg)

        match msg:
            case GameStartMessage():
                bot.on_game_start(state)

            case RoundStartMessage(round=r):
                bot.on_round_start(r, state)

            case HandMessage():
                choice = bot.choose_card(state.hand, state)
                if isinstance(choice, tuple):
                    conn.send_line(format_chopsticks(choice[0], choice[1]))
                else:
                    conn.send_line(format_play(choice))

            case TurnResultMessage(plays=plays):
                bot.on_turn_result(plays, state)

            case RoundEndMessage(round=r):
                bot.on_round_end(r, state)

            case GameEndMessage():
                bot.on_game_end(state)
                return state

            case _:
                pass


def run_bot(
    bot: Bot,
    game_id: str,
    name: str,
    host: str = "localhost",
    port: int = 7878,
    timeout: float = 30.0,
) -> GameState:
    """Connect, join a game, and run the bot until the game ends.

    Args:
        bot: Bot instance.
        game_id: Game to join.
        name: Player name.
        host: Server host.
        port: Server port.
        timeout: Socket timeout in seconds.

    Returns:
        Final GameState.
    """
    conn = SyncConnection(host, port, timeout)
    state = GameState(player_name=name)

    try:
        conn.connect()

        # Join
        conn.send_line(format_join(game_id, name))
        msg = _recv_message(conn)
        state.update(msg)

        # Ready
        conn.send_line(format_ready())
        msg = _recv_message(conn)
        state.update(msg)

        return _run_game_loop(bot, conn, state)
    finally:
        conn.close()


def run_tournament_bot(
    bot: Bot,
    tournament_id: str,
    name: str,
    host: str = "localhost",
    port: int = 7878,
    timeout: float = 60.0,
) -> GameState:
    """Connect, join a tournament, and play all matches until it ends.

    Args:
        bot: Bot instance.
        tournament_id: Tournament to join.
        name: Player name.
        host: Server host.
        port: Server port.
        timeout: Socket timeout in seconds.

    Returns:
        Final GameState.
    """
    conn = SyncConnection(host, port, timeout)
    state = GameState(player_name=name)

    try:
        conn.connect()

        # Join tournament
        conn.send_line(format_tourney(tournament_id, name))
        msg = _recv_message(conn)
        state.update(msg)

        while True:
            line = conn.recv_line()
            msg = parse_server_message(line)
            state.update(msg)

            match msg:
                case TournamentMatchAssignedMessage(match_token=mt):
                    bot.on_tournament_match(state)

                    # Join the match game
                    conn.send_line(format_tjoin(mt))
                    join_msg = _recv_message(conn)
                    state.update(join_msg)

                    # Ready up
                    conn.send_line(format_ready())
                    ready_msg = _recv_message(conn)
                    state.update(ready_msg)

                    # Play the game
                    _run_game_loop(bot, conn, state)

                case TournamentCompleteMessage(winner=winner):
                    bot.on_tournament_complete(winner, state)
                    return state

                case _:
                    pass
    finally:
        conn.close()
