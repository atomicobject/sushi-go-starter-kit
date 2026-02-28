from collections import Counter

# ── constants ────────────────────────────────────────────────────────────────

PLAYERS_BY_HAND = {10: 2, 9: 3, 8: 4, 7: 5}

CARD_DEFAULT_FREQUENCIES = {
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

TOTAL_CARDS = 108

# ── card tracking helpers ─────────────────────────────────────────────────────

def find_missing(old_hand: list[str], new_hand: list[str]) -> list[str]:
    """Return cards that were in old_hand but are no longer in new_hand (i.e. played)."""
    count_old = Counter(old_hand)
    count_new = Counter(new_hand)
    missing = []
    for item, count in count_old.items():
        diff = count - count_new[item]
        if diff > 0:
            missing.extend([item] * diff)
    return missing


def update_state(hand: list[str], state) -> None:
    """
    Update state.card_distribution with best estimates of all cards
    currently in play across all hands (seen and unseen).
    """
    # ── first time we see a hand ──────────────────────────────────────────────
    if state.hands is None:
        state.player_count = PLAYERS_BY_HAND.get(len(hand), 2)
        state.hands = [hand.copy()]
        state.hand_num = 0
        state.start_card_num = len(hand)
        state.total_remaining = TOTAL_CARDS
        _recompute_distribution(state)
        return

    # ── hand slot already exists: detect what the opponent played last turn ───
    if state.hand_num < len(state.hands):
        played = find_missing(state.hands[state.hand_num], hand)
        state.enemy_cards_played.extend(played)
        state.hands[state.hand_num] = hand.copy()

    # ── new hand slot (we're seeing a hand position for the first time) ───────
    else:
        state.hands.append(hand.copy())
        state.total_remaining -= len(hand)

    _recompute_distribution(state)


def _recompute_distribution(state) -> None:
    """
    Build state.card_distribution:
      for known hands → use exact counts
      for unseen hands → estimate proportionally from remaining deck
    """
    known_cards: list[str] = []
    for h in state.hands:
        known_cards.extend(h)
    known_count = Counter(known_cards)

    played_count = Counter(state.enemy_cards_played)

    # cards accounted for = in known hands + already played by opponents
    accounted = Counter(known_count)
    accounted.update(played_count)
    # also remove our own played cards
    # (state.played_cards tracks the local player's played pile)

    unseen_hands = state.player_count - len(state.hands)
    unseen_hand_size = state.start_card_num if hasattr(state, "start_card_num") else 9

    distribution: dict[str, float] = {}
    remaining_in_deck = max(0, TOTAL_CARDS - sum(accounted.values()))

    for card, total_freq in CARD_DEFAULT_FREQUENCIES.items():
        in_known = known_count.get(card, 0)
        if unseen_hands == 0 or remaining_in_deck == 0:
            distribution[card] = float(in_known)
        else:
            # expected cards of this type still floating in unseen hands
            remaining_of_type = max(0, total_freq - accounted.get(card, 0))
            proportion = remaining_of_type / remaining_in_deck
            expected_in_unseen = proportion * unseen_hands * unseen_hand_size
            distribution[card] = in_known + expected_in_unseen

    state.card_distribution = distribution


# ── scoring / valuation ───────────────────────────────────────────────────────

def score_card(card: str, hand: list[str], state) -> float:
    """
    Return a heuristic value for playing `card` given the current game state.
    Higher is better.
    """
    played = state.played_cards          # our own played pile this round
    round_num = state.round              # 1-3
    player_count = state.player_count
    dist = state.card_distribution       # estimated counts across all live hands

    tempura_count  = played.count("Tempura")
    sashimi_count  = played.count("Sashimi")
    dumpling_count = played.count("Dumpling")
    wasabi_played  = state.has_unused_wasabi
    has_chopsticks = state.has_chopsticks

    # turns remaining in this round (hand sizes shrink by 1 each turn)
    turns_left = len(hand) - 1

    # ── Tempura ──────────────────────────────────────────────────────────────
    if card == "Tempura":
        need = 2 - (tempura_count % 2)  # 1 if we have odd, 2 if we have even
        # probability another tempura will come through
        tempura_in_play = dist.get("Tempura", 0) - hand.count("Tempura")
        reach = min(turns_left, tempura_in_play)
        if need == 1:          # one more completes a pair → 5 pts
            return 4.5
        elif reach >= 1:       # can likely complete a pair later
            return 3.0
        else:
            return 0.5         # won't complete; nearly worthless

    # ── Sashimi ──────────────────────────────────────────────────────────────
    if card == "Sashimi":
        need = 3 - (sashimi_count % 3)
        sashimi_in_play = dist.get("Sashimi", 0) - hand.count("Sashimi")
        if need == 1:
            return 5.0         # one away from 10 pts
        elif need == 2 and sashimi_in_play >= 2 and turns_left >= 2:
            return 3.5
        elif need == 3 and sashimi_in_play >= 3 and turns_left >= 3:
            return 2.5
        else:
            return 0.3         # can't complete triple

    # ── Dumpling ─────────────────────────────────────────────────────────────
    if card == "Dumpling":
        # scoring: 1,3,6,10,15 for 1-5 dumplings
        DUMP_SCORES = [0, 1, 3, 6, 10, 15]
        current_score = DUMP_SCORES[min(dumpling_count, 5)]
        next_score    = DUMP_SCORES[min(dumpling_count + 1, 5)]
        marginal      = next_score - current_score
        return float(marginal)

    # ── Maki Rolls ───────────────────────────────────────────────────────────
    if card.startswith("Maki Roll"):
        value = int(card.split("(")[1].rstrip(")"))
        my_maki = sum(
            int(c.split("(")[1].rstrip(")")) for c in played if c.startswith("Maki Roll")
        )
        # estimate competitors' maki
        enemy_maki_est = (dist.get("Maki Roll (1)", 0) * 1 +
                          dist.get("Maki Roll (2)", 0) * 2 +
                          dist.get("Maki Roll (3)", 0) * 3) / max(player_count - 1, 1)
        projected = my_maki + value
        # higher maki value cards are intrinsically better
        base = value * 1.2
        if projected > enemy_maki_est:
            base += 2.0        # likely winning maki
        elif projected == enemy_maki_est:
            base += 0.5
        return base

    # ── Nigiri ───────────────────────────────────────────────────────────────
    NIGIRI_BASE = {"Egg Nigiri": 1, "Salmon Nigiri": 2, "Squid Nigiri": 3}
    if card in NIGIRI_BASE:
        base_val = NIGIRI_BASE[card]
        if wasabi_played:
            return base_val * 3 + 1   # triple on wasabi; +1 priority bonus
        return float(base_val)

    # ── Wasabi ───────────────────────────────────────────────────────────────
    if card == "Wasabi":
        if wasabi_played:
            return -1.0        # already have unused wasabi; don't double up
        # value is how likely we are to land a nigiri on top of it
        nigiri_est = (dist.get("Squid Nigiri", 0) * 3 +
                      dist.get("Salmon Nigiri", 0) * 2 +
                      dist.get("Egg Nigiri", 0) * 1)
        nigiri_chance = min(nigiri_est / max(turns_left, 1), 1.0)
        return 2.0 + nigiri_chance * 4.0   # up to 6 value if nigiris are plentiful

    # ── Pudding ──────────────────────────────────────────────────────────────
    if card == "Pudding":
        # worth more in later rounds and when we need catch-up
        base = 1.5
        if round_num == 3:
            base = 3.0         # last round, pudding delta matters most
        elif round_num == 2:
            base = 2.0
        # boost if we have fewer puddings than estimated average
        avg_pudding = dist.get("Pudding", 0) / max(player_count, 1)
        if state.puddings < avg_pudding:
            base += 1.5
        return base

    # ── Chopsticks ───────────────────────────────────────────────────────────
    if card == "Chopsticks":
        if has_chopsticks:
            return -1.0        # already have chopsticks; useless second copy
        if turns_left <= 1:
            return -1.0        # no time to use them
        return 1.0 + turns_left * 0.3   # more valuable early in round

    return 0.0   # unknown card


# ── deny value: how much do we hurt an opponent by taking this card ───────────

def deny_value(card: str, dist: dict[str, float], player_count: int) -> float:
    """
    Extra value from denying an opponent a strong card.
    Only significant in 2-player games.
    """
    if player_count > 2:
        return 0.0
    HIGH_DENY = {"Squid Nigiri", "Sashimi", "Pudding", "Maki Roll (3)"}
    MED_DENY  = {"Salmon Nigiri", "Tempura", "Wasabi", "Maki Roll (2)"}
    if card in HIGH_DENY:
        return 0.5
    if card in MED_DENY:
        return 0.25
    return 0.0


# ── main decide function ──────────────────────────────────────────────────────

def decide(hand: list[str], state) -> int:
    """
    Choose the best card index to play.

    Args:
        hand:  list of card name strings in the player's current hand
        state: GameState object (mutated in place for tracking)

    Returns:
        0-based index into hand
    """
    # ── 1. update tracking ────────────────────────────────────────────────────
    update_state(hand, state)

    # ── 2. advance hand_num for next call ─────────────────────────────────────
    state.hand_num = (state.hand_num + 1) % state.player_count

    # ── 3. score every card in hand ──────────────────────────────────────────
    best_index = 0
    best_score = float("-inf")

    for i, card in enumerate(hand):
        s = score_card(card, hand, state)
        s += deny_value(card, state.card_distribution, state.player_count)
        if s > best_score:
            best_score = s
            best_index = i

    return best_index