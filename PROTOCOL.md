# Sushi Go Protocol Reference

This document describes the TCP protocol used to communicate with the Sushi Go game server.

All communication is **plain text, line-delimited** (each message ends with `\n`). Connect via TCP to the server's game port (default `7878`).

## Client Commands

Commands you send to the server:

| Command | Description |
|---------|-------------|
| `JOIN <game_id> <player_name>` | Join an existing game |
| `REJOIN <token>` | Rejoin after disconnect using your rejoin token |
| `READY` | Signal ready to start (idempotent — returns OK if game already started) |
| `PLAY <card_index>` | Play a card by its 0-based index |
| `CHOPSTICKS <idx1> <idx2>` | Use chopsticks to play two cards (indices must differ) |
| `STATUS` | Request current game state |
| `GAMES` | List joinable games |
| `LEAVE` | Leave current game |

## Server Messages

Messages the server sends to you:

| Message | Description |
|---------|-------------|
| `WELCOME <game_id> <player_id> <rejoin_token>` | Successfully joined a game |
| `REJOINED <game_id> <player_id>` | Successfully rejoined after disconnect |
| `JOINED <player_name> <count>/<max>` | Another player joined your game |
| `OK [details]` | Command succeeded |
| `ERROR <code> <message>` | Command failed (see Error Codes below) |
| `GAME_START <player_count>` | Game is starting |
| `PLAYER_ORDER <name1>,<name2>,...` | Player seating order (sent right after `GAME_START`) |
| `ROUND_START <round>` | New round beginning (1, 2, or 3) |
| `HAND <idx:card> ...` | Your current hand — **this means it's your turn to play** |
| `PLAYED <player1>:<cards>; <player2>:<cards>; ...` | All cards played this turn (revealed simultaneously) |
| `WAITING <player_names...>` | Players who haven't acted yet |
| `ROUND_END <round> <scores_json>` | Round finished with scores |
| `GAME_END <final_scores_json> <winners_json>` | Game over with final results |

## Player Order

Immediately after `GAME_START`, the server sends a `PLAYER_ORDER` message with the comma-separated names of all players in seating order:

```
PLAYER_ORDER Alice,Bob,Charlie
```

Hands pass from `player[i]` to `player[i+1]` each turn (wrapping from last to first). Knowing the seating order lets you anticipate which cards will reach you.

Old clients that don't recognize `PLAYER_ORDER` can safely ignore it.

## HAND Message Format

The `HAND` message tells you what cards you're holding. Each card is prefixed with its 0-based index:

```
HAND 0:Tempura 1:Sashimi 2:Salmon Nigiri 3:Dumpling 4:Pudding
```

To play a card, send `PLAY` with the index. For example, `PLAY 2` plays "Salmon Nigiri" from the hand above.

**Important:** You only receive `HAND` when it is time for you to act:

- After `ROUND_START` (new cards dealt)
- After `PLAYED` (turn completed, hands passed)

`HAND` is **not** sent as a periodic status update. When you see `HAND`, respond with `PLAY` (or `CHOPSTICKS`).

## Card Names

The server uses full card names in all messages:

| Card Name |
|-----------|
| Tempura |
| Sashimi |
| Dumpling |
| Maki Roll (1) |
| Maki Roll (2) |
| Maki Roll (3) |
| Egg Nigiri |
| Salmon Nigiri |
| Squid Nigiri |
| Pudding |
| Wasabi |
| Chopsticks |

## Chopsticks

If you have a Chopsticks card in your played area, you may play two cards in a single turn:

```
CHOPSTICKS 0 3
```

This plays the cards at indices 0 and 3 from your hand. The Chopsticks card returns to your hand and gets passed with it. The two indices must be different.

## Rejoin Tokens

When you join a game, the server includes a **rejoin token** in the `WELCOME` message:

```
WELCOME abc123xy 0 fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
                   ^--- rejoin token
```

If your bot disconnects, reconnect and send:

```
REJOIN fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
```

This restores your session seamlessly — other players are not notified.

## READY Command

`READY` is idempotent. If the game has already started (e.g., the last player joining triggered auto-start), `READY` simply returns `OK`. This means you can always send `READY` after joining without worrying about timing.

## Error Codes

| Code | Meaning |
|------|---------|
| E001 | Invalid command format / parsing error |
| E002 | Not your turn |
| E003 | Game has already started |
| E004 | Game has already ended |
| E005 | Player not found |
| E006 | Invalid card index |
| E007 | No chopsticks available |
| E008 | Player already submitted move this turn |
| E009 | Cannot use same card index twice |
| E010 | Name already taken |
| E011 | Game is full |

## Tournament Protocol

Tournaments are bracket-style elimination events. The protocol adds a few commands on top of the standard game flow.

### Joining a Tournament

```
TOURNEY <tournament_id> <player_name>
```

Server responds:

```
TOURNAMENT_WELCOME <tournament_id> <count>/<max> <rejoin_token>
```

As other players join, you'll see:

```
TOURNAMENT_JOINED <tournament_id> <player_name> <count>/<max>
```

### Match Assignment

When your next match is ready, the server sends:

```
TOURNAMENT_MATCH <tournament_id> <match_token> <round> <opponent_name>
```

Or, if you receive a bye (auto-advance):

```
TOURNAMENT_MATCH <tournament_id> BYE <round>
```

### Joining a Match

When you receive a `TOURNAMENT_MATCH` with a match token, join it with:

```
TJOIN <match_token>
```

After `TJOIN`, the standard game flow begins (`WELCOME`, `HAND`, `PLAY`, etc.).

### Tournament End

When the tournament finishes:

```
TOURNAMENT_COMPLETE <tournament_id> <winner_name>
```

## Example Session

A complete game from a bot's perspective:

```
>>> JOIN myGame Alice
<<< WELCOME myGame 0 fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8
>>> READY
<<< OK
<<< JOINED Bob 2/2
<<< GAME_START 2
<<< PLAYER_ORDER Alice,Bob
<<< ROUND_START 1
<<< HAND 0:Tempura 1:Sashimi 2:Salmon Nigiri 3:Dumpling 4:Pudding 5:Wasabi 6:Maki Roll (2) 7:Egg Nigiri 8:Chopsticks 9:Squid Nigiri
>>> PLAY 9
<<< OK
<<< WAITING Alice Bob
<<< PLAYED Alice:Squid Nigiri; Bob:Tempura
<<< HAND 0:Maki Roll (3) 1:Dumpling 2:Sashimi 3:Pudding 4:Maki Roll (1) 5:Egg Nigiri 6:Tempura 7:Wasabi 8:Dumpling
>>> PLAY 0
<<< OK
...
<<< ROUND_END 1 {"Alice":12,"Bob":8}
<<< ROUND_START 2
<<< HAND 0:Tempura 1:Maki Roll (2) 2:Pudding 3:Salmon Nigiri 4:Egg Nigiri 5:Sashimi 6:Dumpling 7:Wasabi 8:Chopsticks 9:Dumpling
>>> PLAY 3
<<< OK
...
<<< ROUND_END 2 {"Alice":22,"Bob":19}
<<< ROUND_START 3
<<< HAND 0:Sashimi 1:Tempura 2:Maki Roll (3) 3:Squid Nigiri 4:Pudding 5:Dumpling 6:Salmon Nigiri 7:Wasabi 8:Egg Nigiri 9:Chopsticks
>>> PLAY 3
<<< OK
...
<<< ROUND_END 3 {"Alice":35,"Bob":30}
<<< GAME_END {"Alice":41,"Bob":24} ["Alice"]
```
