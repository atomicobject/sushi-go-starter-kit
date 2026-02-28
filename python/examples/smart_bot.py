#!/usr/bin/env python3
"""Smart bot — uses state tracking to make better card choices."""

import sys

from ao_games import Bot, Card, HandCard, GameState, run_bot


# Priority order: higher-value cards first
CARD_PRIORITY = {
    Card.SASHIMI: 10,
    Card.TEMPURA: 9,
    Card.SQUID_NIGIRI: 8,
    Card.SALMON_NIGIRI: 7,
    Card.EGG_NIGIRI: 6,
    Card.DUMPLING: 5,
    Card.MAKI_3: 4,
    Card.MAKI_2: 3,
    Card.MAKI_1: 2,
    Card.WASABI: 1,
    Card.PUDDING: 1,
    Card.CHOPSTICKS: 0,
}


class SmartBot(Bot):
    def choose_card(self, hand: list[HandCard], state: GameState) -> int:
        # Pick the highest-priority card
        best = max(hand, key=lambda hc: CARD_PRIORITY.get(hc.card, 0))
        return best.index

    def on_game_start(self, state: GameState) -> None:
        print(f"[SmartBot] Game started with {state.player_count} players")

    def on_round_start(self, round_num: int, state: GameState) -> None:
        print(f"[SmartBot] Round {round_num} started")

    def on_round_end(self, round_num: int, state: GameState) -> None:
        scores = state.round_scores.get(round_num, {})
        for name, score in scores.items():
            print(f"  {name}: {score.total} pts")

    def on_game_end(self, state: GameState) -> None:
        print(f"[SmartBot] Game over! Winners: {state.winners}")
        for name, score in state.final_scores.items():
            print(f"  {name}: {score}")


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else "test"
    name = sys.argv[2] if len(sys.argv) > 2 else "SmartBot"
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 7878

    run_bot(SmartBot(), game_id, name, host, port)
