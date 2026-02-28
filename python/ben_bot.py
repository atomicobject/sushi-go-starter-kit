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
import json

from player import Player
from card import Card
from game import GameState
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
            self.state = GameState(
                game_id=parts[1],
                player_id=int(parts[2]),
                my_name=player_name
            )
            # Add ourselves as a player
            self.state.add_player(player_name)
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
                my_player = self.state.get_my_player()
                if my_player:
                    my_player.set_current_hand(cards)
                    print(f"My hand: {cards}")

    def choose_card(self, hand: list[str]) -> int:
        """
        Choose which card to play.

        This is where you implement your AI strategy!
        The default implementation uses a simple priority-based approach.

        Args:
            hand: List of card names in your current hand

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

        # If we have unused wasabi, prioritize nigiri
        my_player = self.state.get_my_player() if self.state else None
        if my_player and my_player.has_unused_wasabi():
            for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
                if nigiri in hand:
                    return hand.index(nigiri)

        # Otherwise use priority list
        for card in priority:
            if card in hand:
                return hand.index(card)

        # Fallback: random
        return random.randint(0, len(hand) - 1)


    def parse_played_message(self, message: str):
        """Parse a PLAYED message and update all players' cards."""
        # Format: PLAYED Alice:Squid Nigiri; Bob:Tempura
        if not message.startswith("PLAYED"):
            return

        payload = message[len("PLAYED "):]
        player_cards = payload.split("; ")

        for entry in player_cards:
            if ":" not in entry:
                continue
            player_name, card_name = entry.split(":", 1)
            player_name = player_name.strip()
            card_name = card_name.strip()

            # Add player if we haven't seen them yet
            if player_name not in self.state.players:
                self.state.add_player(player_name)

            # Record the card they played
            player = self.state.get_player(player_name)
            if player:
                player.add_played_card(card_name)
                print(f"{player_name} played {card_name}")

    def handle_message(self, message: str):
        """Handle a message from the server."""
        if message.startswith("HAND"):
            self.parse_hand(message)
        elif message.startswith("JOINED"):
            # Format: JOINED <player_name> <count>/<max>
            parts = message.split()
            if len(parts) >= 2 and self.state:
                player_name = parts[1]
                self.state.add_player(player_name)
                print(f"Player joined: {player_name}")
        elif message.startswith("GAME_START"):
            parts = message.split()
            if self.state and len(parts) >= 2:
                self.state.num_players = int(parts[1])
                print(f"Game starting with {self.state.num_players} players")
        elif message.startswith("ROUND_START"):
            parts = message.split()
            if self.state:
                self.state.round = int(parts[1])
                self.state.reset_round()
                print(f"Round {self.state.round} starting")
        elif message.startswith("PLAYED"):
            # Parse all played cards and increment turn
            if self.state:
                self.parse_played_message(message)
                self.state.turn += 1
        elif message.startswith("ROUND_END"):
            # Format: ROUND_END <round> <scores_json>
            # Example: ROUND_END 1 {"Alice":12,"Bob":8}
            if self.state:
                parts = message.split(None, 2)
                if len(parts) >= 3:
                    try:
                        import json
                        scores = json.loads(parts[2])
                        round_num = int(parts[1])
                        for player_name, score in scores.items():
                            player = self.state.get_player(player_name)
                            if player:
                                player.points_by_round[round_num] = score
                        print(f"Round {round_num} ended. Scores: {scores}")
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Error parsing round scores: {e}")
        elif message.startswith("GAME_END"):
            print("Game over!")
            if self.state:
                # Print final statistics
                print("\nFinal Player States:")
                for player in self.state.players.values():
                    print(f"  {player}")
            return False
        elif message.startswith("WAITING"):
            # Our move was accepted, waiting for others
            pass
        return True

    def play_turn(self):
        """Play a single turn."""
        if not self.state:
            return

        my_player = self.state.get_my_player()
        if not my_player or not my_player.current_hand:
            return

        card_index = self.choose_card(my_player.current_hand)
        played_card = my_player.current_hand[card_index]

        response = self.play_card(card_index)

        if response.startswith("OK"):
            print(f"Playing: {played_card}")
            # Note: We'll update our played_cards when we receive the PLAYED message

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
                if message.startswith("HAND") and self.state:
                    my_player = self.state.get_my_player()
                    if my_player and my_player.current_hand:
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
