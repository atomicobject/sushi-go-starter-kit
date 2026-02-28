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

To join a game on someone else's laptop
```bash
python first_card_bot.py <ip_address> <port> <game_id> <your_name>
```

Replace `<game_id>` with the game ID shown in the web UI or given to you by the tournament organizer.

## Running a Test Server

First, load the server image from the LAN:

```bash
curl -O https://joes-macbook.tail10906.ts.net/sushi-go-test.tar && docker load < sushi-go-test.tar
```

or 

```bash
curl -O http://joes-macbook.local:9090/sushi-go-test.tar && docker load < sushi-go-test.tar
```


Then start it:

```bash
docker run -it -p 7878:7878 -p 8080:8080 sushi-go-test
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

## Handling Disconnects (Rejoin Tokens)

When your bot joins a game, the server sends back a **rejoin token** in the `WELCOME` message:

```
WELCOME myGame 0 fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                  Save this! It's your lifeline.
```

If your bot crashes or loses its connection, you can reconnect and send `REJOIN <token>` instead of `JOIN`. This restores your session — you keep your seat, your cards, and your score. Other players won't even notice you disconnected.

### How to use it

1. **Save the token** when you receive `WELCOME` (the 4th field)
2. If you disconnect, open a new TCP connection
3. Send `REJOIN <token>` instead of `JOIN`
4. Server responds with `REJOINED <game_id> <player_id>` — you're back in
5. You'll receive the next `HAND` message when it's your turn, just like normal

### Tips

- Save the token to a file so your bot can read it on restart
- You do **not** need to send `READY` again after rejoining
- The token is a random 32-character string unique to your seat in that game
- If the game has already ended, `REJOIN` will return an error

### Example reconnect flow

```
# First connection
>>> JOIN myGame Alice
<<< WELCOME myGame 0 fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
>>> READY
<<< OK
<<< HAND 0:Tempura 1:Sashimi ...
>>> PLAY 0
<<< OK

# Connection drops...

# New connection
>>> REJOIN fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
<<< REJOINED myGame 0
<<< HAND 0:Dumpling 1:Pudding ...   (game continues)
>>> PLAY 1
<<< OK
```

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
