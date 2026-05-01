"""
Flask API Server for Wumpus World Logic Agent
==============================================
Provides REST endpoints for game management, agent control,
arrow shooting, and inference-driven pathfinding.
"""

import os
import sys
from collections import deque

# Ensure sibling modules are importable (needed for Vercel serverless)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from game import WumpusWorld
from knowledge_base import KnowledgeBase
from resolution import is_cell_safe

# ---------------------------------------------------------------------------
# Flask App Setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)
CORS(app)

# Serve frontend static files
FRONTEND_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
)

# ---------------------------------------------------------------------------
# Global Game State
# ---------------------------------------------------------------------------
game_state = {
    "world": None,
    "kb": None,
    "visited": set(),
    "safe_proven": set(),
    "unsafe_proven": set(),
    "frontier": set(),
    "move_history": [],
    "total_inference_steps": 0,
    "current_percepts": {},
    "step_count": 0,
    "returning_home": False,  # True when agent has gold and is heading back
    "return_path": [],  # BFS path back to (0,0)
}


def reset_game(rows, cols, seed=None):
    """Initialize a new game with the given grid dimensions."""
    world = WumpusWorld(rows, cols, seed=seed)
    kb = KnowledgeBase()

    game_state["world"] = world
    game_state["kb"] = kb
    game_state["visited"] = set()
    game_state["safe_proven"] = set()
    game_state["unsafe_proven"] = set()
    game_state["frontier"] = set()
    game_state["move_history"] = []
    game_state["total_inference_steps"] = 0
    game_state["current_percepts"] = {}
    game_state["step_count"] = 0
    game_state["returning_home"] = False
    game_state["return_path"] = []

    # Add the single-wumpus constraint
    kb.tell_single_wumpus_constraint(rows, cols)

    # Visit the starting cell
    _visit_cell(0, 0)


def _visit_cell(r, c):
    """Process visiting a cell: update KB with percepts, run inference."""
    world = game_state["world"]
    kb = game_state["kb"]

    game_state["visited"].add((r, c))
    game_state["frontier"].discard((r, c))

    kb.tell_visited_safe(r, c)

    percepts = world.get_percepts(r, c)
    game_state["current_percepts"] = percepts

    adjacents = world.get_adjacent(r, c)

    kb.tell_breeze(r, c, percepts["breeze"], adjacents)
    kb.tell_stench(r, c, percepts["stench"], adjacents)

    for ar, ac in adjacents:
        if (ar, ac) not in game_state["visited"]:
            game_state["frontier"].add((ar, ac))

    _infer_frontier()

    # If gold was just collected, plan return path
    if world.gold_collected and not game_state["returning_home"]:
        game_state["returning_home"] = True
        game_state["return_path"] = _find_return_path()


def _infer_frontier():
    """Run resolution refutation on all frontier cells to classify them."""
    kb = game_state["kb"]
    inference_steps_this_round = 0

    for (r, c) in list(game_state["frontier"]):
        if (r, c) in game_state["safe_proven"]:
            continue

        result = is_cell_safe(kb, r, c)
        inference_steps_this_round += result["total_steps"]

        if result["safe"]:
            game_state["safe_proven"].add((r, c))

    game_state["total_inference_steps"] += inference_steps_this_round
    return inference_steps_this_round


def _find_return_path():
    """BFS from agent position to (0,0) through visited cells."""
    world = game_state["world"]
    agent_pos = world.agent_pos
    visited = game_state["visited"]
    target = (0, 0)

    if agent_pos == target:
        return []

    queue = deque([(agent_pos, [agent_pos])])
    seen = {agent_pos}

    while queue:
        pos, path = queue.popleft()
        for neighbor in world.get_adjacent(*pos):
            if neighbor == target:
                return path[1:] + [target]  # Exclude starting position
            if neighbor in visited and neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return []  # No path found


def _choose_next_cell():
    """
    Choose the next cell for the agent to move to.
    If returning home with gold, follow return path.
    Otherwise, explore safe frontier cells.
    """
    world = game_state["world"]

    # If returning home with gold, follow the return path
    if game_state["returning_home"] and game_state["return_path"]:
        return game_state["return_path"][0]

    # Prefer safe frontier cells
    safe_frontier = [
        (r, c) for (r, c) in game_state["frontier"]
        if (r, c) in game_state["safe_proven"]
        and (r, c) not in game_state["visited"]
    ]

    if safe_frontier:
        agent_r, agent_c = world.agent_pos
        safe_frontier.sort(key=lambda cell: abs(cell[0] - agent_r) + abs(cell[1] - agent_c))

        adj = set(world.get_adjacent(agent_r, agent_c))
        adjacent_safe = [c for c in safe_frontier if c in adj]

        if adjacent_safe:
            return adjacent_safe[0]

        return _find_path_to_safe_cell(safe_frontier)

    return None


def _find_path_to_safe_cell(target_cells):
    """BFS from agent through visited cells to find path toward target cells."""
    world = game_state["world"]
    agent_pos = world.agent_pos
    visited = game_state["visited"]
    target_set = set(target_cells)

    queue = deque([(agent_pos, [agent_pos])])
    seen = {agent_pos}

    while queue:
        pos, path = queue.popleft()
        adj = world.get_adjacent(*pos)

        for neighbor in adj:
            if neighbor in target_set:
                if len(path) > 1:
                    return path[1]
                else:
                    return neighbor

            if neighbor in visited and neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


def _build_response(message="", inference_steps_round=0, trace=None):
    """Build the JSON response with full game state."""
    world = game_state["world"]
    if world is None:
        return {"error": "No game in progress. Start a new game first."}

    cells = []
    for r in range(world.rows):
        for c in range(world.cols):
            cell = {
                "row": r,
                "col": c,
                "visited": (r, c) in game_state["visited"],
                "safe": (r, c) in game_state["safe_proven"],
                "unsafe": (r, c) in game_state["unsafe_proven"],
                "frontier": (r, c) in game_state["frontier"],
                "is_agent": (r, c) == world.agent_pos,
                "percepts": None,
                "has_gold": (r, c) == world.gold and not world.gold_collected,
                "wumpus_dead_here": (r, c) == world.wumpus_killed_at,
            }
            if (r, c) in game_state["visited"]:
                cell["percepts"] = world.get_percepts(r, c)
            cells.append(cell)

    # Determine which cells are shootable (adjacent + agent has arrow + stench present)
    shootable_cells = []
    if world.has_arrow and not world.game_over:
        current_percepts = game_state.get("current_percepts", {})
        if current_percepts.get("stench", False):
            adj = world.get_adjacent(*world.agent_pos)
            shootable_cells = [[ar, ac] for ar, ac in adj]

    return {
        "grid": {
            "rows": world.rows,
            "cols": world.cols,
            "cells": cells,
        },
        "agent": {
            "row": world.agent_pos[0],
            "col": world.agent_pos[1],
            "alive": world.agent_alive,
        },
        "current_percepts": game_state["current_percepts"],
        "metrics": {
            "total_inference_steps": game_state["total_inference_steps"],
            "inference_steps_this_round": inference_steps_round,
            "kb_clause_count": game_state["kb"].get_clause_count() if game_state["kb"] else 0,
            "visited_count": len(game_state["visited"]),
            "safe_proven_count": len(game_state["safe_proven"]),
            "frontier_count": len(game_state["frontier"]),
            "step_count": game_state["step_count"],
            "points": world.points,
        },
        "arrow": {
            "has_arrow": world.has_arrow,
            "arrow_used": world.arrow_used,
            "wumpus_alive": world.wumpus_alive,
        },
        "gold": {
            "collected": world.gold_collected,
            "returning_home": game_state["returning_home"],
        },
        "shootable_cells": shootable_cells,
        "move_history": game_state["move_history"][-30:],
        "game_over": world.game_over,
        "game_result": world.game_result,
        "message": message,
        "trace": trace or [],
    }


# ---------------------------------------------------------------------------
# Static File Serving
# ---------------------------------------------------------------------------
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/new-game", methods=["POST"])
def new_game():
    """Start a new game with specified grid dimensions."""
    data = request.get_json() or {}
    rows = data.get("rows", 4)
    cols = data.get("cols", 4)
    seed = data.get("seed", None)

    rows = max(3, min(10, int(rows)))
    cols = max(3, min(10, int(cols)))

    reset_game(rows, cols, seed=seed)
    return jsonify(_build_response(
        message=f"🎮 New {rows}×{cols} game started! Agent at (0,0). Find the gold and return home! Score: 0 pts.",
    ))


@app.route("/api/step", methods=["POST"])
def step():
    """Agent takes one intelligent step: infer → choose → move."""
    world = game_state["world"]
    if world is None:
        return jsonify({"error": "No game. Start a new game first."}), 400

    if world.game_over:
        return jsonify(_build_response(
            message=f"Game is over ({world.game_result}). Final score: {world.points} pts. Start a new game."
        ))

    next_cell = _choose_next_cell()

    if next_cell is None:
        unvisited_safe = game_state["safe_proven"] - game_state["visited"]
        if not unvisited_safe:
            world.game_over = True
            world.game_result = "explored"
            msg = (f"Agent explored all reachable safe cells without finding gold. "
                   f"Final score: {world.points} pts.")
            if world.gold_collected:
                msg = (f"Agent collected gold but couldn't find path home. "
                       f"Final score: {world.points} pts.")
            return jsonify(_build_response(message=msg))
        else:
            world.game_over = True
            world.game_result = "stuck"
            return jsonify(_build_response(
                message=f"Agent is stuck. No safe moves available. Final score: {world.points} pts.",
            ))

    r, c = next_cell

    # If returning home, advance along the return path
    if game_state["returning_home"] and game_state["return_path"]:
        if (r, c) == game_state["return_path"][0]:
            game_state["return_path"].pop(0)

    # Check if this is a backtrack/revisit move
    if (r, c) in game_state["visited"]:
        world.agent_pos = (r, c)
        world.points -= 1  # Still costs a point
        game_state["step_count"] += 1

        # Check if returned home with gold
        if world.gold_collected and (r, c) == (0, 0):
            world.game_over = True
            world.game_result = "win"
            game_state["move_history"].append({
                "step": game_state["step_count"],
                "action": "win",
                "to": [r, c],
                "message": f"🎉 Returned home with gold!",
            })
            return jsonify(_build_response(
                message=f"🎉 YOU WIN! Agent returned home with the gold! "
                        f"Final score: {world.points} pts in {game_state['step_count']} moves!",
            ))

        action_label = "return" if game_state["returning_home"] else "backtrack"
        game_state["move_history"].append({
            "step": game_state["step_count"],
            "action": action_label,
            "to": [r, c],
            "message": f"{'🏠 Returning home' if game_state['returning_home'] else '↩ Backtracking'} through ({r},{c})",
        })
        return jsonify(_build_response(
            message=f"{'🏠 Returning home via' if game_state['returning_home'] else '↩ Backtracking to'} ({r},{c}). Score: {world.points} pts.",
        ))

    # Move to new unvisited cell
    result = world.move_agent(r, c)
    game_state["step_count"] += 1

    if not result["alive"]:
        game_state["move_history"].append({
            "step": game_state["step_count"],
            "action": "died",
            "to": [r, c],
            "message": result["message"],
        })
        return jsonify(_build_response(message=result["message"]))

    # Check if game won (move_agent handles win condition)
    if world.game_over and world.game_result == "win":
        game_state["move_history"].append({
            "step": game_state["step_count"],
            "action": "win",
            "to": [r, c],
            "message": result["message"],
        })
        return jsonify(_build_response(message=result["message"]))

    # Visit the new cell (update KB, run inference)
    _visit_cell(r, c)
    inference_steps = game_state["total_inference_steps"]

    game_state["move_history"].append({
        "step": game_state["step_count"],
        "action": "move",
        "to": [r, c],
        "percepts": game_state["current_percepts"],
        "message": result["message"],
    })

    return jsonify(_build_response(
        message=result["message"],
        inference_steps_round=inference_steps,
    ))


@app.route("/api/shoot", methods=["POST"])
def shoot_arrow():
    """Shoot arrow at a target adjacent cell."""
    world = game_state["world"]
    if world is None:
        return jsonify({"error": "No game in progress."}), 400

    if world.game_over:
        return jsonify(_build_response(message="Game is already over.")), 400

    data = request.get_json() or {}
    target_r = data.get("row")
    target_c = data.get("col")

    if target_r is None or target_c is None:
        return jsonify({"error": "Must specify target row and col."}), 400

    target_r = int(target_r)
    target_c = int(target_c)

    result = world.shoot_arrow(target_r, target_c)

    if not result["success"]:
        return jsonify(_build_response(message=result["message"]))

    game_state["step_count"] += 1
    game_state["move_history"].append({
        "step": game_state["step_count"],
        "action": "shoot",
        "to": [target_r, target_c],
        "hit": result.get("hit", False),
        "message": result["message"],
    })

    # If wumpus was killed, update KB to mark that cell as safe from wumpus
    if result.get("hit", False):
        kb = game_state["kb"]
        from knowledge_base import make_lit, wumpus_symbol
        # Tell KB the wumpus is dead at this location
        kb.add_clause(frozenset({make_lit(wumpus_symbol(target_r, target_c), False)}))
        # Re-run inference since stench patterns may have changed
        _infer_frontier()

    return jsonify(_build_response(message=result["message"]))


@app.route("/api/auto-solve", methods=["POST"])
def auto_solve():
    """Run the agent automatically until game over or fully explored."""
    world = game_state["world"]
    if world is None:
        return jsonify({"error": "No game. Start a new game first."}), 400

    max_auto_steps = 300
    steps_taken = 0
    history = []

    while not world.game_over and steps_taken < max_auto_steps:
        next_cell = _choose_next_cell()

        if next_cell is None:
            unvisited_safe = game_state["safe_proven"] - game_state["visited"]
            if not unvisited_safe:
                world.game_over = True
                world.game_result = "explored"
                history.append(f"All safe cells explored. Score: {world.points}")
            else:
                world.game_over = True
                world.game_result = "stuck"
                history.append(f"Agent stuck. Score: {world.points}")
            break

        r, c = next_cell
        steps_taken += 1
        game_state["step_count"] += 1

        # Advance return path
        if game_state["returning_home"] and game_state["return_path"]:
            if (r, c) == game_state["return_path"][0]:
                game_state["return_path"].pop(0)

        if (r, c) in game_state["visited"]:
            world.agent_pos = (r, c)
            world.points -= 1

            # Check win
            if world.gold_collected and (r, c) == (0, 0):
                world.game_over = True
                world.game_result = "win"
                history.append(f"🎉 Returned home with gold! Score: {world.points}")
                game_state["move_history"].append({
                    "step": game_state["step_count"],
                    "action": "win",
                    "to": [r, c],
                })
                break

            action = "return" if game_state["returning_home"] else "backtrack"
            history.append(f"Step {game_state['step_count']}: {action} to ({r},{c})")
            game_state["move_history"].append({
                "step": game_state["step_count"],
                "action": action,
                "to": [r, c],
            })
            continue

        result = world.move_agent(r, c)

        if not result["alive"]:
            history.append(f"Step {game_state['step_count']}: {result['message']}")
            game_state["move_history"].append({
                "step": game_state["step_count"],
                "action": "died",
                "to": [r, c],
                "message": result["message"],
            })
            break

        if world.game_over and world.game_result == "win":
            history.append(f"Step {game_state['step_count']}: {result['message']}")
            game_state["move_history"].append({
                "step": game_state["step_count"],
                "action": "win",
                "to": [r, c],
                "message": result["message"],
            })
            break

        _visit_cell(r, c)
        history.append(
            f"Step {game_state['step_count']}: Moved to ({r},{c}) "
            f"- Percepts: {game_state['current_percepts']}"
        )
        game_state["move_history"].append({
            "step": game_state["step_count"],
            "action": "move",
            "to": [r, c],
            "percepts": game_state["current_percepts"],
        })

    final_msg = f"Auto-solve completed in {steps_taken} moves. "
    if world.game_result == "win":
        final_msg += f"🎉 YOU WIN! Final score: {world.points} pts!"
    elif world.game_result in ("dead_pit", "dead_wumpus"):
        final_msg += f"💀 Agent died. Final score: {world.points} pts."
    else:
        final_msg += f"Final score: {world.points} pts."

    return jsonify(_build_response(message=final_msg))


@app.route("/api/state", methods=["GET"])
def get_state():
    """Return current game state."""
    return jsonify(_build_response())


@app.route("/api/reveal", methods=["GET"])
def reveal():
    """Reveal the full world state (for debugging / post-game)."""
    world = game_state["world"]
    if world is None:
        return jsonify({"error": "No game in progress."}), 400
    return jsonify(world.get_full_state())


@app.route("/api/kb-log", methods=["GET"])
def kb_log():
    """Return the KB clause log for display."""
    kb = game_state["kb"]
    if kb is None:
        return jsonify({"clauses": []})
    return jsonify({"clauses": kb.get_clause_log()[-50:]})


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Wumpus World Logic Agent — Flask Server")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 60)
    app.run(debug=True, port=5000)
