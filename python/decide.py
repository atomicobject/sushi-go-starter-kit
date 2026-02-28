import random
from collections import Counter
import jacob_client

PLAYER_NUM = {
    10:2,
    9:3,
    8:4,
    7:5
}

CARD_DEFAULT_FREQUENCIES ={
    "Tempura": 14,
    "Sashimi": 14,
    "Dumpling": 14,
    "Maki Roll (1)": 6,
    "Maki Roll (2)": 12,
    "Maki Roll (3)": 3,
    "Egg Nigiri": 5,
    "Salmon Nigiri": 10,
    "Squid Nigiri": 5,
    "Pudding": 10,
    "Wasabi": 6,
    "Chopsticks": 4,
}

priority = {
        "Wasabi" : 12,  # Triples next nigiri
        "Squid Nigiri" : 11,  # 3 points, or 9 with wasabi
        "Salmon Nigiri":10,  # 2 points, or 6 with wasabi
        "Dumpling":9,  # Increasing value
        "Egg Nigiri":8,  # 1 point, or 3 with wasabi
        "Pudding":7,  # End game scoring
        "Maki Roll (3)":6,  # 3 maki rolls
        "Maki Roll (2)":5,  # 2 maki rolls
        "Tempura":4,  # 5 points per pair
        "Sashimi":3,  # 10 points per set of 3
        "Maki Roll (1)":2,  # 1 maki roll
        "Chopsticks":1,  # Play 2 cards next turn
}

def decide(hand: list[str], state: jacob_client.GameState) -> int:

    if state.hands is None:
        state.player_count = PLAYER_NUM[len(hand)]
        state.hands = [hand.copy()]

    if len(state.hands) < state.hand_num:
        state.hands.append(hand)
    else:
        missing = find_missing(state.hands[state.hand_num], hand)
        for item in missing:
            state.enemy_cards_played.append(item)
        state.hands[state.hand_num] = hand.copy()


    return max(priority.values())


def find_missing(list1, list2):
    count1 = Counter(list1)
    count2 = Counter(list2)

    missing = []
    for item, count in count1.items():
        diff = count - count2[item]
        if diff > 0:
            missing.extend([item] * diff)

    return missing


