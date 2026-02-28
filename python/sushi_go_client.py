#!/usr/bin/env python3
"""
Sushi Go Client - Python Starter Kit

This client connects to the Sushi Go server and plays using a simple strategy.
Modify the `choose_card` method to implement your own AI!

Usage:
    python sushi_go_client.py <server_host> <server_port> <game_id> <player_name>

Example:
    python sushi_go_client.py localhost 7878 abc123 MyBot
"""

import random
import re
import socket
import sys
from dataclasses import dataclass
from typing import Optional


print("DEBUG: Running sushi_go_client.py with rogelio/pudding-logic changes")  # ADD THIS LINE
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
    """Tracks the current state of the game."""

    game_id: str
    player_id: int
    hand: list[str]
    round: int = 1
    turn: int = 1
    played_cards: list[str] = None
    has_chopsticks: bool = False
    has_unused_wasabi: bool = False
    puddings: int = 0

    def __post_init__(self):
        if self.played_cards is None:
            self.played_cards = []


class SushiGoClient:
    """A client for playing Sushi Go."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.state: Optional[GameState] = None
        self._recv_buffer = ""

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

    def join_game(self, game_id: str, player_name: str) -> bool:
        """Join a game."""
        self.send(f"JOIN {game_id} {player_name}")
        response = self.receive_until(
            lambda line: line.startswith("WELCOME") or line.startswith("ERROR")
        )

        if response.startswith("WELCOME"):
            parts = response.split()
            self.state = GameState(game_id=parts[1], player_id=int(parts[2]), hand=[])
            return True
        elif response.startswith("ERROR"):
            print(f"Failed to join: {response}")
            return False
        return False

    def signal_ready(self):
        """Signal that we're ready to start."""
        self.send("READY")
        return self.receive()

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
            payload = message[len("HAND ") :]
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

        print(f"DEBUG TURN: {self.state.turn}")
        if self.state.turn % 10 == 0:
            self.state.round += 1
        print(f"DEBUG ROUND: {self.state.round}")


        # SET COMPLETION 

        # Sashimi set of 3 
        if self.count_card("Sashimi") == 2 and "Sashimi" in hand:
            print("DEBUG: SASHIMI SET OF 3 MADE")
            return hand.index("Sashimi")
        
        # Tempura pair 
        if self.count_card("Tempura") == 1 and "Tempura" in hand:
            print("DEBUG: Tempura SET OF 3 MADE")
            return hand.index("Tempura")

        # Dumpling sets
        total_dumplings = self.count_card("Dumplings")
        if self.count_card("Dumpling") >= 1 and "Dumpling" in hand:
            print(f"DEBUG: Total dumplings = {total_dumplings}\nGRABBING DUMPLING")
            return hand.index("Dumpling")

        # If we have wasabi, prioritize nigiri
        if self.state and self.state.has_unused_wasabi:
            for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
                if nigiri in hand:
                    return hand.index(nigiri)


        # Pudding logic
        if self.state and (self.state.round != 1):
            for pud in hand:
                if pud == "Pudding":
                    print("PUDDING GRABBED")
                    return hand.index(pud)
        else:
                if self.state:
                    print(f"DEBUG: Round is {self.state.round}, pudding logic skipped")

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
        
        # Otherwise use priority list
        for card in priority:
            if card in hand:
                return hand.index(card)
        
    def count_card(self, card_name:str ) -> int :
        """Returns the total amount of times a card has been played"""
        return self.state.played_cards.count(card_name)


    
    def handle_message(self, message: str):
        """Handle a message from the server."""
        if message.startswith("HAND"):
            self.parse_hand(message)
        elif message.startswith("ROUND_START"):
            parts = message.split()
            if self.state:
                self.state.round = int(parts[1])
                self.state.turn = 1
                self.state.played_cards = []
        elif message.startswith("PLAYED"):
            # Cards were revealed, next turn
            if self.state:
                self.state.turn += 1
        elif message.startswith("ROUND_END"):
            # Round ended
            if self.state:
                self.state.played_cards = []
        elif message.startswith("GAME_END"):
            print("Game over!")
            return False
        elif message.startswith("WAITING"):
            # Our move was accepted, waiting for others
            pass
        return True

    def play_turn(self):
        """Play a single turn."""
        if not self.state or not self.state.hand:
            return

        card_index = self.choose_card(self.state.hand)

        # Track the card we're about to play
        played_card = self.state.hand[card_index]

        response = self.play_card(card_index)

        if response.startswith("OK"):
            if self.state:
                self.state.played_cards.append(played_card)

    def run(self, game_id: str, player_name: str):
        """Main game loop."""
        try:
            self.connect()

            if not self.join_game(game_id, player_name):
                return

            # Signal ready
            response = self.signal_ready()

            # Main game loop
            running = True
            while running:
                # Check for incoming messages
                message = self.receive()
                running = self.handle_message(message)

                # If we received our hand, play a card
                if message.startswith("HAND") and self.state and self.state.hand:
                    self.play_turn()

        except KeyboardInterrupt:
            print("\nDisconnecting...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.disconnect()


def main():
    if len(sys.argv) != 5:
        print("Usage: python sushi_go_client.py <host> <port> <game_id> <player_name>")
        print("Example: python sushi_go_client.py localhost 7878 abc123 MyBot")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    game_id = sys.argv[3]
    player_name = sys.argv[4]

    client = SushiGoClient(host, port)
    client.run(game_id, player_name)


if __name__ == "__main__":
    main()
