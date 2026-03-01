# Hackathon Results (updated Feb 28, 2026)

This repo is a fork or Atomic Object's suchi-go-starter-kit. For this hackathon, we chose to implement our Sushi Go bot in Python. The winning bot is `python/tournament_bot.py`. We used `python/sushi_go_client.py` as a baseline bot to test how well we could get our custom bot to perform. We tried a variety of methods and strategies that did not work very well and had scrapped them before the tournament.

# Sushi Go Starter Kit

Build a bot to play Sushi Go against other players on a networked game server.

## Game Rules

Sushi Go is a card-drafting game by Gamewright. Find the rules online or get a copy of the game!

## Quick Start

### Prerequisites

- **Python 3.10+** (no external packages needed), or
- **Node.js 18+** (no npm dependencies needed)

### Run the Demo Bot

```bash
# Python — plays the first card every turn
python python/first_card_bot.py <game_id> <your_name>

# Python — priority-based strategy
python python/sushi_go_client.py localhost 7878 <game_id> <your_name>

# JavaScript — priority-based strategy
node javascript/sushi_go_client.js localhost 7878 <game_id> <your_name>
```

Replace `<game_id>` with the game ID shown in the web UI or given to you by the tournament organizer.

## Running a Test Server

First, load the server image from the LAN:

```bash
curl https://joes-macbook.tail10906.ts.net/sushi-go-test.tar | docker load
```

or

```bash
curl http://joes-macbook.local:9090/sushi-go-test.tar | docker load
```


Then start it:

```bash
docker run -p 7878:7878 -p 8080:8080 sushi-go-test
```

- **Port 7878** — TCP game port (where your bot connects)
- **Port 8080** — Web UI for creating games and spectating

Open http://localhost:8080 in a browser, create a game, then run your bot with the game ID.

## Building Your Bot

The basic pattern every bot follows:

1. Connect to the server via TCP
2. Send `JOIN <game_id> <your_name>`
3. Send `READY`
4. Wait for messages in a loop
5. When you receive `HAND`, choose a card and send `PLAY <index>`
6. Repeat until `GAME_END`

See `python/first_card_bot.py` for a minimal working example (~30 lines of game logic).

## Customizing

The starter clients include a strategy function you can edit:

- **Python:** `choose_card(hand)` in `sushi_go_client.py`
- **JavaScript:** `chooseCard(hand)` in `sushi_go_client.js`

The `hand` parameter is a list of card names (e.g., `["Tempura", "Salmon Nigiri", "Pudding"]`). Return the index of the card you want to play.

Or, write your bot from scratch — all you need is a TCP socket and the protocol below.

## Language Guides

- [Python Guide](python/README.md)
- [JavaScript Guide](javascript/README.md)

## Protocol Reference

See [PROTOCOL.md](PROTOCOL.md) for the full protocol specification, including:

| You Send | Server Sends |
|----------|-------------|
| `JOIN <game_id> <name>` | `WELCOME <game_id> <id> <token>` |
| `READY` | `OK` |
| `PLAY <index>` | `OK` |
| `CHOPSTICKS <i> <j>` | `OK` |
| `REJOIN <token>` | `REJOINED <game_id> <id>` |
| | `HAND 0:Card 1:Card ...` (your turn) |
| | `PLAYED ...` (turn results) |
| | `ROUND_END ...` / `GAME_END ...` |
