#!/usr/bin/env python3
"""Simple random bot — ~15 lines of game logic."""

import random
import sys

from ao_games import Bot, HandCard, GameState, run_bot


class RandomBot(Bot):
    def choose_card(self, hand: list[HandCard], state: GameState) -> int:
        return random.choice(hand).index


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else "test"
    name = sys.argv[2] if len(sys.argv) > 2 else "RandomBot"
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 7878

    result = run_bot(RandomBot(), game_id, name, host, port)
    print(f"Game over! Winners: {result.winners}, Scores: {result.final_scores}")
