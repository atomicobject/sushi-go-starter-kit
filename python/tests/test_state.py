"""Tests for GameState updates from message sequences."""

from ao_games.protocol import (
    GameEndMessage,
    GameStartMessage,
    HandMessage,
    PlayerJoinedMessage,
    PlayerLeftMessage,
    RoundEndMessage,
    RoundStartMessage,
    TurnResultMessage,
    WelcomeMessage,
    TournamentMatchAssignedMessage,
    TournamentCompleteMessage,
)
from ao_games.state import GameState
from ao_games.types import Card, HandCard, RoundScore


def test_welcome_sets_ids():
    state = GameState()
    state.update(WelcomeMessage(game_id="g1", player_id=0, rejoin_token="tok"))
    assert state.game_id == "g1"
    assert state.player_id == 0
    assert state.rejoin_token == "tok"
    assert state.phase == "lobby"


def test_player_joined():
    state = GameState()
    state.update(PlayerJoinedMessage(player_name="Alice", player_count=1, max_players=4))
    assert state.players == ["Alice"]
    assert state.player_count == 1
    assert state.max_players == 4

    state.update(PlayerJoinedMessage(player_name="Bob", player_count=2, max_players=4))
    assert state.players == ["Alice", "Bob"]
    assert state.player_count == 2

    # Duplicate join doesn't add again
    state.update(PlayerJoinedMessage(player_name="Alice", player_count=2, max_players=4))
    assert state.players == ["Alice", "Bob"]


def test_player_left():
    state = GameState(players=["Alice", "Bob"], player_count=2)
    state.update(PlayerLeftMessage(player_name="Bob"))
    assert state.players == ["Alice"]
    assert state.player_count == 1


def test_game_start():
    state = GameState()
    state.update(GameStartMessage(player_count=3, move_timeout_ms=500))
    assert state.phase == "playing"
    assert state.player_count == 3
    assert state.move_timeout_ms == 500


def test_round_and_hand():
    state = GameState()
    state.update(RoundStartMessage(round=1))
    assert state.round == 1
    assert state.turn == 0

    hand = [HandCard(0, Card.TEMPURA), HandCard(1, Card.SASHIMI)]
    state.update(HandMessage(cards=hand))
    assert state.turn == 1
    assert len(state.hand) == 2


def test_turn_result():
    state = GameState()
    plays = [("Alice", [Card.TEMPURA]), ("Bob", [Card.MAKI_3])]
    state.update(TurnResultMessage(plays=plays))
    assert state.last_plays == plays


def test_round_end():
    state = GameState()
    scores = {"Alice": RoundScore(total=13), "Bob": RoundScore(total=7)}
    state.update(RoundEndMessage(round=1, scores=scores))
    assert 1 in state.round_scores
    assert state.round_scores[1]["Alice"].total == 13


def test_game_end():
    state = GameState()
    state.update(
        GameEndMessage(
            final_scores={"Alice": 25, "Bob": 18},
            winners=["Alice"],
            next_game_id="g2",
            tournament_winner=None,
        )
    )
    assert state.phase == "ended"
    assert state.final_scores == {"Alice": 25, "Bob": 18}
    assert state.winners == ["Alice"]
    assert state.next_game_id == "g2"


def test_full_game_sequence():
    """Simulate a minimal game: lobby -> start -> round -> hand -> end."""
    state = GameState()

    state.update(WelcomeMessage(game_id="g1", player_id=0, rejoin_token="tok"))
    state.update(PlayerJoinedMessage(player_name="Me", player_count=1, max_players=2))
    state.update(PlayerJoinedMessage(player_name="Rival", player_count=2, max_players=2))
    assert state.phase == "lobby"

    state.update(GameStartMessage(player_count=2, move_timeout_ms=300))
    assert state.phase == "playing"

    state.update(RoundStartMessage(round=1))
    state.update(HandMessage(cards=[HandCard(0, Card.TEMPURA), HandCard(1, Card.SASHIMI)]))
    assert state.round == 1
    assert state.turn == 1

    state.update(TurnResultMessage(plays=[("Me", [Card.TEMPURA]), ("Rival", [Card.SASHIMI])]))

    state.update(
        GameEndMessage(
            final_scores={"Me": 10, "Rival": 8},
            winners=["Me"],
            next_game_id=None,
            tournament_winner=None,
        )
    )
    assert state.phase == "ended"
    assert state.winners == ["Me"]


def test_tournament_match_resets_game_state():
    state = GameState(phase="ended", round=3, hand=[HandCard(0, Card.TEMPURA)])
    state.update(
        TournamentMatchAssignedMessage(
            tournament_id="t1", match_token="m1", round=2, opponent="Alice"
        )
    )
    assert state.tournament_id == "t1"
    assert state.match_token == "m1"
    assert state.phase == "lobby"
    assert state.round == 0
    assert state.hand == []


def test_tournament_complete():
    state = GameState()
    state.update(TournamentCompleteMessage(tournament_id="t1", winner="Alice"))
    assert state.tournament_winner == "Alice"
