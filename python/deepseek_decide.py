"""
deepseek_decde.py - Advanced Sushi Go! decision model
Implements set completion, wasabi synergy, pudding endgame, and chopsticks timing.
"""

from collections import Counter
from math import inf

# Base scores for each card type (average expected points if picked early)
BASE_SCORES = {
    "Egg Nigiri": 1.0,
    "Salmon Nigiri": 2.0,
    "Squid Nigiri": 3.0,
    "Tempura": 2.5,          # 5 points per pair → average 2.5 per card
    "Sashimi": 3.33,         # 10 points per set of 3 → average 3.33 per card
    "Dumpling": 0.0,         # calculated dynamically
    "Maki Roll (1)": 1.5,    # rough value based on competition
    "Maki Roll (2)": 2.5,
    "Maki Roll (3)": 3.5,
    "Wasabi": 2.0,           # potential to triple a Nigiri later
    "Pudding": 0.0,          # endgame value, weighted by round
    "Chopsticks": 4.0,       # flexibility, higher early
}

def decide(hand, state):
    """
    Main decision function. Returns index of the best card to play.
    `hand`: list of card names (strings) in current hand.
    `state`: dictionary containing game state from the client.
    """
    played_cards = state.played_cards
    played_counts = Counter(played_cards)
    hand_counts = Counter(hand)
    current_round = state.round
    player_count = state.player_count
    puddings_owned = state.puddings
    has_unused_wasabi = state.has_unused_wasabi

    # Calculate a score for each card in hand
    scores = []
    for idx, card in enumerate(hand):
        score = score_card(
            card,
            hand_counts,
            played_counts,
            current_round,
            player_count,
            puddings_owned,
            has_unused_wasabi,
            state
        )
        scores.append((score, idx))

    # Return index of highest score
    best_idx = max(scores, key=lambda x: x[0])[1]
    return best_idx

def score_card(card, hand_counts, played_counts, round_num, player_count,
               puddings_owned, has_unused_wasabi, state):
    """
    Compute a priority score for a single card based on current context.
    """
    # Start with base score
    base = BASE_SCORES.get(card, 0.0)
    score = base

    # ----- Wasabi & Nigiri synergy -----
    if card in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri"):
        # If we have an unused Wasabi, this Nigiri becomes extremely valuable
        if has_unused_wasabi:
            # Triple value: 3, 6, or 9 points from the combination
            if card == "Squid Nigiri":
                score += 6.0   # 9 total (3 base + 6 bonus)
            elif card == "Salmon Nigiri":
                score += 4.0   # 6 total
            else:  # Egg Nigiri
                score += 2.0   # 3 total
        else:
            # Slight bonus if we already have a Wasabi but it's used? No, has_unused_wasabi is the flag.
            pass

    if card == "Wasabi":
        # Wasabi is valuable if we don't have one unused already.
        # Estimate its worth as the expected value of a future Nigiri (average ~2 points * 2 = 4 extra)
        if not has_unused_wasabi:
            # If we already have a Nigiri in hand, even better
            # Count Nigiri in current hand (excluding this Wasabi)
            nigiri_in_hand = hand_counts.get("Egg Nigiri", 0) + \
                             hand_counts.get("Salmon Nigiri", 0) + \
                             hand_counts.get("Squid Nigiri", 0)
            if nigiri_in_hand > 0:
                score += 5.0   # High chance to combo immediately
            else:
                score += 3.0   # Still good for future
        else:
            score -= 2.0       # Second Wasabi is much less useful

    # ----- Tempura set completion -----
    if card == "Tempura":
        current = played_counts.get("Tempura", 0)
        if current % 2 == 1:
            # We have an odd number → picking this completes a pair (5 points total)
            score += 2.5       # Boost to reflect immediate gain
        else:
            # Even count (including zero) → this starts a new pair
            score -= 0.5       # Slight penalty because it's speculative

    # ----- Sashimi set completion -----
    if card == "Sashimi":
        current = played_counts.get("Sashimi", 0)
        mod = current % 3
        if mod == 2:
            # Two already → this completes a set (10 points)
            score += 6.67      # Big boost
        elif mod == 1:
            # One already → this gets us to two, so still high value
            score += 3.33
        else:
            # None → starting a set, moderate value
            pass

    # ----- Dumplings (increasing marginal value) -----
    if card == "Dumpling":
        current = played_counts.get("Dumpling", 0)
        # Dumpling scoring: 1,3,6,10,15 for 1..5
        marginal = [1, 2, 3, 4, 5]  # marginal gain for the (k+1)th dumpling
        if current < 5:
            # Next dumpling gives marginal[current] points
            score += marginal[current]
        else:
            # Beyond 5, each extra is worthless (still 15 total)
            score -= 5          # penalty for useless card

    # ----- Maki Rolls (compete for majority) -----
    if "Maki Roll" in card:
        # Extract number of rolls from card name (e.g., "Maki Roll (2)" -> 2)
        try:
            rolls = int(card.split("(")[1][0])
        except:
            rolls = 1
        current_maki = sum(
            int(c.split("(")[1][0]) for c in played_counts
            if "Maki Roll" in c
        )
        total_with = current_maki + rolls
        # Simple heuristic: if we have few, it's not worth competing; if we have many, we might want to secure lead
        if total_with > 5:   # arbitrary threshold
            score += rolls * 1.5   # extra bonus
        else:
            score += rolls * 0.5

    # ----- Pudding (endgame importance) -----
    if card == "Pudding":
        # Base priority increases with round
        if round_num == 1:
            score += 5
        elif round_num == 2:
            score += 10
        else:  # round 3
            score += 20
        # Adjust based on how many we already have
        # In a 2-player game, you want at least 1 to avoid last place
        if puddings_owned == 0:
            score += 10        # desperate for first pudding
        elif puddings_owned == 1:
            score += 5         # safe but could be better
        else:
            score -= 5         # already have a lead, don't overcommit

    # ----- Chopsticks (early value) -----
    if card == "Chopsticks":
        # More valuable in early rounds and early turns
        turn = state.turn
        if round_num == 1 and turn < 5:
            score += 8
        elif round_num == 2 and turn < 5:
            score += 5
        else:
            score += 2

    # ----- Denial heuristic (take cards that are critical for opponents) -----
    # Without direct info, we can only guess based on what's left in hand.
    # If a card is rare in the current hand, it might be the last chance for someone.
    # We'll add a small bonus to cards that appear only once in hand.
    if hand_counts[card] == 1:
        # Might be the last copy; deny potential opponents
        score += 0.5

    return score