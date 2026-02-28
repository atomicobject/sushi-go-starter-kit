# Python Client

There are two ways to build a bot: with the **SDK** (recommended) or with **standalone scripts**.

## Option 1: Using the SDK (Recommended)

The `ao_games` SDK handles connections, message parsing, and state tracking for you. You just implement `choose_card()`.

### Install

```bash
pip install "ao_games @ git+https://github.com/atomicobject/sushi-go-starter-kit.git#subdirectory=python"
```

Or add to `requirements.txt`:

```
ao_games @ git+https://github.com/atomicobject/sushi-go-starter-kit.git#subdirectory=python
```

Requires Python 3.10+. No other dependencies.

### Quick Start

Copy `sdk_bot.py` and edit the `choose_card` method:

```python
from ao_games import Bot, Card, HandCard, GameState, run_bot

class MyBot(Bot):
    def choose_card(self, hand: list[HandCard], state: GameState) -> int:
        # hand is a list of HandCard(index, card)
        # Return the index of the card you want to play
        return hand[0].index  # your strategy here!

run_bot(MyBot(), "game_id", "MyName", "localhost", 7878)
```

```bash
python sdk_bot.py <game_id> <player_name> [host] [port]
python sdk_bot.py abc123 MyBot 192.168.1.50 7878
```

### What You Get

Each `HandCard` has an `.index` (int) and a `.card` (`Card` enum). You can inspect cards:

```python
for hc in hand:
    print(hc.card.display_name)  # "Salmon Nigiri"
    print(hc.card.code)          # "SAL"
    print(hc.card.is_nigiri)     # True
    print(hc.card.nigiri_points) # 2
    print(hc.card.maki_count)    # 0
```

The `state` object tracks everything — round, turn, what others played, scores:

```python
state.round            # Current round number
state.turn             # Current turn number
state.last_plays       # [(name, [Card, ...]), ...] from last turn
state.round_scores     # {round_num: {name: RoundScore}}
state.player_count     # Number of players
```

### Lifecycle Hooks

Override any of these for more control:

```python
class MyBot(Bot):
    def choose_card(self, hand, state) -> int: ...         # Required
    def on_game_start(self, state): ...                    # Game begins
    def on_round_start(self, round_num, state): ...        # Round begins
    def on_turn_result(self, plays, state): ...            # See what everyone played
    def on_round_end(self, round_num, state): ...          # Round scores available
    def on_game_end(self, state): ...                      # Final scores available
```

### Using Chopsticks

Return a tuple of two indices to play two cards:

```python
def choose_card(self, hand, state) -> int | tuple[int, int]:
    # Play two cards if you have chopsticks available
    return (hand[0].index, hand[1].index)
```

### Card Types

| Card | Enum | Code |
|------|------|------|
| Tempura | `Card.TEMPURA` | `TMP` |
| Sashimi | `Card.SASHIMI` | `SSH` |
| Dumpling | `Card.DUMPLING` | `DMP` |
| Maki Roll (1/2/3) | `Card.MAKI_1` / `MAKI_2` / `MAKI_3` | `MK1` / `MK2` / `MK3` |
| Egg Nigiri | `Card.EGG_NIGIRI` | `EGG` |
| Salmon Nigiri | `Card.SALMON_NIGIRI` | `SAL` |
| Squid Nigiri | `Card.SQUID_NIGIRI` | `SQD` |
| Pudding | `Card.PUDDING` | `PUD` |
| Wasabi | `Card.WASABI` | `WAS` |
| Chopsticks | `Card.CHOPSTICKS` | `CHP` |

---

## Option 2: Standalone Scripts (No Install)

These scripts use only the standard library — no `pip install` needed.

| File | Description |
|------|-------------|
| `first_card_bot.py` | Minimal bot (~30 lines of logic) that always plays the first card |
| `sushi_go_client.py` | Full-featured client with state tracking and a priority-based strategy |

```bash
# first_card_bot.py — game_id and name first, host/port optional
python first_card_bot.py <game_id> <player_name> [host] [port]
python first_card_bot.py abc123 MyBot
python first_card_bot.py abc123 MyBot 192.168.1.50 7878

# sushi_go_client.py — host and port first
python sushi_go_client.py <host> <port> <game_id> <player_name>
python sushi_go_client.py localhost 7878 abc123 MyBot
```

Edit the `choose_card` method in either file to implement your strategy.

### Key Patterns

**HAND = your turn**: Only send `PLAY` when you receive a `HAND` message. The server sends `HAND` exactly when it's time for you to act.

**State tracking**: `sushi_go_client.py` tracks played cards, chopsticks, and wasabi state for you. Use `self.state` to make smarter decisions.

## Rejoin After Disconnect

The starter clients save the rejoin token from the `WELCOME` message. If your bot crashes, you can reconnect using that token instead of joining fresh:

```python
import socket

host, port = "localhost", 7878
token = "fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8"  # saved from WELCOME

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))
sock_file = sock.makefile("r")

sock.sendall(f"REJOIN {token}\n".encode())
response = sock_file.readline().strip()
# response: "REJOINED myGame 0"
```

For a production bot, save the token to a file on join and read it back on startup:

```python
# On join — save token
with open("rejoin_token.txt", "w") as f:
    f.write(rejoin_token)

# On restart — check for saved token
try:
    with open("rejoin_token.txt") as f:
        token = f.read().strip()
    send(f"REJOIN {token}")
except FileNotFoundError:
    send(f"JOIN {game_id} {player_name}")
```

See the [main README](../README.md#handling-disconnects-rejoin-tokens) for more details.

## Protocol

See [../PROTOCOL.md](../PROTOCOL.md) for the full protocol specification.
