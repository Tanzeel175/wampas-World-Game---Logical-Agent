/**
 * App Controller — Main application logic.
 * Handles UI events, coordinates API calls, manages shoot mode, and updates the view.
 */
(function () {
    'use strict';

    // ---- DOM References ----
    const inputRows = document.getElementById('input-rows');
    const inputCols = document.getElementById('input-cols');
    const btnNewGame = document.getElementById('btn-new-game');
    const btnStep = document.getElementById('btn-step');
    const btnAutoSolve = document.getElementById('btn-auto-solve');
    const btnReveal = document.getElementById('btn-reveal');
    const btnShoot = document.getElementById('btn-shoot');

    let isProcessing = false;
    let shootModeActive = false;
    let currentState = null;

    // ---- Initialize ----
    GridRenderer.init();

    // ---- Event Handlers ----
    btnNewGame.addEventListener('click', handleNewGame);
    btnStep.addEventListener('click', handleStep);
    btnAutoSolve.addEventListener('click', handleAutoSolve);
    btnReveal.addEventListener('click', handleReveal);
    btnShoot.addEventListener('click', toggleShootMode);

    async function handleNewGame() {
        if (isProcessing) return;
        isProcessing = true;
        setButtonsLoading(true);

        const rows = parseInt(inputRows.value) || 4;
        const cols = parseInt(inputCols.value) || 4;

        try {
            const state = await WumpusAPI.newGame(rows, cols);
            if (state.error) {
                alert(state.error);
                return;
            }

            currentState = state;
            shootModeActive = false;
            GridRenderer.setRevealedWorld(null);
            GridRenderer.setShootMode(false, [], null);
            GridRenderer.hideGameOver();
            updateUI(state);
            enableGameButtons(true);

            // Show points and arrow sections
            document.getElementById('points-section').style.display = 'block';
        } catch (err) {
            console.error('Error starting new game:', err);
            alert('Failed to connect to the server. Is the Flask backend running?');
        } finally {
            isProcessing = false;
            setButtonsLoading(false);
        }
    }

    async function handleStep() {
        if (isProcessing || shootModeActive) return;
        isProcessing = true;
        btnStep.disabled = true;

        try {
            const state = await WumpusAPI.step();
            if (state.error) {
                alert(state.error);
                return;
            }
            currentState = state;
            updateUI(state);

            if (state.game_over) {
                handleGameOver(state);
            }
        } catch (err) {
            console.error('Error taking step:', err);
        } finally {
            isProcessing = false;
            if (!currentState || !currentState.game_over) {
                btnStep.disabled = false;
            }
        }
    }

    async function handleAutoSolve() {
        if (isProcessing || shootModeActive) return;
        isProcessing = true;
        enableGameButtons(false);
        btnAutoSolve.textContent = '⏳ Solving...';

        try {
            const state = await WumpusAPI.autoSolve();
            if (state.error) {
                alert(state.error);
                return;
            }
            currentState = state;
            updateUI(state);

            if (state.game_over) {
                handleGameOver(state);
            }
        } catch (err) {
            console.error('Error auto-solving:', err);
        } finally {
            isProcessing = false;
            btnAutoSolve.innerHTML = '<span class="btn-icon">🚀</span> Auto Solve';
        }
    }

    async function handleReveal() {
        try {
            const world = await WumpusAPI.reveal();
            GridRenderer.setRevealedWorld(world);
            const state = await WumpusAPI.getState();
            currentState = state;
            GridRenderer.render(state);
        } catch (err) {
            console.error('Error revealing world:', err);
        }
    }

    function toggleShootMode() {
        if (!currentState || currentState.game_over) return;

        shootModeActive = !shootModeActive;
        const hintEl = document.getElementById('arrow-hint');

        if (shootModeActive) {
            btnShoot.classList.add('btn-shoot-active');
            btnShoot.innerHTML = '<span class="btn-icon">❌</span> Cancel Shoot';
            hintEl.style.display = 'block';

            // Enable shoot mode on grid
            GridRenderer.setShootMode(true, currentState.shootable_cells, handleShootCell);
            GridRenderer.render(currentState);
        } else {
            cancelShootMode();
        }
    }

    function cancelShootMode() {
        shootModeActive = false;
        const hintEl = document.getElementById('arrow-hint');
        btnShoot.classList.remove('btn-shoot-active');
        btnShoot.innerHTML = '<span class="btn-icon">🎯</span> Shoot Arrow';
        hintEl.style.display = 'none';

        GridRenderer.setShootMode(false, [], null);
        if (currentState) {
            GridRenderer.render(currentState);
        }
    }

    async function handleShootCell(row, col) {
        if (isProcessing) return;
        isProcessing = true;

        try {
            const state = await WumpusAPI.shoot(row, col);
            if (state.error) {
                alert(state.error);
                return;
            }
            currentState = state;
            cancelShootMode();
            updateUI(state);

            if (state.game_over) {
                handleGameOver(state);
            }
        } catch (err) {
            console.error('Error shooting arrow:', err);
        } finally {
            isProcessing = false;
        }
    }

    async function handleGameOver(state) {
        enableGameButtons(false);
        const world = await WumpusAPI.reveal();
        GridRenderer.setRevealedWorld(world);
        GridRenderer.render(state);

        const points = state.metrics ? state.metrics.points : 0;
        GridRenderer.showGameOver(state.game_result, state.message, points);
    }

    // ---- UI Update Helpers ----
    function updateUI(state) {
        GridRenderer.render(state);
        Dashboard.updatePercepts(state.current_percepts);
        Dashboard.updateMetrics(state.metrics);
        Dashboard.updateArrow(state.arrow, state.shootable_cells);
        Dashboard.updateStatus(state.gold);
        Dashboard.updateLog(state.move_history, state.message);
    }

    function enableGameButtons(enabled) {
        btnStep.disabled = !enabled;
        btnAutoSolve.disabled = !enabled;
        btnReveal.disabled = !enabled;
    }

    function setButtonsLoading(loading) {
        if (loading) {
            btnNewGame.disabled = true;
            btnNewGame.textContent = '⏳ Creating...';
        } else {
            btnNewGame.disabled = false;
            btnNewGame.innerHTML = '<span class="btn-icon">🎮</span> New Game';
        }
    }
})();
