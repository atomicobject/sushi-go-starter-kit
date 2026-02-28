#!/usr/bin/env python3
"""
First Card Tournament Bot - A simple Sushi Go tournament player that always picks the first card.

Usage:
    python first_card_tournament_bot.py <tournament_id> <player_name> [host] [port]
    python first_card_tournament_bot.py <host> <port> <tournament_id> <player_name>

Example:
    python first_card_tournament_bot.py spicy-salmon FirstBot
    python first_card_tournament_bot.py spicy-salmon FirstBot localhost 7878
    python first_card_tournament_bot.py localhost 7878 spicy-salmon FirstBot
"""

import random
import socket
import sys
import time


def main():
    if len(sys.argv) < 3:
        print("Usage: python first_card_tournament_bot.py <tournament_id> <player_name> [host] [port]")
        print("   or: python first_card_tournament_bot.py <host> <port> <tournament_id> <player_name>")
        sys.exit(1)

    args = sys.argv[1:]
    host = "localhost"
    port = 7878

    # Support both:
    # 1) <tournament_id> <player_name> [host] [port]
    # 2) <host> <port> <tournament_id> <player_name>
    if len(args) >= 4 and args[1].isdigit():
        host = args[0]
        port = int(args[1])
        tournament_id = args[2]
        player_name = args[3]
    else:
        tournament_id = args[0]
        player_name = args[1]
        if len(args) > 2:
            host = args[2]
        if len(args) > 3:
            try:
                port = int(args[3])
            except ValueError:
                print(f"Invalid port: {args[3]}")
                print("Usage: python first_card_tournament_bot.py <tournament_id> <player_name> [host] [port]")
                print("   or: python first_card_tournament_bot.py <host> <port> <tournament_id> <player_name>")
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
        # Join the tournament
        send(f"TOURNEY {tournament_id} {player_name}")
        response = recv_until(
            lambda line: line.startswith("TOURNAMENT_WELCOME") or line.startswith("ERROR")
        )
        if not response.startswith("TOURNAMENT_WELCOME"):
            print(f"Failed to join tournament: {response}")
            return

        # Parse rejoin token from TOURNAMENT_WELCOME <tid> <count>/<max> <rejoin_token>
        parts = response.split()
        rejoin_token = parts[3] if len(parts) > 3 else ""
        print(f"Joined tournament {tournament_id} (rejoin token: {rejoin_token})")

        # Tournament loop — wait for match assignments
        while True:
            msg = recv()
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

                # Join the match
                send(f"TJOIN {match_token}")
                join_response = recv_until(
                    lambda line: line.startswith("WELCOME") or line.startswith("ERROR")
                )
                if not join_response.startswith("WELCOME"):
                    print(f"Failed to join match: {join_response}")
                    continue

                # Signal ready
                send("READY")

                # Play the game
                while True:
                    game_msg = recv()

                    if game_msg.startswith("GAME_END"):
                        print("Game over!")
                        # Leave the game so we can join the next match
                        send("LEAVE")
                        recv_until(lambda line: line.startswith("OK") or line.startswith("ERROR"))
                        break
                    elif game_msg.startswith("HAND"):
                        hand = parse_hand_message(game_msg)
                        if not hand:
                            continue
                        delay = random.uniform(0.5, 2.5)
                        time.sleep(delay)
                        send("PLAY 0")
                    elif game_msg.startswith("TOURNAMENT_MATCH") or game_msg.startswith("TOURNAMENT_COMPLETE"):
                        # Tournament message arrived during game — handle after game ends
                        # For TOURNAMENT_COMPLETE we can exit immediately
                        if game_msg.startswith("TOURNAMENT_COMPLETE"):
                            tparts = game_msg.split()
                            winner = tparts[2] if len(tparts) > 2 else "unknown"
                            print(f"Tournament complete! Winner: {winner}")
                            return
                    # Ignore other messages (OK, WAITING, PLAYED, ROUND_START, ROUND_END, etc.)

            elif msg.startswith("TOURNAMENT_COMPLETE"):
                # TOURNAMENT_COMPLETE <tid> <winner>
                parts = msg.split()
                winner = parts[2] if len(parts) > 2 else "unknown"
                print(f"Tournament complete! Winner: {winner}")
                break

            elif msg.startswith("TOURNAMENT_JOINED"):
                # Another player joined the tournament
                print(f"  {msg}")

            # Ignore other messages

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
