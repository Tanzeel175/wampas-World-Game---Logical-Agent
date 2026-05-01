/**
 * API Module — Fetch wrappers for the Flask backend.
 */
const API_BASE = window.location.origin + '/api';

const WumpusAPI = {
    async newGame(rows, cols) {
        const res = await fetch(`${API_BASE}/new-game`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows, cols }),
        });
        return res.json();
    },

    async step() {
        const res = await fetch(`${API_BASE}/step`, { method: 'POST' });
        return res.json();
    },

    async autoSolve() {
        const res = await fetch(`${API_BASE}/auto-solve`, { method: 'POST' });
        return res.json();
    },

    /**
     * Shoot arrow at target cell.
     * @param {number} row
     * @param {number} col
     */
    async shoot(row, col) {
        const res = await fetch(`${API_BASE}/shoot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row, col }),
        });
        return res.json();
    },

    async getState() {
        const res = await fetch(`${API_BASE}/state`);
        return res.json();
    },

    async reveal() {
        const res = await fetch(`${API_BASE}/reveal`);
        return res.json();
    },

    async getKBLog() {
        const res = await fetch(`${API_BASE}/kb-log`);
        return res.json();
    },
};
