import random
from collections import Counter

players = {
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

total_cards = 108
start_card_num = 0

from collections import Counter

def find_missing(list1, list2):
    count1 = Counter(list1)
    count2 = Counter(list2)
    
    missing = []
    for item, count in count1.items():
        diff = count - count2[item]
        if diff > 0:
            missing.extend([item] * diff)
    
    return missing
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

dumpling_scale = [1,2,3,4,5]


def decide(hand: list[str], state):
    """
    The main decision-making function for the Gemini bot.
    """
    if state.hands is None:
        state.player_count = players[len(hand)]
        state.hands = [hand.copy()]
        start_card_num = len(hand)
        
    if len(state.hands) < state.hand_num:
        state.hands.append(hand)
        total_cards -= len(hand)
        
        temp = []
        for cur_hand in state.hands:
            temp += cur_hand
        playable_count = dict(Counter(temp))
        
        temp = []
        for cur_hand in state.enemy_cards_played:
            temp += cur_hand
        played_count = dict(Counter(temp))
        
        amount = state.player_count - len(state.hands)
        for key in playable_count.keys():
            state.card_distribution[key] = playable_count[key] + amount * start_card_num * (CARD_DEFAULT_FREQUENCIES[key] - playable_count[key] - played_count[key]) / total_cards
        
        
        
    else:
        missing = find_missing(state.hands[state.hand_num], hand)
        for item in missing:
            state.enemy_cards_played.append(item)
        state.hands[state.hand_num] = hand.copy()
        
        temp = []
        for cur_hand in state.hands:
            temp += cur_hand
        
        count = Counter(temp)
        state.card_distribution = dict(count)
    

    # First, let's analyze our current played cards and hand
    played_cards = state.played_cards
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
    if card == "Tempura" and int(state.card_distribution["Tempura"]) % 2 == 0:
        priority += 10

    # Sashimi: Higher priority if we have one or two already
    if card == "Sashimi" and 0 < int(state.card_distribution["Sashimi"]) % 3 and played_counts["Sashimi"] % 3 == 1:
        priority += 2

    if card == "Sashimi" and 0 < int(state.card_distribution["Sashimi"]) % 3 and played_counts["Sashimi"] % 3 == 2:
        priority += 20

    # Dumplings: Value increases with each one
    priority += played_counts["Dumpling"] * 2

    # Maki Rolls: Value depends on what others have played (a more complex addition)
    # For now, a simple bonus based on the number of rolls
    if "Maki Roll" in card:
      priority += int(card.split("(")[1][0])

    # Pudding: important for end-game, but not urgent mid-round
    if card == "Pudding":
        priority += state.round

    return priority
