# JavaScript Client

## Requirements

- Node.js 18+
- No npm dependencies — uses only the built-in `net` and `readline` modules

## Files

| File | Description |
|------|-------------|
| `sushi_go_client.js` | Full-featured client with state tracking and a priority-based strategy |

## Usage

```bash
node sushi_go_client.js <host> <port> <game_id> <player_name>
node sushi_go_client.js localhost 7878 abc123 MyBot
```

## Implementing Your Strategy

Edit the `chooseCard` method in `sushi_go_client.js`:

```javascript
chooseCard(hand) {
    /**
     * Choose which card to play.
     *
     * @param {string[]} hand - Card names (e.g., ["Tempura", "Salmon Nigiri", "Pudding"])
     * @returns {number} Index of the card to play (0-based)
     */
    // Your strategy here!
    return 0;
}
```

The default implementation uses a simple priority list. Replace it with your own logic.

## Key Patterns

### Buffered reading

The client buffers incoming TCP data and splits on newlines, since messages may arrive in chunks:

```javascript
receive() {
    return new Promise((resolve) => {
        const checkBuffer = () => {
            const idx = this.buffer.indexOf('\n');
            if (idx !== -1) {
                const msg = this.buffer.substring(0, idx);
                this.buffer = this.buffer.substring(idx + 1);
                resolve(msg);
                return true;
            }
            return false;
        };
        if (checkBuffer()) return;
        const onData = (data) => {
            this.buffer += data.toString();
            if (checkBuffer()) this.socket.removeListener('data', onData);
        };
        this.socket.on('data', onData);
    });
}
```

### HAND = your turn

Only send `PLAY` when you receive a `HAND` message. The server sends `HAND` exactly when it's time for you to act — not as a status update.

### State tracking

The client tracks played cards, chopsticks, and wasabi state via `this.state`. Use it to make smarter decisions.

## Rejoin After Disconnect

The starter client saves the rejoin token from the `WELCOME` message. If your bot crashes, you can reconnect using that token instead of joining fresh:

```javascript
const net = require('net');

const token = 'fG6miM0Ge9OnNyUTsARaSyX3ZUW8cqr8'; // saved from WELCOME
const socket = new net.Socket();

socket.connect(7878, 'localhost', () => {
    socket.write(`REJOIN ${token}\n`);
});
// server responds: "REJOINED myGame 0"
```

For a production bot, save the token to a file on join and read it back on startup:

```javascript
const fs = require('fs');

// On join — save token
fs.writeFileSync('rejoin_token.txt', rejoinToken);

// On restart — check for saved token
try {
    const token = fs.readFileSync('rejoin_token.txt', 'utf-8').trim();
    send(`REJOIN ${token}`);
} catch {
    send(`JOIN ${gameId} ${playerName}`);
}
```

See the [main README](../README.md#handling-disconnects-rejoin-tokens) for more details.

## Protocol

See [../PROTOCOL.md](../PROTOCOL.md) for the full protocol specification.
