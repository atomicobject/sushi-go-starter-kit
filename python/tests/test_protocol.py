"""Tests for protocol parsing — test vectors match Rust message.rs tests."""

import pytest
from ao_games.errors import ProtocolError, ErrorCode
from ao_games.protocol import (
    parse_server_message,
    OkMessage,
    WelcomeMessage,
    RejoinedMessage,
    CreatedMessage,
    PlayerJoinedMessage,
    PlayerLeftMessage,
    GameStartMessage,
    RoundStartMessage,
    HandMessage,
    WaitingMessage,
    TurnResultMessage,
    RoundEndMessage,
    GameEndMessage,
    TournamentWelcomeMessage,
    TournamentRejoinedMessage,
    TournamentPlayerJoinedMessage,
    TournamentMatchAssignedMessage,
    TournamentCompleteMessage,
    format_join,
    format_rejoin,
    format_ready,
    format_play,
    format_chopsticks,
    format_status,
    format_games,
    format_leave,
    format_tourney,
    format_tjoin,
)
from ao_games.types import Card


# ---------------------------------------------------------------------------
# Server message parsing (matches Rust message.rs tests lines 364-443)
# ---------------------------------------------------------------------------


class TestOkMessage:
    def test_simple(self):
        msg = parse_server_message("OK")
        assert isinstance(msg, OkMessage)
        assert msg.details is None

    def test_with_details(self):
        msg = parse_server_message("OK Move accepted")
        assert isinstance(msg, OkMessage)
        assert msg.details == "Move accepted"


class TestWelcomeMessage:
    def test_parse(self):
        msg = parse_server_message("WELCOME abc123 0 tok_abc123")
        assert isinstance(msg, WelcomeMessage)
        assert msg.game_id == "abc123"
        assert msg.player_id == 0
        assert msg.rejoin_token == "tok_abc123"


class TestRejoinedMessage:
    def test_parse(self):
        msg = parse_server_message("REJOINED abc123 1")
        assert isinstance(msg, RejoinedMessage)
        assert msg.game_id == "abc123"
        assert msg.player_id == 1


class TestCreatedMessage:
    def test_parse(self):
        msg = parse_server_message("CREATED game_xyz")
        assert isinstance(msg, CreatedMessage)
        assert msg.game_id == "game_xyz"


class TestPlayerJoinedMessage:
    def test_parse(self):
        msg = parse_server_message("JOINED Alice 2/4")
        assert isinstance(msg, PlayerJoinedMessage)
        assert msg.player_name == "Alice"
        assert msg.player_count == 2
        assert msg.max_players == 4


class TestPlayerLeftMessage:
    def test_parse(self):
        msg = parse_server_message("LEFT Bob")
        assert isinstance(msg, PlayerLeftMessage)
        assert msg.player_name == "Bob"


class TestGameStartMessage:
    def test_parse(self):
        msg = parse_server_message("GAME_START 4 300")
        assert isinstance(msg, GameStartMessage)
        assert msg.player_count == 4
        assert msg.move_timeout_ms == 300


class TestRoundStartMessage:
    def test_parse(self):
        msg = parse_server_message("ROUND_START 2")
        assert isinstance(msg, RoundStartMessage)
        assert msg.round == 2


class TestHandMessage:
    def test_simple_cards(self):
        msg = parse_server_message("HAND 0:Tempura 1:Sashimi 2:Dumpling")
        assert isinstance(msg, HandMessage)
        assert len(msg.cards) == 3
        assert msg.cards[0].index == 0
        assert msg.cards[0].card is Card.TEMPURA
        assert msg.cards[1].card is Card.SASHIMI
        assert msg.cards[2].card is Card.DUMPLING

    def test_multi_word_names(self):
        """Matches Rust test: HAND 0:Tempura 1:Sashimi 2:Salmon Nigiri"""
        msg = parse_server_message("HAND 0:Tempura 1:Sashimi 2:Salmon Nigiri")
        assert len(msg.cards) == 3
        assert msg.cards[0].card is Card.TEMPURA
        assert msg.cards[1].card is Card.SASHIMI
        assert msg.cards[2].card is Card.SALMON_NIGIRI

    def test_all_card_types(self):
        line = (
            "HAND 0:Tempura 1:Sashimi 2:Dumpling 3:Maki Roll (1) "
            "4:Maki Roll (2) 5:Maki Roll (3) 6:Egg Nigiri "
            "7:Salmon Nigiri 8:Squid Nigiri 9:Pudding"
        )
        msg = parse_server_message(line)
        assert len(msg.cards) == 10
        assert msg.cards[3].card is Card.MAKI_1
        assert msg.cards[6].card is Card.EGG_NIGIRI
        assert msg.cards[8].card is Card.SQUID_NIGIRI
        assert msg.cards[9].card is Card.PUDDING


class TestWaitingMessage:
    def test_parse(self):
        msg = parse_server_message("WAITING Alice Charlie")
        assert isinstance(msg, WaitingMessage)
        assert msg.players == ["Alice", "Charlie"]


class TestTurnResultMessage:
    def test_single_card(self):
        msg = parse_server_message("PLAYED Alice:TMP")
        assert isinstance(msg, TurnResultMessage)
        assert len(msg.plays) == 1
        assert msg.plays[0] == ("Alice", [Card.TEMPURA])

    def test_multiple_players(self):
        """Matches Rust test: PLAYED Alice:TMP; Bob:MK3,WAS"""
        msg = parse_server_message("PLAYED Alice:TMP; Bob:MK3,WAS")
        assert len(msg.plays) == 2
        assert msg.plays[0] == ("Alice", [Card.TEMPURA])
        assert msg.plays[1] == ("Bob", [Card.MAKI_3, Card.WASABI])


class TestRoundEndMessage:
    def test_parse(self):
        line = 'ROUND_END 1 {"Alice":{"maki_points":6,"tempura_points":5,"sashimi_points":0,"dumpling_points":0,"nigiri_points":2,"total":13}}'
        msg = parse_server_message(line)
        assert isinstance(msg, RoundEndMessage)
        assert msg.round == 1
        assert "Alice" in msg.scores
        assert msg.scores["Alice"].maki_points == 6
        assert msg.scores["Alice"].total == 13


class TestGameEndMessage:
    def test_basic(self):
        line = 'GAME_END {"Alice":25,"Bob":18} WINNER:Alice'
        msg = parse_server_message(line)
        assert isinstance(msg, GameEndMessage)
        assert msg.final_scores == {"Alice": 25, "Bob": 18}
        assert msg.winners == ["Alice"]
        assert msg.next_game_id is None
        assert msg.tournament_winner is None

    def test_with_next_and_tournament_winner(self):
        line = 'GAME_END {"Alice":25,"Bob":18} WINNER:Alice NEXT:game_2 TOURNAMENT_WINNER:Alice'
        msg = parse_server_message(line)
        assert msg.winners == ["Alice"]
        assert msg.next_game_id == "game_2"
        assert msg.tournament_winner == "Alice"

    def test_multiple_winners(self):
        line = 'GAME_END {"Alice":25,"Bob":25} WINNER:Alice,Bob'
        msg = parse_server_message(line)
        assert msg.winners == ["Alice", "Bob"]


class TestErrorMessage:
    def test_raises_protocol_error(self):
        with pytest.raises(ProtocolError) as exc_info:
            parse_server_message("ERROR E001 Invalid command format")
        assert exc_info.value.code == ErrorCode.INVALID_COMMAND
        assert "Invalid command format" in exc_info.value.message


class TestTournamentMessages:
    def test_welcome(self):
        msg = parse_server_message("TOURNAMENT_WELCOME tourney1 3/8 tok_abc")
        assert isinstance(msg, TournamentWelcomeMessage)
        assert msg.tournament_id == "tourney1"
        assert msg.player_count == 3
        assert msg.max_players == 8
        assert msg.rejoin_token == "tok_abc"

    def test_rejoined(self):
        msg = parse_server_message("TOURNAMENT_REJOINED tourney1 Alice match_tok")
        assert isinstance(msg, TournamentRejoinedMessage)
        assert msg.tournament_id == "tourney1"
        assert msg.player_name == "Alice"
        assert msg.current_match_token == "match_tok"

    def test_rejoined_no_match(self):
        msg = parse_server_message("TOURNAMENT_REJOINED tourney1 Alice")
        assert isinstance(msg, TournamentRejoinedMessage)
        assert msg.current_match_token is None

    def test_player_joined(self):
        msg = parse_server_message("TOURNAMENT_JOINED tourney1 Bob 4/8")
        assert isinstance(msg, TournamentPlayerJoinedMessage)
        assert msg.tournament_id == "tourney1"
        assert msg.player_name == "Bob"
        assert msg.player_count == 4
        assert msg.max_players == 8

    def test_match_assigned(self):
        msg = parse_server_message("TOURNAMENT_MATCH tourney1 match_tok 2 Alice")
        assert isinstance(msg, TournamentMatchAssignedMessage)
        assert msg.tournament_id == "tourney1"
        assert msg.match_token == "match_tok"
        assert msg.round == 2
        assert msg.opponent == "Alice"

    def test_match_bye(self):
        msg = parse_server_message("TOURNAMENT_MATCH tourney1 match_tok 1 BYE")
        assert isinstance(msg, TournamentMatchAssignedMessage)
        assert msg.opponent is None

    def test_complete(self):
        msg = parse_server_message("TOURNAMENT_COMPLETE tourney1 Alice")
        assert isinstance(msg, TournamentCompleteMessage)
        assert msg.tournament_id == "tourney1"
        assert msg.winner == "Alice"


# ---------------------------------------------------------------------------
# Command formatting
# ---------------------------------------------------------------------------


class TestCommandFormatting:
    def test_join(self):
        assert format_join("game1", "Alice") == "JOIN game1 Alice"

    def test_rejoin(self):
        assert format_rejoin("tok_abc") == "REJOIN tok_abc"

    def test_ready(self):
        assert format_ready() == "READY"

    def test_play(self):
        assert format_play(3) == "PLAY 3"

    def test_chopsticks(self):
        assert format_chopsticks(1, 4) == "CHOPSTICKS 1 4"

    def test_status(self):
        assert format_status() == "STATUS"

    def test_games(self):
        assert format_games() == "GAMES"

    def test_leave(self):
        assert format_leave() == "LEAVE"

    def test_tourney(self):
        assert format_tourney("t1", "Bob") == "TOURNEY t1 Bob"

    def test_tjoin(self):
        assert format_tjoin("match_1") == "TJOIN match_1"
