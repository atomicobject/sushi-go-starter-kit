from Drake_client import GameState
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



def decide(hand: list[str], state: GameState) -> int:
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
    
    
    
    state.hand_num = (state.hand_num + 1) % state.player_count
    return 0