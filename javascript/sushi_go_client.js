#!/usr/bin/env node
/**
 * Sushi Go Client - JavaScript/Node.js Starter Kit
 *
 * This client connects to the Sushi Go server and plays using a simple strategy.
 * Modify the `chooseCard` method to implement your own AI!
 *
 * Usage:
 *     node sushi_go_client.js <server_host> <server_port> <game_id> <player_name>
 *
 * Example:
 *     node sushi_go_client.js localhost 7878 abc123 MyBot
 */

const net = require('net');
const readline = require('readline');

// Card names used by the protocol (now using full names instead of codes)
const CARD_NAMES = {
    'Tempura': 'Tempura',
    'Sashimi': 'Sashimi',
    'Dumpling': 'Dumpling',
    'Maki Roll (1)': 'Maki Roll (1)',
    'Maki Roll (2)': 'Maki Roll (2)',
    'Maki Roll (3)': 'Maki Roll (3)',
    'Egg Nigiri': 'Egg Nigiri',
    'Salmon Nigiri': 'Salmon Nigiri',
    'Squid Nigiri': 'Squid Nigiri',
    'Pudding': 'Pudding',
    'Wasabi': 'Wasabi',
    'Chopsticks': 'Chopsticks',
};

class SushiGoClient {
    constructor(host, port) {
        this.host = host;
        this.port = port;
        this.socket = null;
        this.state = {
            gameId: null,
            playerId: null,
            rejoinToken: null,
            hand: [],
            round: 1,
            turn: 1,
            playerOrder: [],
            playedCards: [],
            hasChopsticks: false,
            hasUnusedWasabi: false,
            puddings: 0,
        };
        this.buffer = '';
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.socket = new net.Socket();

            this.socket.connect(this.port, this.host, () => {
                console.log(`Connected to ${this.host}:${this.port}`);
                resolve();
            });

            this.socket.on('error', (err) => {
                reject(err);
            });

            this.socket.on('close', () => {
                console.log('Connection closed');
            });
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.destroy();
            this.socket = null;
        }
    }

    send(command) {
        const message = command + '\n';
        this.socket.write(message);
        console.log(`>>> ${command}`);
    }

    receive() {
        return new Promise((resolve) => {
            const checkBuffer = () => {
                const newlineIndex = this.buffer.indexOf('\n');
                if (newlineIndex !== -1) {
                    const message = this.buffer.substring(0, newlineIndex);
                    this.buffer = this.buffer.substring(newlineIndex + 1);
                    console.log(`<<< ${message}`);
                    resolve(message);
                    return true;
                }
                return false;
            };

            if (checkBuffer()) return;

            const onData = (data) => {
                this.buffer += data.toString();
                if (checkBuffer()) {
                    this.socket.removeListener('data', onData);
                }
            };

            this.socket.on('data', onData);
        });
    }

    async joinGame(gameId, playerName) {
        this.send(`JOIN ${gameId} ${playerName}`);
        const response = await this.receiveUntil((line) =>
            line.startsWith('WELCOME') || line.startsWith('ERROR')
        );

        if (response.startsWith('WELCOME')) {
            const parts = response.split(' ');
            this.state.gameId = parts[1];
            this.state.playerId = parseInt(parts[2]);
            this.state.rejoinToken = parts[3] || null;
            console.log(`Rejoin token: ${this.state.rejoinToken}`);
            return true;
        } else if (response.startsWith('ERROR')) {
            console.log(`Failed to join: ${response}`);
            return false;
        }
        return false;
    }

    async receiveUntil(predicate) {
        while (true) {
            const message = await this.receive();
            const trimmed = message.trim();

            // The server sends a multi-line greeting banner on connect.
            // Ignore blank/banner lines until we hit a protocol message.
            if (!trimmed) {
                continue;
            }
            if (predicate(trimmed)) {
                return trimmed;
            }
        }
    }

    async signalReady() {
        this.send('READY');
        return await this.receive();
    }

    async playCard(cardIndex) {
        this.send(`PLAY ${cardIndex}`);
        return await this.receive();
    }

    async playChopsticks(index1, index2) {
        this.send(`CHOPSTICKS ${index1} ${index2}`);
        return await this.receive();
    }

    parseHand(message) {
        if (message.startsWith('HAND')) {
            const payload = message.slice('HAND '.length);
            const cards = [];
            const cardPattern = /(\d+):(.*?)(?=\s\d+:|$)/g;
            let match;

            // Parse indexed cards while preserving multi-word card names.
            while ((match = cardPattern.exec(payload)) !== null) {
                const cardName = match[2].trim();
                cards.push(cardName);
            }

            this.state.hand = cards;
            // Update chopsticks/wasabi tracking
            this.state.hasChopsticks = this.state.playedCards.includes('Chopsticks');
            this.state.hasUnusedWasabi = this.state.playedCards.includes('Wasabi') &&
                !this.state.playedCards.some(c => ['Egg Nigiri', 'Salmon Nigiri', 'Squid Nigiri'].includes(c));
        }
    }

    /**
     * Choose which card to play.
     *
     * This is where you implement your AI strategy!
     * The default implementation uses a simple priority-based approach.
     *
     * @param {string[]} hand - List of card codes in your current hand
     * @returns {number} Index of the card to play (0-based)
     */
    chooseCard(hand) {
        // Simple priority-based strategy
        const priority = [
            'Squid Nigiri',     // 3 points, or 9 with wasabi
            'Salmon Nigiri',    // 2 points, or 6 with wasabi
            'Maki Roll (3)',    // 3 maki rolls
            'Maki Roll (2)',    // 2 maki rolls
            'Tempura',          // 5 points per pair
            'Sashimi',          // 10 points per set of 3
            'Dumpling',         // Increasing value
            'Wasabi',           // Triples next nigiri
            'Egg Nigiri',       // 1 point, or 3 with wasabi
            'Pudding',          // End game scoring
            'Maki Roll (1)',    // 1 maki roll
            'Chopsticks',       // Play 2 cards next turn
        ];

        // If we have wasabi, prioritize nigiri
        if (this.state.hasUnusedWasabi) {
            for (const nigiri of ['Squid Nigiri', 'Salmon Nigiri', 'Egg Nigiri']) {
                const index = hand.indexOf(nigiri);
                if (index !== -1) return index;
            }
        }

        // Otherwise use priority list
        for (const card of priority) {
            const index = hand.indexOf(card);
            if (index !== -1) return index;
        }

        // Fallback: random
        return Math.floor(Math.random() * hand.length);
    }

    handleMessage(message) {
        if (message.startsWith('PLAYER_ORDER ')) {
            const payload = message.slice('PLAYER_ORDER '.length);
            this.state.playerOrder = payload ? payload.split(',') : [];
        } else if (message.startsWith('HAND')) {
            this.parseHand(message);
        } else if (message.startsWith('ROUND_START')) {
            const parts = message.split(' ');
            this.state.round = parseInt(parts[1]);
            this.state.turn = 1;
            this.state.playedCards = [];
        } else if (message.startsWith('PLAYED')) {
            // Cards were revealed, next turn
            this.state.turn += 1;
        } else if (message.startsWith('ROUND_END')) {
            // Round ended
            this.state.playedCards = [];
        } else if (message.startsWith('GAME_END')) {
            console.log('Game over!');
            return false;
        } else if (message.startsWith('WAITING')) {
            // Our move was accepted, waiting for others
        }
        return true;
    }

    async playTurn() {
        if (!this.state.hand || this.state.hand.length === 0) {
            return;
        }

        const cardIndex = this.chooseCard(this.state.hand);
        const playedCard = this.state.hand[cardIndex];

        const response = await this.playCard(cardIndex);

        if (response.startsWith('OK')) {
            this.state.playedCards.push(playedCard);
        }
    }

    async run(gameId, playerName) {
        try {
            await this.connect();

            if (!await this.joinGame(gameId, playerName)) {
                return;
            }

            // Signal ready
            await this.signalReady();

            // Main game loop
            let running = true;
            while (running) {
                const message = await this.receive();
                running = this.handleMessage(message);

                // If we received our hand, play a card
                if (message.startsWith('HAND') && this.state.hand.length > 0) {
                    await this.playTurn();
                }
            }
        } catch (err) {
            console.error(`Error: ${err.message}`);
        } finally {
            this.disconnect();
        }
    }
}

// Main entry point
function main() {
    const args = process.argv.slice(2);

    if (args.length !== 4) {
        console.log('Usage: node sushi_go_client.js <host> <port> <game_id> <player_name>');
        console.log('Example: node sushi_go_client.js localhost 7878 abc123 MyBot');
        process.exit(1);
    }

    const [host, port, gameId, playerName] = args;
    const client = new SushiGoClient(host, parseInt(port));
    client.run(gameId, playerName);
}

main();
