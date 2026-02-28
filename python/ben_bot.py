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
from card_evaluator import CardEvaluator
from typing import Optional

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

# For handling responses from the server
SHORTHAND_TO_NAME = {
    "TMP": "Tempura",
    "SSH": "Sashimi",
    "DMP": "Dumpling",
    "MK1": "Maki Roll (1)",
    "MK2": "Maki Roll (2)",
    "MK3": "Maki Roll (3)",
    "EGG": "Egg Nigiri",
    "SAL": "Salmon Nigiri",
    "SQD": "Squid Nigiri",
    "PDG": "Pudding",
    "WSB": "Wasabi",
    "CHP": "Chopsticks",
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

    def choose_card(self, player: Player) -> int:
        """
        Choose which card to play using a hybrid greedy + smart strategy.

        Strategy:
        1. Complete high-value sets (Sashimi 3rd, Tempura 2nd)
        2. Use wasabi with best available nigiri
        3. Take wasabi if great nigiri in hand
        4. Otherwise: greedy priority list

        Args:
            player: The Player object with current hand and played cards

        Returns:
            Index of the card to play (0-based)
        """
        if not player.current_hand:
            return 0

        hand = player.current_hand
        played = player.played_cards

        # PRIORITY 1: Complete Sashimi set (3rd card = 10 points!)
        sashimi_count = played.count("Sashimi")
        if sashimi_count == 2 and "Sashimi" in hand:
            print("STRATEGY: Completing Sashimi set (10 points!)")
            return hand.index("Sashimi")

        # PRIORITY 2: Complete Tempura pair (2nd card = 5 points!)
        tempura_count = played.count("Tempura")
        if tempura_count % 2 == 1 and "Tempura" in hand:
            print("STRATEGY: Completing Tempura pair (5 points!)")
            return hand.index("Tempura")

        # PRIORITY 3: Use wasabi with best nigiri available
        if player.has_unused_wasabi():
            for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
                if nigiri in hand:
                    print(f"STRATEGY: Using wasabi with {nigiri}")
                    return hand.index(nigiri)

        # PRIORITY 4: Take wasabi if we have Squid or Salmon in hand
        if "Wasabi" in hand:
            if "Squid Nigiri" in hand or "Salmon Nigiri" in hand:
                print("STRATEGY: Taking wasabi (good nigiri in hand)")
                return hand.index("Wasabi")

        # PRIORITY 5: Greedy priority list (like original_bot)
        priority = [
            "Squid Nigiri",      # 3 points (9 with wasabi)
            "Salmon Nigiri",     # 2 points (6 with wasabi)
            "Sashimi",           # Start sets aggressively
            "Tempura",           # Start pairs aggressively
            "Maki Roll (3)",     # 3 maki
            "Maki Roll (2)",     # 2 maki
            "Dumpling",          # Increasing value
            "Wasabi",            # Speculative (might get nigiri)
            "Egg Nigiri",        # 1 point (3 with wasabi)
            "Pudding",           # End game scoring
            "Maki Roll (1)",     # 1 maki
            "Chopsticks",        # Flexibility
        ]

        for card in priority:
            if card in hand:
                print(f"STRATEGY: Greedy pick - {card}")
                return hand.index(card)

        # Fallback: first card
        print("STRATEGY: Fallback - taking first card")
        return 0


    def parse_played_message(self, message: str):
        """Parse a PLAYED message and update all players' cards."""
        if not message.startswith("PLAYED"):
            return

        payload = message[len("PLAYED "):]
        player_cards = payload.split("; ")

        for entry in player_cards:
            if ":" not in entry:
                continue
            player_name, card_name = entry.split(":", 1)
            player_name = player_name.strip()
            card_code = card_name.strip()
            card_name = SHORTHAND_TO_NAME.get(card_code, card_code)

            if player_name not in self.state.players:
                self.state.add_player(player_name)

            player = self.state.get_player(player_name)
            if player:
                player.add_played_card(card_name)
                print(f"{player_name} played {card_name}")

    def handle_message(self, message: str):
        """Handle a message from the server."""
        if message.startswith("HAND"):
            self.parse_hand(message)
        elif message.startswith("JOINED"):
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

        card_index = self.choose_card(my_player)
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
