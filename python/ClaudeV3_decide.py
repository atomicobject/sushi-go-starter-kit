from collections import Counter

# ── constants ─────────────────────────────────────────────────────────────────

PLAYERS_BY_HAND = {10: 2, 9: 3, 8: 4, 7: 5}

CARD_DEFAULT_FREQUENCIES = {
    "Tempura":        14,
    "Sashimi":        14,
    "Dumpling":       14,
    "Maki Roll (1)":   6,
    "Maki Roll (2)":  12,
    "Maki Roll (3)":   3,
    "Egg Nigiri":      5,
    "Salmon Nigiri":  10,
    "Squid Nigiri":    5,
    "Pudding":        10,
    "Wasabi":          6,
    "Chopsticks":      4,
}

TOTAL_CARDS   = 108
DUMP_SCORES   = [0, 1, 3, 6, 10, 15]

# Gemini's battle-tested base priorities — these win tiebreaks correctly
BASE_PRIORITY = {
    "Chopsticks":     0,
    "Egg Nigiri":     1,
    "Maki Roll (1)":  2,
    "Maki Roll (2)":  3,
    "Maki Roll (3)":  4,
    "Pudding":        5,
    "Tempura":        6,
    "Sashimi":        7,
    "Dumpling":       8,
    "Salmon Nigiri":  9,
    "Squid Nigiri":  10,
    "Wasabi":        11,
}

# ── card tracking (Drake's distribution system) ───────────────────────────────

def _find_missing(old_hand: list, new_hand: list) -> list:
    """Cards in old_hand that disappeared → were played by that opponent."""
    c1, c2 = Counter(old_hand), Counter(new_hand)
    out = []
    for item, cnt in c1.items():
        diff = cnt - c2[item]
        if diff > 0:
            out.extend([item] * diff)
    return out


def _recompute_distribution(state) -> None:
    """
    Estimate how many of each card exist across ALL live hands
    (known hands exact + unseen hands estimated from deck proportions).
    O(num_card_types) — very fast.
    """
    known: list = []
    for h in state.hands:
        known.extend(h)
    known_cnt   = Counter(known)
    played_cnt  = Counter(state.enemy_cards_played)

    accounted   = known_cnt + played_cnt          # total cards we've observed
    deck_left   = max(0, TOTAL_CARDS - sum(accounted.values()))
    unseen_n    = state.player_count - len(state.hands)
    hand_size   = getattr(state, "start_card_num", 9)

    dist = {}
    for card, freq in CARD_DEFAULT_FREQUENCIES.items():
        in_known  = known_cnt.get(card, 0)
        if unseen_n == 0 or deck_left == 0:
            dist[card] = float(in_known)
        else:
            remaining = max(0, freq - accounted.get(card, 0))
            expected  = (remaining / deck_left) * unseen_n * hand_size
            dist[card] = in_known + expected

    state.card_distribution = dist


def update_state(hand: list, state) -> None:
    """Update tracking each time we receive a new hand. O(hand_size)."""
    if state.hands is None:
        # First call — initialise everything
        state.player_count   = PLAYERS_BY_HAND.get(len(hand), 2)
        state.hands          = [hand.copy()]
        state.hand_num       = 0
        state.start_card_num = len(hand)
        _recompute_distribution(state)
        return

    if state.hand_num < len(state.hands):
        # We've seen this hand position before — diff it to find what was played
        played = _find_missing(state.hands[state.hand_num], hand)
        state.enemy_cards_played.extend(played)
        state.hands[state.hand_num] = hand.copy()
    else:
        # New hand position coming into view
        state.hands.append(hand.copy())

    _recompute_distribution(state)


# ── scoring (Gemini's logic + distribution awareness) ────────────────────────

def _score(card: str, hand: list, state) -> float:
    """
    Priority score for one card.
    Starts from Gemini's proven base priorities, then applies
    context bonuses informed by Drake's distribution data.
    All arithmetic is simple — no loops — well under 1 ms per card.
    """
    played       = state.played_cards
    dist         = state.card_distribution
    player_count = state.player_count
    round_num    = state.round
    turns_left   = len(hand) - 1          # picks remaining after this one

    played_cnt   = Counter(played)         # O(|played|), cached implicitly per call
    priority     = float(BASE_PRIORITY.get(card, 0))

    # ── Wasabi + Nigiri (Gemini's decisive +20) ───────────────────────────────
    if card in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri"):
        nigiris_down = sum(played_cnt[n] for n in
                           ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri"))
        unused_wasabi = played_cnt.get("Wasabi", 0) - nigiris_down
        if unused_wasabi > 0:
            priority += 20   # Gemini's exact bonus — proven effective

    # ── Tempura ──────────────────────────────────────────────────────────────
    if card == "Tempura":
        have = played_cnt["Tempura"]
        if have % 2 == 1:
            priority += 10                           # one away → complete it
        else:
            # Only start a new pair if more tempura are reachable
            available = dist.get("Tempura", 0) - hand.count("Tempura")
            if available < 1 or turns_left < 1:
                priority -= 4                        # no partner coming; deprioritise

    # ── Sashimi ──────────────────────────────────────────────────────────────
    if card == "Sashimi":
        have = played_cnt["Sashimi"] % 3
        available = dist.get("Sashimi", 0) - hand.count("Sashimi")
        if have == 2:
            priority += 10                           # one away from 10 pts
        elif have == 1:
            if available >= 1 and turns_left >= 1:
                priority += 5
            else:
                priority -= 5                        # can't complete; dead card
        elif have == 0:
            if available >= 2 and turns_left >= 2:
                priority += 2
            else:
                priority -= 5                        # no path to triple

    # ── Dumpling (Gemini's * 2 snowball) ─────────────────────────────────────
    if card == "Dumpling":
        have     = played_cnt["Dumpling"]
        marginal = DUMP_SCORES[min(have + 1, 5)] - DUMP_SCORES[min(have, 5)]
        priority += marginal + have * 2              # exact Gemini formula + marginal

    # ── Maki Rolls ───────────────────────────────────────────────────────────
    if card.startswith("Maki Roll"):
        roll_val = int(card.split("(")[1].rstrip(")"))
        priority += roll_val                         # Gemini's simple face-value bonus
        # Distribution bonus: are we winning maki?
        my_maki = sum(
            int(c.split("(")[1].rstrip(")"))
            for c in played if c.startswith("Maki Roll")
        )
        total_dist_maki = (dist.get("Maki Roll (1)", 0)
                           + dist.get("Maki Roll (2)", 0) * 2
                           + dist.get("Maki Roll (3)", 0) * 3)
        opp_maki_est = total_dist_maki / max(player_count - 1, 1)
        if my_maki + roll_val > opp_maki_est:
            priority += 2    # leading on maki → press the advantage

    # ── Wasabi (value depends on nigiri supply) ───────────────────────────────
    if card == "Wasabi":
        nigiris_down  = sum(played_cnt[n] for n in
                            ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri"))
        unused_wasabi = played_cnt.get("Wasabi", 0) - nigiris_down
        if unused_wasabi > 0:
            priority -= 13   # already have unused wasabi; don't stack
        else:
            nigiri_supply = (dist.get("Squid Nigiri", 0) * 3
                             + dist.get("Salmon Nigiri", 0) * 2
                             + dist.get("Egg Nigiri", 0))
            if nigiri_supply < 1 or turns_left < 1:
                priority -= 8   # no nigiris coming; wasabi is worthless

    # ── Pudding ───────────────────────────────────────────────────────────────
    if card == "Pudding":
        priority += round_num                        # Gemini's exact bonus
        # Extra push if we're behind the average pudding count
        avg = (dist.get("Pudding", 0) + state.puddings) / max(player_count, 1)
        if state.puddings < avg:
            priority += 2

    # ── Chopsticks ────────────────────────────────────────────────────────────
    if card == "Chopsticks":
        if state.has_chopsticks or turns_left <= 1:
            priority -= 10   # useless second copy or no time to use
        else:
            priority += turns_left * 0.3

    return priority


def _deny(card: str, player_count: int) -> float:
    """
    Small bonus for taking a card that would strongly benefit opponents.
    Only material in 1v1; negligible in 4-player.
    """
    if player_count > 2:
        return 0.0
    HIGH = {"Squid Nigiri", "Sashimi", "Pudding", "Maki Roll (3)"}
    MED  = {"Salmon Nigiri", "Tempura", "Maki Roll (2)"}
    if card in HIGH: return 1.0
    if card in MED:  return 0.5
    return 0.0


# ── public entry point ────────────────────────────────────────────────────────

def decide(hand: list, state) -> int:
    """
    Returns the 0-based index of the best card to play.
    Total runtime: O(hand_size * |played|) — comfortably under 1 ms.
    """
    # Update distribution tracking
    update_state(hand, state)
    state.hand_num = (state.hand_num + 1) % state.player_count

    best_idx   = 0
    best_score = float("-inf")

    for i, card in enumerate(hand):
        s = _score(card, hand, state) + _deny(card, state.player_count)
        if s > best_score:
            best_score = s
            best_idx   = i

    return best_idx
