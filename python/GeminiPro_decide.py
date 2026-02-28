from collections import Counter

def decide(hand: list[str], state) -> int:
    """
    Evaluates the current hand against the game state using a 6-tier priority hierarchy.
    Returns the integer index of the optimal card to draft.
    """
    best_index = 0
    highest_score = -999

    # Track current board state
    my_played = Counter(state.played_cards if state.played_cards else [])
    enemy_played = Counter(state.enemy_cards_played if state.enemy_cards_played else [])
    
    # Check for empty Wasabi
    my_nigiri_count = my_played["Squid Nigiri"] + my_played["Salmon Nigiri"] + my_played["Egg Nigiri"]
    has_empty_wasabi = my_played["Wasabi"] > my_nigiri_count
    
    enemy_nigiri_count = enemy_played["Squid Nigiri"] + enemy_played["Salmon Nigiri"] + enemy_played["Egg Nigiri"]
    enemy_has_empty_wasabi = enemy_played["Wasabi"] > enemy_nigiri_count

    cards_left = len(hand)

    for i, card in enumerate(hand):
        score = 0
        
        # 1. IMMEDIATE HIGH-YIELD COMPLETION (Guaranteed points)
        if has_empty_wasabi and card == "Squid Nigiri":
            score += 100  # 9 pts
        elif my_played["Sashimi"] % 3 == 2 and card == "Sashimi":
            score += 95   # 10 pts
        elif my_played["Tempura"] % 2 == 1 and card == "Tempura":
            score += 90   # 5 pts
        elif has_empty_wasabi and card == "Salmon Nigiri":
            score += 85   # 6 pts
        elif has_empty_wasabi and card == "Egg Nigiri":
            score += 80   # 3 pts
            
        # 2. CRITICAL HATE-DRAFTING (Denial)
        elif card == "Sashimi" and enemy_played["Sashimi"] >= 2:
            score += 75   # Deny 10 points
        elif card == "Squid Nigiri" and enemy_has_empty_wasabi:
            score += 70   # Deny 9 points
            
        # 3. MAKI DOMINANCE (Comparative scoring)
        elif "Maki Roll" in card:
            maki_val = int(card.split("(")[1][0])
            score += 40 + (maki_val * 5) # Scale based on Maki count
            
        # 4. SETUP & PROBABILITY (Early round investments)
        elif cards_left >= 7:
            if card == "Wasabi":
                score += 65
            elif card == "Sashimi" and my_played["Sashimi"] % 3 == 0:
                score += 60
            elif card == "Tempura" and my_played["Tempura"] % 2 == 0:
                score += 55
                
        # PENALTY: Avoid useless setups late in the round
        if cards_left <= 3 and card in ["Wasabi", "Sashimi", "Tempura"]:
            # Only penalize if it doesn't complete a set (handled in Step 1)
            score -= 100 
                
        # 5. PUDDING BUFFER (Endgame mitigation)
        elif card == "Pudding":
            score += 30
            if state.round == 3:
                score += 20 # Critical in final round to avoid -4 pts
                
        # 6. CHOPSTICKS EFFICIENCY
        elif card == "Chopsticks":
            if cards_left >= 7: 
                score += 50
            else:
                score -= 100 # Never draft late
                
        # BASE SCORING (Fallbacks if no high-priority conditions are met)
        if score == 0:
            if card == "Squid Nigiri": score += 25
            elif card == "Dumpling": score += 15 + (my_played["Dumpling"] * 5)
            elif card == "Salmon Nigiri": score += 10
            elif card == "Egg Nigiri": score += 5
            
        # Update best card
        if score > highest_score:
            highest_score = score
            best_index = i

    return best_index