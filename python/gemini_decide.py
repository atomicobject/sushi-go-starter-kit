import random
from collections import Counter

# Constants for card values and priorities
# These can be adjusted to fine-tune the strategy
CARD_SCORES = {
    "Pudding": 0,
    "Maki Roll (1)": 0,
    "Maki Roll (2)": 0,
    "Maki Roll (3)": 0,
    "Tempura": 2.5,  # 5 points for a pair
    "Sashimi": 3.33,  # 10 points for a set of 3
    "Dumpling": 0,  # Points are 1, 3, 6, 10, 15
    "Egg Nigiri": 1,
    "Salmon Nigiri": 2,
    "Squid Nigiri": 3,
    "Wasabi": 0,
    "Chopsticks": 0,
}

# A simple initial priority for each card. This will be adjusted by the strategy.
CARD_PRIORITY = {
    "Pudding": 5,
    "Maki Roll (1)": 2,
    "Maki Roll (2)": 3,
    "Maki Roll (3)": 4,
    "Tempura": 6,
    "Sashimi": 7,
    "Dumpling": 8,
    "Egg Nigiri": 1,
    "Salmon Nigiri": 9,
    "Squid Nigiri": 10,
    "Wasabi": 11,
    "Chopsticks": 0,
}


def decide(hand, state):
    """
    The main decision-making function for the Gemini bot.
    """

    # First, let's analyze our current played cards and hand
    played_cards = state.get("played_cards", [])
    hand_counts = Counter(hand)
    played_counts = Counter(played_cards)

    # Calculate the priority of each card in the hand
    priorities = {}
    for i, card in enumerate(hand):
        priorities[i] = get_card_priority(card, hand_counts, played_counts, state)

    # Choose the card with the highest priority
    best_card_index = max(priorities, key=priorities.get)

    return best_card_index


def get_card_priority(card, hand_counts, played_counts, state):
    """
    Calculates the priority of a single card based on the game state.
    """
    priority = CARD_PRIORITY.get(card, 0)

    # Wasabi + Nigiri: High priority to play a Nigiri on a Wasabi
    if "Wasabi" in played_counts and card in ["Egg Nigiri", "Salmon Nigiri", "Squid Nigiri"]:
        priority += 20

    # Tempura: Higher priority if we already have one
    if card == "Tempura" and played_counts["Tempura"] % 2 == 1:
        priority += 10

    # Sashimi: Higher priority if we have one or two already
    if card == "Sashimi" and 0 < played_counts["Sashimi"] % 3 < 3:
        priority += 10

    # Dumplings: Value increases with each one
    priority += played_counts["Dumpling"] * 2

    # Maki Rolls: Value depends on what others have played (a more complex addition)
    # For now, a simple bonus based on the number of rolls
    if "Maki Roll" in card:
      priority += int(card.split("(")[1][0])

    # Pudding: important for end-game, but not urgent mid-round
    if card == "Pudding":
        priority += state.get("round", 1) # Becomes more important in later rounds

    return priority
