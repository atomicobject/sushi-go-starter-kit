"""Tests for Card enum and type round-trips."""

import pytest
from ao_games.types import Card


ALL_CARDS = [
    (Card.TEMPURA, "TMP", "Tempura"),
    (Card.SASHIMI, "SSH", "Sashimi"),
    (Card.DUMPLING, "DMP", "Dumpling"),
    (Card.MAKI_1, "MK1", "Maki Roll (1)"),
    (Card.MAKI_2, "MK2", "Maki Roll (2)"),
    (Card.MAKI_3, "MK3", "Maki Roll (3)"),
    (Card.EGG_NIGIRI, "EGG", "Egg Nigiri"),
    (Card.SALMON_NIGIRI, "SAL", "Salmon Nigiri"),
    (Card.SQUID_NIGIRI, "SQD", "Squid Nigiri"),
    (Card.PUDDING, "PUD", "Pudding"),
    (Card.WASABI, "WAS", "Wasabi"),
    (Card.CHOPSTICKS, "CHP", "Chopsticks"),
]


@pytest.mark.parametrize("card,code,name", ALL_CARDS)
def test_card_code_roundtrip(card, code, name):
    assert card.code == code
    assert Card.from_code(code) is card


@pytest.mark.parametrize("card,code,name", ALL_CARDS)
def test_card_name_roundtrip(card, code, name):
    assert card.display_name == name
    assert Card.from_name(name) is card


def test_from_code_unknown():
    with pytest.raises(ValueError, match="Unknown card code"):
        Card.from_code("XXX")


def test_from_name_unknown():
    with pytest.raises(ValueError, match="Unknown card name"):
        Card.from_name("Nonexistent")


def test_is_nigiri():
    assert Card.EGG_NIGIRI.is_nigiri
    assert Card.SALMON_NIGIRI.is_nigiri
    assert Card.SQUID_NIGIRI.is_nigiri
    assert not Card.TEMPURA.is_nigiri
    assert not Card.WASABI.is_nigiri


def test_maki_count():
    assert Card.MAKI_1.maki_count == 1
    assert Card.MAKI_2.maki_count == 2
    assert Card.MAKI_3.maki_count == 3
    assert Card.TEMPURA.maki_count == 0


def test_nigiri_points():
    assert Card.EGG_NIGIRI.nigiri_points == 1
    assert Card.SALMON_NIGIRI.nigiri_points == 2
    assert Card.SQUID_NIGIRI.nigiri_points == 3
    assert Card.DUMPLING.nigiri_points == 0


def test_all_12_members():
    assert len(Card) == 12
