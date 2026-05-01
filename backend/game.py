"""
Wumpus World Game Engine
========================
Manages the grid environment, hazard placement, percept generation,
agent state, points system, and arrow mechanics.

Points System:
  - Each move costs 1 point
  - Collecting gold grants +70 points
  - Shooting arrow costs -20 points
  - Killing Wumpus grants +10 points
  - Dying: 0 points (game ends)
  - Win: return to (0,0) with gold
"""

import random


class WumpusWorld:
    """
    Represents a Wumpus World grid environment with full game mechanics.
    """

    def __init__(self, rows=4, cols=4, pit_prob=0.15, seed=None):
        if seed is not None:
            random.seed(seed)

        self.rows = rows
        self.cols = cols
        self.pits = set()
        self.wumpus = None
        self.gold = None
        self.agent_pos = (0, 0)
        self.agent_alive = True
        self.wumpus_alive = True
        self.gold_collected = False
        self.game_over = False
        self.game_result = None  # 'win', 'dead_pit', 'dead_wumpus', 'stuck', 'explored'

        # Points system
        self.points = 0

        # Arrow system: agent has exactly 1 arrow per game
        self.has_arrow = True
        self.arrow_used = False
        self.wumpus_killed_at = None  # cell where wumpus was killed

        # Scream flag: true on the turn the wumpus is killed
        self.scream_active = False

        # Place pits
        for r in range(rows):
            for c in range(cols):
                if (r, c) == (0, 0):
                    continue
                if random.random() < pit_prob:
                    self.pits.add((r, c))

        # Place wumpus (not at start, not on a pit)
        available = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if (r, c) != (0, 0) and (r, c) not in self.pits
        ]
        if available:
            self.wumpus = random.choice(available)
        else:
            fallback = [
                (r, c) for r in range(rows) for c in range(cols) if (r, c) != (0, 0)
            ]
            self.wumpus = random.choice(fallback) if fallback else None

        # Place gold (not at start, not on hazard)
        gold_candidates = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if (r, c) != (0, 0)
            and (r, c) not in self.pits
            and (r, c) != self.wumpus
        ]
        if gold_candidates:
            self.gold = random.choice(gold_candidates)

    def get_adjacent(self, r, c):
        """Return list of valid adjacent cell coordinates."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                neighbors.append((nr, nc))
        return neighbors

    def get_percepts(self, r, c):
        """
        Get percepts at cell (r, c).
        Returns dict with: breeze, stench, glitter, scream
        """
        adjacent = self.get_adjacent(r, c)
        breeze = any((ar, ac) in self.pits for ar, ac in adjacent)
        stench = any((ar, ac) == self.wumpus for ar, ac in adjacent) and self.wumpus_alive
        glitter = (r, c) == self.gold and not self.gold_collected
        return {
            "breeze": breeze,
            "stench": stench,
            "glitter": glitter,
            "scream": self.scream_active,
        }

    def move_agent(self, r, c):
        """
        Move the agent to cell (r, c).
        Costs 1 point per move.
        """
        if self.game_over:
            return {"success": False, "message": "Game is already over."}

        if (r, c) not in self.get_adjacent(*self.agent_pos):
            return {"success": False, "message": f"Cell ({r},{c}) is not adjacent."}

        # Clear scream (only lasts one turn)
        self.scream_active = False

        self.agent_pos = (r, c)
        self.points -= 1  # Each move costs 1 point

        # Check for death by pit
        if (r, c) in self.pits:
            self.agent_alive = False
            self.game_over = True
            self.game_result = "dead_pit"
            self.points = 0
            return {
                "success": True,
                "alive": False,
                "message": f"💀 Agent fell into a pit at ({r},{c})! Final score: {self.points} points.",
            }

        # Check for death by wumpus
        if (r, c) == self.wumpus and self.wumpus_alive:
            self.agent_alive = False
            self.game_over = True
            self.game_result = "dead_wumpus"
            self.points = 0
            return {
                "success": True,
                "alive": False,
                "message": f"💀 Agent was eaten by the Wumpus at ({r},{c})! Final score: {self.points} points.",
            }

        # Check for gold collection
        gold_msg = ""
        if (r, c) == self.gold and not self.gold_collected:
            self.gold_collected = True
            self.points += 70  # +70 for collecting gold
            gold_msg = f" 🏆 GOLD COLLECTED! (+70 pts, total: {self.points})"

        # Check if agent returned home with gold → WIN!
        if self.gold_collected and (r, c) == (0, 0):
            self.game_over = True
            self.game_result = "win"
            return {
                "success": True,
                "alive": True,
                "percepts": self.get_percepts(r, c),
                "message": f"🎉 Agent returned home with the gold! YOU WIN! Final score: {self.points} points in {self._get_total_context()}.",
            }

        percepts = self.get_percepts(r, c)
        base_msg = f"Agent moved to ({r},{c}). Score: {self.points} pts."
        return {
            "success": True,
            "alive": True,
            "percepts": percepts,
            "message": base_msg + gold_msg,
        }

    def shoot_arrow(self, target_r, target_c):
        """
        Shoot arrow at target cell. Must be adjacent to agent.
        
        Costs -20 points.
        If wumpus is at target: wumpus dies, +10 points, scream heard.
        
        Returns dict with result info.
        """
        if self.game_over:
            return {"success": False, "message": "Game is already over."}

        if not self.has_arrow:
            return {"success": False, "message": "No arrow left! You already used your only arrow."}

        # Validate target is adjacent to agent
        adj = self.get_adjacent(*self.agent_pos)
        if (target_r, target_c) not in adj:
            return {
                "success": False,
                "message": f"Cannot shoot at ({target_r},{target_c}). Must target an adjacent cell.",
            }

        # Use the arrow
        self.has_arrow = False
        self.arrow_used = True
        self.points -= 20  # Shooting costs 20 points

        # Check if wumpus is hit
        if self.wumpus_alive and (target_r, target_c) == self.wumpus:
            self.wumpus_alive = False
            self.wumpus_killed_at = (target_r, target_c)
            self.scream_active = True
            self.points += 10  # Bonus for killing wumpus
            return {
                "success": True,
                "hit": True,
                "message": f"🎯 DIRECT HIT! Arrow killed the Wumpus at ({target_r},{target_c})! "
                           f"(-20 shoot + 10 kill = score: {self.points}). A terrible scream echoes!",
            }
        else:
            return {
                "success": True,
                "hit": False,
                "message": f"🏹 Arrow missed! Shot at ({target_r},{target_c}) but nothing was there. "
                           f"(-20 pts, score: {self.points}). No arrow remaining.",
            }

    def _get_total_context(self):
        """Helper to format the total moves context."""
        return "a heroic adventure"

    def get_full_state(self):
        """Return complete world state (for reveal/debug)."""
        grid = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                cell = {"row": r, "col": c, "contents": []}
                if (r, c) in self.pits:
                    cell["contents"].append("pit")
                if (r, c) == self.wumpus:
                    if self.wumpus_alive:
                        cell["contents"].append("wumpus")
                    else:
                        cell["contents"].append("dead_wumpus")
                if (r, c) == self.gold and not self.gold_collected:
                    cell["contents"].append("gold")
                row.append(cell)
            grid.append(row)
        return {
            "rows": self.rows,
            "cols": self.cols,
            "grid": grid,
            "agent": {"row": self.agent_pos[0], "col": self.agent_pos[1]},
            "pits": [list(p) for p in self.pits],
            "wumpus": list(self.wumpus) if self.wumpus else None,
            "wumpus_alive": self.wumpus_alive,
            "gold": list(self.gold) if self.gold else None,
            "gold_collected": self.gold_collected,
        }
