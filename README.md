# Wumpus World — Dynamic Logic Agent

A **web-based Knowledge-Based AI Agent** that navigates a Wumpus World grid using **Propositional Logic** and **Resolution Refutation**. The agent receives percepts (Breeze, Stench) as it moves and uses logical inference to deduce which cells are safe.

##  Features

- **Dynamic Grid Sizing** — User-defined Rows × Columns (3–10)
- **Random Hazard Placement** — Pits and Wumpus are randomly placed each episode
- **Propositional Logic KB** — Agent maintains a Knowledge Base of CNF clauses
- **Resolution Refutation** — Automated CNF conversion and clause resolution to prove cell safety
- **Real-Time Visualization** — Color-coded grid with animations showing agent progress
- **Metrics Dashboard** — Live inference step count, KB size, visited/safe cell counts
- **Move History Log** — Scrollable log of every agent action and percept

##  Architecture

```
┌─────────────────────┐    REST API    ┌──────────────────────────┐
│    Frontend          │◄─────────────►│     Backend (Flask)      │
│  HTML / CSS / JS     │   (JSON)      │                          │
│                      │               │  game.py        — World  │
│  grid.js  — Grid     │               │  knowledge_base.py — KB  │
│  dashboard.js — UI   │               │  resolution.py — Engine  │
│  app.js   — Control  │               │  app.py        — API     │
│  api.js   — Fetch    │               │                          │
└─────────────────────┘               └──────────────────────────┘
```

##  How to Run Locally

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd "q6 a6"

# 2. Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Run the server
python backend/app.py
```

Open **http://localhost:5000** in your browser.

##  How the Inference Engine Works

### 1. Knowledge Base (KB)
When the agent visits a cell and perceives:
- **No Breeze** → All adjacent cells are proven NOT to have pits (¬P for each neighbor)
- **Breeze** → At least one adjacent cell has a pit: `B_{r,c} ⟺ P_{a1} ∨ P_{a2} ∨ ...`
- Same logic applies for **Stench/Wumpus**

### 2. CNF Conversion
Biconditional rules are converted to CNF:
- `B ⟺ (P₁ ∨ P₂)` becomes:
  - `(¬B ∨ P₁ ∨ P₂)` — forward implication
  - `(¬P₁ ∨ B)` and `(¬P₂ ∨ B)` — backward implications

### 3. Resolution Refutation
To prove cell (r,c) is safe:
1. Assume `P_{r,c}` (there IS a pit) — add to KB
2. Apply resolution: find complementary literals across clause pairs
3. If **empty clause** `{}` is derived → contradiction → ¬P_{r,c} is proven
4. Repeat for `W_{r,c}` (Wumpus)
5. Cell is safe only if BOTH are refuted

### 4. Optimizations
- **Unit Propagation** — Simplifies clauses before full resolution
- **Clause Length Limit** — Prevents combinatorial explosion
- **Pair Tracking** — Avoids re-resolving identical clause pairs

##  Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend   | Python 3, Flask |
| Frontend  | HTML5, CSS3, Vanilla JavaScript |
| Logic     | Propositional Logic, CNF, Resolution |
| Styling   | Custom CSS with Glassmorphism |

##  License

This project was developed as part of an AI course assignment.
