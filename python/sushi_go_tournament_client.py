#!/usr/bin/env python3
"""
Sushi Go Tournament Client - Python Starter Kit

This client connects to the Sushi Go server and plays through an entire tournament
using a simple strategy. Modify the `choose_card` method to implement your own AI!

Usage:
    python sushi_go_tournament_client.py <server_host> <server_port> <tournament_id> <player_name>

Example:
    python sushi_go_tournament_client.py localhost 7878 spicy-salmon MyBot
"""

import random
import re
import socket
import sys
from dataclasses import dataclass, field
from typing import Optional

# Card names used by the protocol (now using full names instead of codes)
CARD_NAMES = {
    "Tempura": "Tempura",
    "Sashimi": "Sashimi",
    "Dumpling": "Dumpling",
    "Maki Roll (1)": "Maki Roll (1)",
    "Maki Roll (2)": "Maki Roll (2)",
    "Maki Roll (3)": "Maki Roll (3)",
    "Egg Nigiri": "Egg Nigiri",
    "Salmon Nigiri": "Salmon Nigiri",
    "Squid Nigiri": "Squid Nigiri",
    "Pudding": "Pudding",
    "Wasabi": "Wasabi",
    "Chopsticks": "Chopsticks",
}


@dataclass
class GameState:
    """Tracks the current state of a single game within the tournament."""

    game_id: str = ""
    player_id: int = 0
    rejoin_token: str = ""
    hand: list[str] = field(default_factory=list)
    round: int = 1
    turn: int = 1
    played_cards: list[str] = field(default_factory=list)
    has_chopsticks: bool = False
    has_unused_wasabi: bool = False
    puddings: int = 0


class SushiGoTournamentClient:
    """A client for playing Sushi Go tournaments."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.state: Optional[GameState] = None
        self._recv_buffer = ""
        # Tournament state
        self.tournament_id: str = ""
        self.tournament_rejoin_token: str = ""

    def connect(self):
        """Connect to the server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self._recv_buffer = ""
        print(f"Connected to {self.host}:{self.port}")

    def disconnect(self):
        """Disconnect from the server."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, command: str):
        """Send a command to the server."""
        message = command + "\n"
        self.sock.sendall(message.encode("utf-8"))
        print(f">>> {command}")

    def receive(self) -> str:
        """Receive one line-delimited message from the server."""
        while True:
            if "\n" in self._recv_buffer:
                line, self._recv_buffer = self._recv_buffer.split("\n", 1)
                message = line.strip()
                print(f"<<< {message}")
                return message

            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self._recv_buffer += chunk.decode("utf-8", errors="replace")

    def receive_until(self, predicate) -> str:
        """Read lines until one matches predicate."""
        while True:
            message = self.receive()
            if not message:
                continue
            if predicate(message):
                return message

    def join_tournament(self, tournament_id: str, player_name: str) -> bool:
        """Join a tournament."""
        self.tournament_id = tournament_id
        self.send(f"TOURNEY {tournament_id} {player_name}")
        response = self.receive_until(
            lambda line: line.startswith("TOURNAMENT_WELCOME") or line.startswith("ERROR")
        )

        if response.startswith("TOURNAMENT_WELCOME"):
            # TOURNAMENT_WELCOME <tid> <count>/<max> <rejoin_token>
            parts = response.split()
            self.tournament_rejoin_token = parts[3] if len(parts) > 3 else ""
            print(f"Joined tournament {tournament_id} (rejoin token: {self.tournament_rejoin_token})")
            return True
        elif response.startswith("ERROR"):
            print(f"Failed to join tournament: {response}")
            return False
        return False

    def join_match(self, match_token: str) -> bool:
        """Join a tournament match using TJOIN."""
        self.send(f"TJOIN {match_token}")
        response = self.receive_until(
            lambda line: line.startswith("WELCOME") or line.startswith("ERROR")
        )

        if response.startswith("WELCOME"):
            parts = response.split()
            rejoin_token = parts[3] if len(parts) > 3 else ""
            self.state = GameState(
                game_id=parts[1],
                player_id=int(parts[2]),
                rejoin_token=rejoin_token,
            )
            print(f"Joined match (game: {self.state.game_id})")
            return True
        elif response.startswith("ERROR"):
            print(f"Failed to join match: {response}")
            return False
        return False

    def signal_ready(self):
        """Signal that we're ready to start."""
        self.send("READY")
        return self.receive()

    def leave_game(self):
        """Leave the current game so we can join the next match."""
        self.send("LEAVE")
        self.receive_until(
            lambda line: line.startswith("OK") or line.startswith("ERROR")
        )
        self.state = None

    def play_card(self, card_index: int):
        """Play a card by index."""
        self.send(f"PLAY {card_index}")
        return self.receive()

    def play_chopsticks(self, index1: int, index2: int):
        """Use chopsticks to play two cards."""
        self.send(f"CHOPSTICKS {index1} {index2}")
        return self.receive()

    def parse_hand(self, message: str):
        """Parse a HAND message and update state."""
        if message.startswith("HAND"):
            payload = message[len("HAND "):]
            cards = []
            for match in re.finditer(r"(\d+):(.*?)(?=\s\d+:|$)", payload):
                cards.append(match.group(2).strip())
            if self.state:
                self.state.hand = cards
                # Update chopsticks/wasabi tracking based on played cards
                self.state.has_chopsticks = "Chopsticks" in self.state.played_cards
                self.state.has_unused_wasabi = any(
                    c == "Wasabi" for c in self.state.played_cards
                ) and not any(
                    c in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri")
                    for c in self.state.played_cards
                )

    def choose_card(self, hand: list[str]) -> int:
        """
        Choose which card to play.

        This is where you implement your AI strategy!
        The default implementation uses a simple priority-based approach.

        Args:
            hand: List of card codes in your current hand

        Returns:
            Index of the card to play (0-based)
        """
        # Simple priority-based strategy
        priority = [
            "Squid Nigiri",  # 3 points, or 9 with wasabi
            "Salmon Nigiri",  # 2 points, or 6 with wasabi
            "Maki Roll (3)",  # 3 maki rolls
            "Maki Roll (2)",  # 2 maki rolls
            "Tempura",  # 5 points per pair
            "Sashimi",  # 10 points per set of 3
            "Dumpling",  # Increasing value
            "Wasabi",  # Triples next nigiri
            "Egg Nigiri",  # 1 point, or 3 with wasabi
            "Pudding",  # End game scoring
            "Maki Roll (1)",  # 1 maki roll
            "Chopsticks",  # Play 2 cards next turn
        ]

        # If we have wasabi, prioritize nigiri
        if self.state and self.state.has_unused_wasabi:
            for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
                if nigiri in hand:
                    return hand.index(nigiri)

        # Otherwise use priority list
        for card in priority:
            if card in hand:
                return hand.index(card)

        # Fallback: random
        return random.randint(0, len(hand) - 1)

    def handle_game_message(self, message: str) -> bool:
        """Handle an in-game message. Returns False on GAME_END."""
        if message.startswith("HAND"):
            self.parse_hand(message)
        elif message.startswith("ROUND_START"):
            parts = message.split()
            if self.state:
                self.state.round = int(parts[1])
                self.state.turn = 1
                self.state.played_cards = []
        elif message.startswith("PLAYED"):
            if self.state:
                self.state.turn += 1
        elif message.startswith("ROUND_END"):
            if self.state:
                self.state.played_cards = []
        elif message.startswith("GAME_END"):
            print("Game over!")
            return False
        return True

    def play_turn(self):
        """Play a single turn."""
        if not self.state or not self.state.hand:
            return

        card_index = self.choose_card(self.state.hand)
        played_card = self.state.hand[card_index]

        response = self.play_card(card_index)

        if response.startswith("OK"):
            if self.state:
                self.state.played_cards.append(played_card)

    def play_game(self) -> Optional[str]:
        """Play a full game. Returns a tournament message if one arrived during the game, else None."""
        while True:
            message = self.receive()

            # Tournament messages can arrive during a game
            if message.startswith("TOURNAMENT_MATCH") or message.startswith("TOURNAMENT_COMPLETE"):
                return message

            game_running = self.handle_game_message(message)

            if message.startswith("HAND") and self.state and self.state.hand:
                self.play_turn()

            if not game_running:
                return None

    def run(self, tournament_id: str, player_name: str):
        """Main tournament loop."""
        try:
            self.connect()

            if not self.join_tournament(tournament_id, player_name):
                return

            pending_message = None

            # Tournament loop — wait for match assignments
            while True:
                if pending_message:
                    msg = pending_message
                    pending_message = None
                else:
                    msg = self.receive()

                if not msg:
                    continue

                if msg.startswith("TOURNAMENT_MATCH"):
                    # TOURNAMENT_MATCH <tid> <match_token> <round> [<opponent>]
                    parts = msg.split()
                    match_token = parts[2]
                    round_num = parts[3]
                    opponent = parts[4] if len(parts) > 4 else "unknown"

                    if match_token == "BYE" or opponent == "BYE":
                        print(f"Round {round_num}: got a BYE, auto-advancing...")
                        continue

                    print(f"Round {round_num}: matched vs {opponent}")

                    if not self.join_match(match_token):
                        continue

                    self.signal_ready()

                    # Play the game — may return a tournament message that arrived mid-game
                    pending_message = self.play_game()

                    # Leave the game so we can join the next match
                    self.leave_game()

                elif msg.startswith("TOURNAMENT_COMPLETE"):
                    # TOURNAMENT_COMPLETE <tid> <winner>
                    parts = msg.split()
                    winner = parts[2] if len(parts) > 2 else "unknown"
                    print(f"Tournament complete! Winner: {winner}")
                    break

                elif msg.startswith("TOURNAMENT_JOINED"):
                    print(f"  {msg}")

                # Ignore other messages

        except KeyboardInterrupt:
            print("\nDisconnecting...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.disconnect()


def main():
    if len(sys.argv) != 5:
        print("Usage: python sushi_go_tournament_client.py <host> <port> <tournament_id> <player_name>")
        print("Example: python sushi_go_tournament_client.py localhost 7878 spicy-salmon MyBot")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    tournament_id = sys.argv[3]
    player_name = sys.argv[4]

    client = SushiGoTournamentClient(host, port)
    client.run(tournament_id, player_name)


if __name__ == "__main__":
    main()
