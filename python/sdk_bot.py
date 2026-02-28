#!/usr/bin/env python3
"""Example bot using the ao_games SDK.

Usage:
    python sdk_bot.py <game_id> <player_name> [host] [port]

Example:
    python sdk_bot.py abc123 MyBot
    python sdk_bot.py abc123 MyBot 192.168.1.50 7878
"""

import random
import sys

from ao_games import Bot, Card, HandCard, GameState, run_bot


class MyBot(Bot):
    def choose_card(self, hand: list[HandCard], state: GameState) -> int:
        """Pick a card to play.

        `hand` is a list of HandCard(index, card) — return the index to play.
        `state` tracks the full game: round, turn, scores, what others played, etc.

        Replace this with your own strategy!
        """
        return random.choice(hand).index

    def on_round_start(self, round_num: int, state: GameState) -> None:
        print(f"Round {round_num} started")

    def on_game_end(self, state: GameState) -> None:
        print(f"Game over! Scores: {state.final_scores}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python sdk_bot.py <game_id> <player_name> [host] [port]")
        sys.exit(1)

    game_id = sys.argv[1]
    name = sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 7878

    run_bot(MyBot(), game_id, name, host, port)
