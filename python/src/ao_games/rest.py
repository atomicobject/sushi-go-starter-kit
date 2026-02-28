"""REST client for the Sushi Go server admin/spectating API.

RestClient uses only stdlib urllib (zero deps).
AsyncRestClient requires aiohttp (optional dependency).
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from .errors import SushiGoError
from .types import GameInfo, TournamentInfo


class RestClient:
    """Synchronous REST client using stdlib urllib."""

    def __init__(self, base_url: str = "http://localhost:7878"):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            raise SushiGoError(f"HTTP {e.code}: {body_text}") from e
        except urllib.error.URLError as e:
            raise SushiGoError(f"Request failed: {e}") from e

    def list_games(self) -> list[GameInfo]:
        data = self._request("GET", "/api/games")
        return [
            GameInfo(
                id=g["id"],
                player_count=g["player_count"],
                max_players=g["max_players"],
                status=g["status"],
            )
            for g in data.get("games", data) if isinstance(g, dict)
        ]

    def create_game(self, max_players: int = 2) -> dict:
        return self._request("POST", "/api/games", {"max_players": max_players})

    def get_game(self, game_id: str) -> dict:
        return self._request("GET", f"/api/games/{game_id}")

    def list_tournaments(self) -> list[TournamentInfo]:
        data = self._request("GET", "/api/tournaments")
        return [
            TournamentInfo(
                id=t["id"],
                player_count=t["player_count"],
                max_players=t["max_players"],
                match_size=t.get("match_size", 2),
                status=t["status"],
            )
            for t in data.get("tournaments", data) if isinstance(t, dict)
        ]

    def create_tournament(self, max_players: int = 4, match_size: int = 2) -> dict:
        return self._request(
            "POST",
            "/api/tournaments",
            {"max_players": max_players, "match_size": match_size},
        )

    def get_tournament(self, tournament_id: str) -> dict:
        return self._request("GET", f"/api/tournaments/{tournament_id}")


class AsyncRestClient:
    """Async REST client using aiohttp (optional dependency)."""

    def __init__(self, base_url: str = "http://localhost:7878"):
        self.base_url = base_url.rstrip("/")
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        await self._ensure_session()
        url = f"{self.base_url}{path}"
        async with self._session.request(method, url, json=body) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise SushiGoError(f"HTTP {resp.status}: {text}")
            return await resp.json()

    async def list_games(self) -> list[GameInfo]:
        data = await self._request("GET", "/api/games")
        return [
            GameInfo(
                id=g["id"],
                player_count=g["player_count"],
                max_players=g["max_players"],
                status=g["status"],
            )
            for g in data.get("games", data) if isinstance(g, dict)
        ]

    async def create_game(self, max_players: int = 2) -> dict:
        return await self._request("POST", "/api/games", {"max_players": max_players})

    async def get_game(self, game_id: str) -> dict:
        return await self._request("GET", f"/api/games/{game_id}")

    async def list_tournaments(self) -> list[TournamentInfo]:
        data = await self._request("GET", "/api/tournaments")
        return [
            TournamentInfo(
                id=t["id"],
                player_count=t["player_count"],
                max_players=t["max_players"],
                match_size=t.get("match_size", 2),
                status=t["status"],
            )
            for t in data.get("tournaments", data) if isinstance(t, dict)
        ]

    async def create_tournament(self, max_players: int = 4, match_size: int = 2) -> dict:
        return await self._request(
            "POST",
            "/api/tournaments",
            {"max_players": max_players, "match_size": match_size},
        )

    async def get_tournament(self, tournament_id: str) -> dict:
        return await self._request("GET", f"/api/tournaments/{tournament_id}")
