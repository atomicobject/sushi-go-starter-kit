from collections import Counter

# ── constants ─────────────────────────────────────────────────────────────────

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
DUMPLING_SCORES = [0, 1, 3, 6, 10, 15]

# ── card tracking ─────────────────────────────────────────────────────────────

def find_missing(old_hand: list[str], new_hand: list[str]) -> list[str]:
    count_old = Counter(old_hand)
    count_new = Counter(new_hand)
    missing = []
    for item, count in count_old.items():
        diff = count - count_new[item]
        if diff > 0:
            missing.extend([item] * diff)
    return missing


def update_state(hand: list[str], state) -> None:
    if state.hands is None:
        state.player_count = PLAYERS_BY_HAND.get(len(hand), 2)
        state.hands = [hand.copy()]
        state.hand_num = 0
        state.start_card_num = len(hand)
        state.total_remaining = TOTAL_CARDS
        _recompute_distribution(state)
        return

    if state.hand_num < len(state.hands):
        played = find_missing(state.hands[state.hand_num], hand)
        state.enemy_cards_played.extend(played)
        state.hands[state.hand_num] = hand.copy()
    else:
        state.hands.append(hand.copy())
        state.total_remaining = max(0, state.total_remaining - len(hand))

    _recompute_distribution(state)


def _recompute_distribution(state) -> None:
    known_cards: list[str] = []
    for h in state.hands:
        known_cards.extend(h)
    known_count = Counter(known_cards)
    played_count = Counter(state.enemy_cards_played)

    accounted = Counter(known_count)
    accounted.update(played_count)

    unseen_hands = state.player_count - len(state.hands)
    unseen_hand_size = getattr(state, "start_card_num", 9)
    remaining_in_deck = max(0, TOTAL_CARDS - sum(accounted.values()))

    distribution: dict[str, float] = {}
    for card, total_freq in CARD_DEFAULT_FREQUENCIES.items():
        in_known = known_count.get(card, 0)
        if unseen_hands == 0 or remaining_in_deck == 0:
            distribution[card] = float(in_known)
        else:
            remaining_of_type = max(0, total_freq - accounted.get(card, 0))
            proportion = remaining_of_type / remaining_in_deck
            expected_in_unseen = proportion * unseen_hands * unseen_hand_size
            distribution[card] = in_known + expected_in_unseen

    state.card_distribution = distribution


# ── scoring ───────────────────────────────────────────────────────────────────

def score_card(card: str, hand: list[str], state) -> float:
    played        = state.played_cards
    round_num     = state.round
    player_count  = state.player_count
    dist          = state.card_distribution
    turns_left    = len(hand) - 1

    played_counts = Counter(played)

    # ── Tempura ──────────────────────────────────────────────────────────────
    if card == "Tempura":
        have = played_counts["Tempura"]
        if have % 2 == 1:
            return 15.0  # one away from completing a pair → grab it
        tempura_available = dist.get("Tempura", 0) - hand.count("Tempura")
        if tempura_available >= 1 and turns_left >= 1:
            return 6.0
        return 1.0

    # ── Sashimi ──────────────────────────────────────────────────────────────
    if card == "Sashimi":
        have = played_counts["Sashimi"] % 3
        sashimi_available = dist.get("Sashimi", 0) - hand.count("Sashimi")
        if have == 2:
            return 18.0  # one away from 10 pts → highest priority
        if have == 1 and sashimi_available >= 1 and turns_left >= 1:
            return 9.0
        if have == 0 and sashimi_available >= 2 and turns_left >= 2:
            return 5.0
        return 0.5

    # ── Dumpling ─────────────────────────────────────────────────────────────
    if card == "Dumpling":
        have = played_counts["Dumpling"]
        marginal = DUMPLING_SCORES[min(have + 1, 5)] - DUMPLING_SCORES[min(have, 5)]
        return float(marginal) + have * 2.0  # aggressive snowball

    # ── Maki Rolls ───────────────────────────────────────────────────────────
    if card.startswith("Maki Roll"):
        roll_value = int(card.split("(")[1].rstrip(")"))
        my_maki = sum(
            int(c.split("(")[1].rstrip(")"))
            for c in played if c.startswith("Maki Roll")
        )
        total_maki_in_dist = (
            dist.get("Maki Roll (1)", 0) * 1
            + dist.get("Maki Roll (2)", 0) * 2
            + dist.get("Maki Roll (3)", 0) * 3
        )
        opponent_maki_est = total_maki_in_dist / max(player_count - 1, 1)
        projected = my_maki + roll_value
        base = roll_value * 1.5
        if projected > opponent_maki_est:
            base += 3.0
        elif projected >= opponent_maki_est:
            base += 1.5
        return base

    # ── Nigiri ───────────────────────────────────────────────────────────────
    NIGIRI_BASE = {"Egg Nigiri": 1, "Salmon Nigiri": 2, "Squid Nigiri": 3}
    if card in NIGIRI_BASE:
        base_val = float(NIGIRI_BASE[card])
        nigiris_played = sum(
            played_counts[n] for n in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri")
        )
        wasabi_available = played_counts.get("Wasabi", 0) > nigiris_played
        if wasabi_available:
            return base_val * 3 + 8.0  # big bonus to beat Gemini's +20
        return base_val

    # ── Wasabi ───────────────────────────────────────────────────────────────
    if card == "Wasabi":
        nigiris_played = sum(
            played_counts[n] for n in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri")
        )
        unused_wasabi = played_counts.get("Wasabi", 0) - nigiris_played
        if unused_wasabi > 0:
            return -2.0  # already have unused wasabi — don't stack
        nigiri_est = (
            dist.get("Squid Nigiri", 0) * 3
            + dist.get("Salmon Nigiri", 0) * 2
            + dist.get("Egg Nigiri", 0) * 1
        )
        reach = min(nigiri_est, turns_left)
        return 2.0 + reach * 1.5

    # ── Pudding ──────────────────────────────────────────────────────────────
    if card == "Pudding":
        base = float(round_num) * 1.5
        avg_pudding = (dist.get("Pudding", 0) + state.puddings) / max(player_count, 1)
        if state.puddings < avg_pudding:
            base += 2.0
        return base

    # ── Chopsticks ───────────────────────────────────────────────────────────
    if card == "Chopsticks":
        if state.has_chopsticks or turns_left <= 1:
            return -3.0
        return 0.5 + turns_left * 0.4

    return 0.0


# ── deny bonus ────────────────────────────────────────────────────────────────

def deny_value(card: str, dist: dict[str, float], player_count: int) -> float:
    """Deny strong cards from opponents. Weighted heavily in 1v1."""
    multiplier = 1.0 if player_count == 2 else 0.3
    HIGH_DENY = {"Squid Nigiri", "Sashimi", "Pudding", "Maki Roll (3)"}
    MED_DENY  = {"Salmon Nigiri", "Tempura", "Wasabi", "Maki Roll (2)"}
    if card in HIGH_DENY:
        return 1.0 * multiplier
    if card in MED_DENY:
        return 0.5 * multiplier
    return 0.0


# ── main decide ───────────────────────────────────────────────────────────────

def decide(hand: list[str], state) -> int:
    """Returns the 0-based index of the card to play."""
    update_state(hand, state)
    state.hand_num = (state.hand_num + 1) % state.player_count

    best_index = 0
    best_score = float("-inf")

    for i, card in enumerate(hand):
        s = score_card(card, hand, state)
        s += deny_value(card, state.card_distribution, state.player_count)
        if s > best_score:
            best_score = s
            best_index = i

    return best_index
