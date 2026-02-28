#!/usr/bin/env python3
"""Tournament bot — plays all matches in a tournament."""

import random
import sys

from ao_games import Bot, HandCard, GameState, run_tournament_bot


class TournamentBot(Bot):
    def __init__(self):
        self.matches_played = 0
        self.matches_won = 0

    def choose_card(self, hand: list[HandCard], state: GameState) -> int:
        return random.choice(hand).index

    def on_tournament_match(self, state: GameState) -> None:
        self.matches_played += 1
        opponent = state.tournament_opponent or "BYE"
        print(
            f"[TournamentBot] Match #{self.matches_played} "
            f"(round {state.tournament_round}) vs {opponent}"
        )

    def on_game_end(self, state: GameState) -> None:
        if state.player_name in state.winners:
            self.matches_won += 1
            print(f"[TournamentBot] Won! ({self.matches_won}/{self.matches_played})")
        else:
            print(f"[TournamentBot] Lost. ({self.matches_won}/{self.matches_played})")

    def on_tournament_complete(self, winner: str, state: GameState) -> None:
        print(f"[TournamentBot] Tournament over! Winner: {winner}")
        print(f"  Record: {self.matches_won}/{self.matches_played}")


if __name__ == "__main__":
    tournament_id = sys.argv[1] if len(sys.argv) > 1 else "test"
    name = sys.argv[2] if len(sys.argv) > 2 else "TournamentBot"
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 7878

    run_tournament_bot(TournamentBot(), tournament_id, name, host, port)
