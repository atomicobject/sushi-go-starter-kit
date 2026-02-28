# Sushi Go AI Competition Context

## Overview

This is a **card-drafting game AI competition** using the Sushi Go board game. You will develop AI bots in the **Python folder** that compete against other players on a networked game server in a tournament bracket.

## Game Details

**Sushi Go** is a fast-paced, turn-based card game:
- **2-5 players** per game
- **3 rounds** per game
- Each round: Players simultaneously draft cards from a hand, strategically choosing which cards to keep and which to pass
- **Scoring** based on card combinations:
  - Nigiri (Egg, Salmon, Squid): Base points, doubled with Wasabi
  - Maki Rolls: Bonus points for highest/second-highest count
  - Tempura & Sashimi: Bonus for pairs/triples
  - Dumpling: Escalating points (1→5 cards)
  - Pudding: Major end-game bonus for highest/lowest counts
  - Wasabi: Multiplier for next nigiri
  - Chopsticks: Play two cards in one turn (special mechanic)

## Project Structure

```
python/
├── first_card_bot.py       # Minimal bot (~30 lines) - always plays first card
├── sushi_go_client.py      # Full-featured bot with state tracking
└── README.md               # Python-specific documentation
```

## Your Work Focus

**Location:** `python/` folder (this is where you'll implement your AI)

**Main Strategy Function:** `choose_card(hand: list[str]) -> int` in `sushi_go_client.py`
- Input: List of card names you're holding
- Output: Index (0-based) of the card to play
- This is where your AI decision logic lives

**Optional:** `CHOPSTICKS <idx1> <idx2>` protocol support (play two cards if you have chopsticks)

## Running Your Bot

```bash
# Full-featured client (recommended for tournament)
python sushi_go_client.py <host> <port> <game_id> <player_name>
python sushi_go_client.py localhost 7878 abc123 MyAIBot

# Minimal client (for testing)
python first_card_bot.py <game_id> <player_name> [host] [port]
```

## Key Game Mechanics for AI Strategy

### Card Categories
- **Nigiri:** Individual points with Wasabi multiplier
- **Maki Rolls:** Majority bonus (1st/2nd place get points)
- **Sets:** Tempura (2 = 5pts), Sashimi (3 = 10pts), Dumpling (1-5 = 1-15pts)
- **End-Game:** Pudding (high/low count scoring at game end)
- **Special:** Droplets, Tea/Soy Sauce (variant cards)

### Strategic Considerations
- **Pass mechanics:** Cards you don't play go to opponents
- **Majority plays:** Maki rolls reward concentration (2-3 rolls beating 1-2 rolls)
- **Timing:** End-game pudding needs strategic planning early
- **Chopsticks:** Rare opportunity to play two cards - saves turns or completes sets
- **Wasabi value:** Can triple next nigiri, plan accordingly

## Protocol Reference

### Core Commands Your Bot Sends
| Command | When |
|---------|------|
| `JOIN <game_id> <name>` | Connect and enter game |
| `READY` | Signal you're ready to start |
| `PLAY <index>` | Play card at index from current hand |
| `CHOPSTICKS <i> <j>` | Play two cards using chopsticks |

### Server Messages to Handle
| Message | Meaning |
|---------|---------|
| `WELCOME ...` | Successfully joined - you get a rejoin token |
| `HAND 0:Card1 1:Card2 ...` | **Your turn** - choose a card to play |
| `PLAYED ...` | Results of the turn (all players' cards revealed simultaneously) |
| `ROUND_END ...` | Round finished with scores |
| `GAME_END ...` | Game over with final results |

See `PROTOCOL.md` for full specification.

## Tournament Format

- **Bracket-style elimination** with matches assigned dynamically
- Each match is a standard 2-player game (your bot + opponent)
- Winners advance; losers are eliminated
- Byes awarded to odd player counts per round

### Tournament Commands
```
TOURNEY <tournament_id> <player_name>           # Join tournament
(wait for TOURNAMENT_MATCH with match_token)
TJOIN <match_token>                             # Accept match assignment
(then standard game flow: WELCOME, HAND, PLAY...)
```

## Testing Your Bot Locally

```bash
# Start test server (requires Docker)
curl https://joes-macbook.tail10906.ts.net/sushi-go-test.tar | docker load
docker run -p 7878:7878 -p 8080:8080 sushi-go-test

# Open http://localhost:8080 in browser
# Create a game, get game_id, then run:
python python/sushi_go_client.py localhost 7878 <game_id> YourBotName
```

## Starter Bot Features

### `sushi_go_client.py` (recommended template)
- State tracking: Tracks all played cards, scores, hand history
- Card parsing: Understands Sushi Go card syntax
- Default strategy: Basic priority list (Maki > Nigiri > Sets > Misc)
- Ready for tournament: Has proper error handling and protocol support

### `first_card_bot.py` (minimal template)
- ~30 lines of game logic
- Always plays the first card (no strategy)
- Useful for quick testing or understanding the protocol

## Important Implementation Notes

1. **Line-buffered reading:** Use `socket.makefile('r')` for reliable reading
2. **HAND = your turn:** Only respond to HAND messages with PLAY
3. **Rejoin support:** Consider handling disconnection with rejoin tokens
4. **Simultaneous play:** All players submit moves, then results are revealed
5. **Pass order:** Hand direction changes each round (clockwise/counterclockwise)

## Card Names (Official)

Tempura, Sashimi, Dumpling, Maki Roll (1), Maki Roll (2), Maki Roll (3), Egg Nigiri, Salmon Nigiri, Squid Nigiri, Pudding, Wasabi, Chopsticks

## Next Steps for Development

1. **Understand the state:** Use `self.state` in `sushi_go_client.py` to track game progress
2. **Implement `choose_card`:** Replace the default strategy with your AI logic
3. **Test locally:** Run against the test server and other bots
4. **Refine strategy:** Iterate based on tournament performance
5. **Optimize for tournament:** Consider opponent diversity and optimal bet strategy

## Requirements

- Python 3.10+
- **No external packages** - standard library only
- TCP socket support (built-in)
