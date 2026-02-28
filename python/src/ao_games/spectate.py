"""WebSocket spectator for live game/tournament events.

Requires the optional `websockets` dependency:
    pip install ao_games[async]
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator


class AsyncSpectator:
    """Async WebSocket spectator yielding parsed JSON events."""

    def __init__(self, base_url: str = "ws://localhost:7878"):
        self.base_url = base_url.rstrip("/")

    async def spectate_game(self, game_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events from a game's WebSocket stream."""
        import websockets

        url = f"{self.base_url}/ws/games/{game_id}"
        async with websockets.connect(url) as ws:
            async for message in ws:
                yield json.loads(message)

    async def spectate_tournament(self, tournament_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events from a tournament's WebSocket stream."""
        import websockets

        url = f"{self.base_url}/ws/tournaments/{tournament_id}"
        async with websockets.connect(url) as ws:
            async for message in ws:
                yield json.loads(message)
