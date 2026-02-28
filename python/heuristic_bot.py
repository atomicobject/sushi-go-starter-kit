#!/usr/bin/env python3
"""
First Card Bot - A simple Sushi Go player that always picks the first card.

Usage:
    python first_card_bot.py <game_id> <player_name> [host] [port]
    python first_card_bot.py <host> <port> <game_id> <player_name>

Example:
    python first_card_bot.py abc123 FirstBot
    python first_card_bot.py abc123 FirstBot localhost 7878
    python first_card_bot.py localhost 7878 abc123 FirstBot
"""

import random
import socket
import sys
import time


def main():
    if len(sys.argv) < 3:
        print("Usage: python first_card_bot.py <game_id> <player_name> [host] [port]")
        print("   or: python first_card_bot.py <host> <port> <game_id> <player_name>")
        sys.exit(1)

    args = sys.argv[1:]
    host = "localhost"
    port = 7878

    # Support both:
    # 1) <game_id> <player_name> [host] [port]
    # 2) <host> <port> <game_id> <player_name>
    if len(args) >= 4 and args[1].isdigit():
        host = args[0]
        port = int(args[1])
        game_id = args[2]
        player_name = args[3]
    else:
        game_id = args[0]
        player_name = args[1]
        if len(args) > 2:
            host = args[2]
        if len(args) > 3:
            try:
                port = int(args[3])
            except ValueError:
                print(f"Invalid port: {args[3]}")
                print("Usage: python first_card_bot.py <game_id> <player_name> [host] [port]")
                print("   or: python first_card_bot.py <host> <port> <game_id> <player_name>")
                sys.exit(1)

    print(f"Connecting to {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock_file = sock.makefile("r", encoding="utf-8", errors="replace")
    print("Connected!")

    def send(cmd):
        print(f">>> {cmd}")
        sock.sendall((cmd + "\n").encode())

    def recv():
        line = sock_file.readline()
        if line == "":
            raise ConnectionError("Server closed connection")
        msg = line.strip()
        print(f"<<< {msg}")
        return msg

    def recv_until(predicate):
        while True:
            msg = recv()
            if not msg:
                continue
            if predicate(msg):
                return msg

    def parse_game_start_message(message):
        # Example: "GAME_START 4" means 4 players in the game
        parts = message.split()
        if len(parts) >= 2 and parts[0] == "GAME_START":
            try:
                return int(parts[1])
            except ValueError:
                return 0
        return 0

    def parse_hand_message(message):
        # Supports both "HAND A B C" and indexed "HAND 0:A 1:B" with spaces in names.
        tokens = message.split()[1:]
        if not tokens:
            return []

        if not any(":" in token for token in tokens):
            return tokens

        cards = []
        current = []
        for token in tokens:
            if ":" in token:
                prefix, name = token.split(":", 1)
                if prefix.isdigit():
                    if current:
                        cards.append(" ".join(current))
                    current = [name]
                    continue
            if current:
                current.append(token)
            else:
                cards.append(token)
        if current:
            cards.append(" ".join(current))
        return cards

    try:
        # Join the game
        send(f"JOIN {game_id} {player_name}")
        response = recv_until(
            lambda line: line.startswith("WELCOME") or line.startswith("ERROR")
        )
        if not response.startswith("WELCOME"):
            print(f"Failed to join: {response}")
            return

        # Signal ready (will be acknowledged even if game already started)
        send("READY")

        # Main game loop - HAND is only sent when it's time to play
        while True:
            msg = recv()

            if msg.startswith("GAME_END"):
                print("Game over!")
                break
            elif msg.startswith("HAND"):
                # HAND means it's our turn - wait a bit then play the first card
                hand = parse_hand_message(msg)
                if not hand:
                    continue
                delay = random.uniform(0.5, 2.5)
                time.sleep(delay)
                send("PLAY 0")
            # Ignore other messages (JOINED, GAME_START, ROUND_START, PLAYED, WAITING, OK, etc.)
            # NICK HERE
            elif msg.startswith("PLAYED"):
                # Record the current state of the game
                pass



    except KeyboardInterrupt:
        print("\nDisconnecting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
