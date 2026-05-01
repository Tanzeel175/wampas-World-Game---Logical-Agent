/**
 * Grid Renderer — Renders the Wumpus World grid using DOM elements.
 * Supports cell state visualization, arrow shooting mode, and reveal.
 */
const GridRenderer = {
    container: null,
    revealedWorld: null,
    shootMode: false,
    shootableCells: [],
    onCellShoot: null, // callback(row, col)

    init() {
        this.container = document.getElementById('game-grid');
    },

    /**
     * Enable/disable shoot mode.
     */
    setShootMode(enabled, shootableCells, callback) {
        this.shootMode = enabled;
        this.shootableCells = shootableCells || [];
        this.onCellShoot = callback || null;
    },

    /**
     * Render the full grid from game state.
     */
    render(state) {
        if (!state || !state.grid) return;

        const { rows, cols, cells } = state.grid;
        const agent = state.agent;
        const goldInfo = state.gold || {};
        this.container.style.display = 'grid';
        this.container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        document.getElementById('grid-placeholder').style.display = 'none';
        this.container.innerHTML = '';

        cells.forEach(cell => {
            const div = document.createElement('div');
            div.className = 'grid-cell';
            div.id = `cell-${cell.row}-${cell.col}`;
            div.setAttribute('data-row', cell.row);
            div.setAttribute('data-col', cell.col);

            // Coordinates label
            const coords = document.createElement('span');
            coords.className = 'cell-coords';
            coords.textContent = `${cell.row},${cell.col}`;
            div.appendChild(coords);

            const icon = document.createElement('span');
            icon.className = 'cell-icon';

            const perceptIcons = document.createElement('span');
            perceptIcons.className = 'cell-percept-icons';

            const isAgent = cell.is_agent;
            const isRevealed = this.revealedWorld !== null;

            // --- Determine cell visual state ---
            if (isAgent && agent.alive) {
                div.classList.add('cell-agent', 'cell-visited');
                if (goldInfo.collected) {
                    icon.textContent = '🤖💰'; // Agent carrying gold
                } else {
                    icon.textContent = '🤖';
                }
            } else if (isAgent && !agent.alive) {
                div.classList.add('cell-dead');
                icon.textContent = '💀';
            } else if (cell.wumpus_dead_here) {
                div.classList.add('cell-wumpus-dead');
                icon.textContent = '💀';
            } else if (isRevealed && this._isRevealedPit(cell.row, cell.col)) {
                div.classList.add('cell-pit-revealed');
                icon.textContent = '🕳️';
            } else if (isRevealed && this._isRevealedWumpus(cell.row, cell.col)) {
                if (this._isWumpusDead()) {
                    div.classList.add('cell-wumpus-dead');
                    icon.textContent = '💀';
                } else {
                    div.classList.add('cell-wumpus-revealed');
                    icon.textContent = '👹';
                }
            } else if (cell.has_gold) {
                // Unvisited cell with gold visible (only in reveal mode)
                if (isRevealed) {
                    div.classList.add('cell-gold');
                    icon.textContent = '💰';
                } else if (cell.visited) {
                    div.classList.add('cell-visited');
                    icon.textContent = '✅';
                } else if (cell.safe) {
                    div.classList.add('cell-safe-proven');
                    icon.textContent = '🟢';
                } else {
                    div.classList.add('cell-unknown');
                    icon.textContent = '❓';
                }
            } else if (cell.visited) {
                div.classList.add('cell-visited');
                icon.textContent = '✅';
            } else if (cell.safe) {
                div.classList.add('cell-safe-proven');
                icon.textContent = '🟢';
            } else {
                div.classList.add('cell-unknown');
                icon.textContent = '❓';
            }

            // Percept indicators
            if (cell.visited && cell.percepts) {
                if (cell.percepts.breeze) {
                    div.classList.add('cell-breeze');
                    perceptIcons.innerHTML += '<span title="Breeze">💨</span>';
                }
                if (cell.percepts.stench) {
                    div.classList.add('cell-stench');
                    perceptIcons.innerHTML += '<span title="Stench">☠️</span>';
                }
                if (cell.percepts.glitter) {
                    perceptIcons.innerHTML += '<span title="Glitter">✨</span>';
                }
                if (cell.percepts.scream) {
                    perceptIcons.innerHTML += '<span title="Scream">😱</span>';
                }
            }

            // Shoot mode: highlight shootable cells
            if (this.shootMode) {
                const isShootable = this.shootableCells.some(
                    sc => sc[0] === cell.row && sc[1] === cell.col
                );
                if (isShootable) {
                    div.classList.add('cell-shootable');
                    div.title = `Click to shoot arrow at (${cell.row},${cell.col})`;
                    div.style.cursor = 'crosshair';
                    div.addEventListener('click', () => {
                        if (this.onCellShoot) {
                            this.onCellShoot(cell.row, cell.col);
                        }
                    });
                }
            }

            div.appendChild(icon);
            div.appendChild(perceptIcons);
            div.style.animation = `cellReveal 0.3s ease ${(cell.row * cols + cell.col) * 0.02}s both`;
            this.container.appendChild(div);
        });
    },

    setRevealedWorld(worldData) {
        this.revealedWorld = worldData;
    },

    showGameOver(result, message, points) {
        const overlay = document.getElementById('game-over-overlay');
        const iconEl = document.getElementById('game-over-icon');
        const titleEl = document.getElementById('game-over-title');
        const msgEl = document.getElementById('game-over-message');
        const scoreEl = document.getElementById('game-over-score');

        const configs = {
            win:          { icon: '🏆', title: 'YOU WIN!' },
            explored:     { icon: '🗺️', title: 'Exploration Complete' },
            dead_pit:     { icon: '🕳️', title: 'Fell Into a Pit!' },
            dead_wumpus:  { icon: '👹', title: 'Eaten by the Wumpus!' },
            stuck:        { icon: '🚧', title: 'Agent Stuck!' },
        };

        const cfg = configs[result] || { icon: '🏁', title: 'Game Over' };
        iconEl.textContent = cfg.icon;
        titleEl.textContent = cfg.title;
        msgEl.textContent = message || '';

        // Show final score prominently
        if (points !== undefined) {
            scoreEl.innerHTML = `<div class="final-score">Final Score: <strong>${points}</strong> pts</div>`;
            scoreEl.style.display = 'block';
        } else {
            scoreEl.style.display = 'none';
        }

        overlay.style.display = 'flex';
    },

    hideGameOver() {
        document.getElementById('game-over-overlay').style.display = 'none';
    },

    _isRevealedPit(r, c) {
        if (!this.revealedWorld) return false;
        return this.revealedWorld.pits.some(p => p[0] === r && p[1] === c);
    },

    _isRevealedWumpus(r, c) {
        if (!this.revealedWorld) return false;
        const w = this.revealedWorld.wumpus;
        return w && w[0] === r && w[1] === c;
    },

    _isWumpusDead() {
        if (!this.revealedWorld) return false;
        return this.revealedWorld.wumpus_alive === false;
    },

    _isRevealedGold(r, c) {
        if (!this.revealedWorld) return false;
        const g = this.revealedWorld.gold;
        return g && g[0] === r && g[1] === c && !this.revealedWorld.gold_collected;
    },
};
