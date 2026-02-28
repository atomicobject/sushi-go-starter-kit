"""High-level game clients wrapping connection + protocol + state."""

from __future__ import annotations

from typing import Callable

from .connection import AsyncConnection, SyncConnection
from .protocol import (
    GameEndMessage,
    HandMessage,
    ServerMessage,
    format_chopsticks,
    format_games,
    format_help,
    format_join,
    format_leave,
    format_play,
    format_ready,
    format_rejoin,
    format_status,
    format_tjoin,
    format_tourney,
    parse_server_message,
)
from .state import GameState
from .types import Card, HandCard


class GameClient:
    """Synchronous game client."""

    def __init__(self, host: str = "localhost", port: int = 7878, timeout: float = 30.0):
        self.conn = SyncConnection(host, port, timeout)
        self.state = GameState()

    def connect(self) -> None:
        self.conn.connect()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def _send(self, cmd: str) -> None:
        self.conn.send_line(cmd)

    def recv_message(self) -> ServerMessage:
        """Receive and parse one server message, updating state."""
        while True:
            line = self.conn.recv_line()
            try:
                msg = parse_server_message(line)
            except ValueError:
                continue  # skip banner/non-protocol lines
            self.state.update(msg)
            return msg

    # -- High-level commands --

    def join(self, game_id: str, player_name: str) -> ServerMessage:
        self.state.player_name = player_name
        self._send(format_join(game_id, player_name))
        return self.recv_message()

    def rejoin(self, token: str) -> ServerMessage:
        self._send(format_rejoin(token))
        return self.recv_message()

    def ready(self) -> ServerMessage:
        self._send(format_ready())
        return self.recv_message()

    def play(self, card_index: int) -> None:
        self._send(format_play(card_index))

    def play_card(self, card: Card) -> None:
        """Play the first card in hand matching the given Card type."""
        for hc in self.state.hand:
            if hc.card == card:
                self.play(hc.index)
                return
        raise ValueError(f"Card {card.display_name} not in hand")

    def chopsticks(self, card_index1: int, card_index2: int) -> None:
        self._send(format_chopsticks(card_index1, card_index2))

    def status(self) -> ServerMessage:
        self._send(format_status())
        return self.recv_message()

    def games(self) -> ServerMessage:
        self._send(format_games())
        return self.recv_message()

    def leave(self) -> None:
        self._send(format_leave())

    def help(self) -> ServerMessage:
        self._send(format_help())
        return self.recv_message()

    def join_tournament(self, tournament_id: str, player_name: str) -> ServerMessage:
        self.state.player_name = player_name
        self._send(format_tourney(tournament_id, player_name))
        return self.recv_message()

    def join_match(self, match_token: str) -> ServerMessage:
        self._send(format_tjoin(match_token))
        return self.recv_message()

    # -- Message loop helpers --

    def wait_for_hand(self) -> HandMessage:
        """Keep receiving messages until a HAND message arrives."""
        while True:
            msg = self.recv_message()
            if isinstance(msg, HandMessage):
                return msg
            if isinstance(msg, GameEndMessage):
                raise StopIteration("Game ended")

    def run_game_loop(self, on_turn: Callable[[list[HandCard], GameState], int | tuple[int, int]]) -> GameState:
        """Run the game loop, calling on_turn for each hand.

        on_turn receives (hand, state) and returns either:
        - int: card index to play
        - tuple[int, int]: two card indices for chopsticks
        """
        while True:
            msg = self.recv_message()
            if isinstance(msg, GameEndMessage):
                return self.state
            if isinstance(msg, HandMessage):
                choice = on_turn(self.state.hand, self.state)
                if isinstance(choice, tuple):
                    self.chopsticks(choice[0], choice[1])
                else:
                    self.play(choice)


class AsyncGameClient:
    """Async game client."""

    def __init__(self, host: str = "localhost", port: int = 7878, timeout: float = 30.0):
        self.conn = AsyncConnection(host, port, timeout)
        self.state = GameState()

    async def connect(self) -> None:
        await self.conn.connect()

    async def close(self) -> None:
        await self.conn.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _send(self, cmd: str) -> None:
        await self.conn.send_line(cmd)

    async def recv_message(self) -> ServerMessage:
        while True:
            line = await self.conn.recv_line()
            try:
                msg = parse_server_message(line)
            except ValueError:
                continue  # skip banner/non-protocol lines
            self.state.update(msg)
            return msg

    async def join(self, game_id: str, player_name: str) -> ServerMessage:
        self.state.player_name = player_name
        await self._send(format_join(game_id, player_name))
        return await self.recv_message()

    async def rejoin(self, token: str) -> ServerMessage:
        await self._send(format_rejoin(token))
        return await self.recv_message()

    async def ready(self) -> ServerMessage:
        await self._send(format_ready())
        return await self.recv_message()

    async def play(self, card_index: int) -> None:
        await self._send(format_play(card_index))

    async def play_card(self, card: Card) -> None:
        for hc in self.state.hand:
            if hc.card == card:
                await self.play(hc.index)
                return
        raise ValueError(f"Card {card.display_name} not in hand")

    async def chopsticks(self, card_index1: int, card_index2: int) -> None:
        await self._send(format_chopsticks(card_index1, card_index2))

    async def status(self) -> ServerMessage:
        await self._send(format_status())
        return await self.recv_message()

    async def games(self) -> ServerMessage:
        await self._send(format_games())
        return await self.recv_message()

    async def leave(self) -> None:
        await self._send(format_leave())

    async def join_tournament(self, tournament_id: str, player_name: str) -> ServerMessage:
        self.state.player_name = player_name
        await self._send(format_tourney(tournament_id, player_name))
        return await self.recv_message()

    async def join_match(self, match_token: str) -> ServerMessage:
        await self._send(format_tjoin(match_token))
        return await self.recv_message()
