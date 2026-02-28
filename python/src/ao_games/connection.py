"""Low-level TCP connections for the Sushi Go protocol.

Provides SyncConnection (stdlib socket) and AsyncConnection (asyncio).
Both send/receive newline-delimited text lines.
"""

from __future__ import annotations

import socket
from typing import Self

from .errors import ConnectionError, TimeoutError

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0


class SyncConnection:
    """Synchronous TCP connection using stdlib socket."""

    def __init__(self, host: str = "localhost", port: int = 7878, timeout: float = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._file = None

    def connect(self) -> None:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._file = self._sock.makefile("r")
        except socket.timeout as e:
            raise TimeoutError(f"Connection timed out: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}") from e

    def send_line(self, line: str) -> None:
        if self._sock is None:
            raise ConnectionError("Not connected")
        try:
            self._sock.sendall((line + "\n").encode())
        except socket.timeout as e:
            raise TimeoutError(f"Send timed out: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Send failed: {e}") from e

    def recv_line(self) -> str:
        if self._file is None:
            raise ConnectionError("Not connected")
        try:
            line = self._file.readline()
            if not line:
                raise ConnectionError("Server closed connection")
            return line.strip()
        except socket.timeout as e:
            raise TimeoutError(f"Receive timed out: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Receive failed: {e}") from e

    def close(self) -> None:
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class AsyncConnection:
    """Async TCP connection using asyncio streams."""

    def __init__(self, host: str = "localhost", port: int = 7878, timeout: float = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader = None
        self._writer = None

    async def connect(self) -> None:
        import asyncio

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"Connection timed out: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}") from e

    async def send_line(self, line: str) -> None:
        if self._writer is None:
            raise ConnectionError("Not connected")
        try:
            self._writer.write((line + "\n").encode())
            await self._writer.drain()
        except OSError as e:
            raise ConnectionError(f"Send failed: {e}") from e

    async def recv_line(self) -> str:
        import asyncio

        if self._reader is None:
            raise ConnectionError("Not connected")
        try:
            data = await asyncio.wait_for(
                self._reader.readline(),
                timeout=self.timeout,
            )
            if not data:
                raise ConnectionError("Server closed connection")
            return data.decode().strip()
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"Receive timed out: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Receive failed: {e}") from e

    async def close(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except OSError:
                pass
            self._writer = None
            self._reader = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()
