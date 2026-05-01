/**
 * Dashboard Module — Updates percepts display, metrics counters,
 * points, arrow status, and move history log.
 */
const Dashboard = {

    updatePercepts(percepts) {
        if (!percepts) return;

        const items = [
            { id: 'percept-breeze', key: 'breeze', activeLabel: 'DETECTED' },
            { id: 'percept-stench', key: 'stench', activeLabel: 'DETECTED' },
            { id: 'percept-glitter', key: 'glitter', activeLabel: 'FOUND' },
            { id: 'percept-scream', key: 'scream', activeLabel: 'HEARD!' },
        ];

        items.forEach(item => {
            const el = document.getElementById(item.id);
            if (!el) return;
            const statusEl = el.querySelector('.percept-status');
            const isActive = percepts[item.key] === true;

            if (isActive) {
                el.classList.add('active');
                statusEl.textContent = item.activeLabel;
                statusEl.classList.remove('inactive');
                statusEl.classList.add('active');
            } else {
                el.classList.remove('active');
                statusEl.textContent = '—';
                statusEl.classList.remove('active');
                statusEl.classList.add('inactive');
            }
        });
    },

    updateMetrics(metrics) {
        if (!metrics) return;

        const mappings = {
            'metric-points': metrics.points,
            'metric-steps': metrics.step_count,
            'metric-inference': metrics.total_inference_steps,
            'metric-clauses': metrics.kb_clause_count,
            'metric-visited': metrics.visited_count,
            'metric-safe': metrics.safe_proven_count,
        };

        Object.entries(mappings).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                const prev = parseInt(el.textContent) || 0;
                const next = value !== undefined ? value : 0;
                if (prev !== next) {
                    el.textContent = next.toLocaleString();
                    el.style.transform = 'scale(1.15)';
                    setTimeout(() => { el.style.transform = 'scale(1)'; }, 200);
                }
            }
        });

        // Update sidebar points display
        const pointsEl = document.getElementById('points-value');
        if (pointsEl && metrics.points !== undefined) {
            pointsEl.textContent = metrics.points;
            if (metrics.points > 0) {
                pointsEl.className = 'points-value points-positive';
            } else if (metrics.points < 0) {
                pointsEl.className = 'points-value points-negative';
            } else {
                pointsEl.className = 'points-value';
            }
        }
    },

    /**
     * Update arrow UI.
     */
    updateArrow(arrowInfo, shootableCells) {
        const section = document.getElementById('arrow-section');
        const textEl = document.getElementById('arrow-text');
        const btnShoot = document.getElementById('btn-shoot');
        const hintEl = document.getElementById('arrow-hint');

        if (!section || !arrowInfo) return;

        section.style.display = 'block';

        if (arrowInfo.has_arrow) {
            textEl.textContent = '1 arrow available';
            textEl.className = '';
            // Enable shoot only when stench is present (shootable cells > 0)
            btnShoot.disabled = !shootableCells || shootableCells.length === 0;
        } else {
            if (arrowInfo.wumpus_alive === false) {
                textEl.textContent = '🎯 Wumpus killed!';
                textEl.className = 'arrow-hit';
            } else {
                textEl.textContent = '🏹 Arrow used (missed)';
                textEl.className = 'arrow-miss';
            }
            btnShoot.disabled = true;
        }
    },

    /**
     * Update the gold/return status banner.
     */
    updateStatus(goldInfo) {
        const banner = document.getElementById('status-banner');
        const iconEl = document.getElementById('status-icon');
        const textEl = document.getElementById('status-text');

        if (!banner || !goldInfo) {
            if (banner) banner.style.display = 'none';
            return;
        }

        if (goldInfo.collected && goldInfo.returning_home) {
            banner.style.display = 'flex';
            banner.className = 'glass-panel status-banner status-returning';
            iconEl.textContent = '🏠';
            textEl.textContent = 'Gold collected! Returning to start...';
        } else if (goldInfo.collected) {
            banner.style.display = 'flex';
            banner.className = 'glass-panel status-banner status-gold';
            iconEl.textContent = '💰';
            textEl.textContent = 'Gold collected! (+70 pts)';
        } else {
            banner.style.display = 'none';
        }
    },

    updateLog(history, latestMessage) {
        const logEl = document.getElementById('move-log');

        if (!history || history.length === 0) {
            logEl.innerHTML = '<div class="log-placeholder">No moves yet. Start a game!</div>';
            return;
        }

        logEl.innerHTML = '';

        const entries = [...history].reverse();
        entries.forEach(move => {
            const entry = document.createElement('div');
            entry.className = 'log-entry';

            if (move.action === 'died') {
                entry.classList.add('log-danger');
            } else if (move.action === 'backtrack' || move.action === 'return') {
                entry.classList.add('log-warning');
            } else if (move.action === 'shoot') {
                entry.classList.add(move.hit ? 'log-success' : 'log-danger');
            } else if (move.action === 'win') {
                entry.classList.add('log-win');
            } else {
                entry.classList.add('log-success');
            }

            let text = `#${move.step} `;
            if (move.action === 'move') {
                text += `→ (${move.to[0]},${move.to[1]})`;
                if (move.percepts) {
                    const active = [];
                    if (move.percepts.breeze) active.push('💨');
                    if (move.percepts.stench) active.push('☠️');
                    if (move.percepts.glitter) active.push('✨');
                    if (move.percepts.scream) active.push('😱');
                    if (active.length > 0) text += ' ' + active.join(' ');
                }
            } else if (move.action === 'backtrack') {
                text += `↩ (${move.to[0]},${move.to[1]})`;
            } else if (move.action === 'return') {
                text += `🏠 (${move.to[0]},${move.to[1]})`;
            } else if (move.action === 'shoot') {
                text += move.hit ? `🎯 HIT (${move.to[0]},${move.to[1]})` : `🏹 MISS (${move.to[0]},${move.to[1]})`;
            } else if (move.action === 'died') {
                text += `💀 ${move.message || 'Agent died'}`;
            } else if (move.action === 'win') {
                text += `🏆 WIN!`;
            }

            entry.textContent = text;
            logEl.appendChild(entry);
        });

        logEl.scrollTop = 0;
    },

    reset() {
        this.updatePercepts({ breeze: false, stench: false, glitter: false, scream: false });
        ['metric-points', 'metric-steps', 'metric-inference', 'metric-clauses',
         'metric-visited', 'metric-safe'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '0';
        });
        document.getElementById('move-log').innerHTML =
            '<div class="log-placeholder">No moves yet. Start a game!</div>';

        const banner = document.getElementById('status-banner');
        if (banner) banner.style.display = 'none';
    },
};
