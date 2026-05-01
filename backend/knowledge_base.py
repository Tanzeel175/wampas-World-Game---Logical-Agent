"""
Propositional Logic Knowledge Base
===================================
Maintains a set of CNF clauses representing the agent's knowledge about
the Wumpus World. Supports TELL (adding facts/rules) and provides
clauses for the resolution engine to ASK queries.

Representation:
  - Literal: tuple (symbol: str, positive: bool)
    e.g., ("P_1_2", True) means "there IS a pit at (1,2)"
    e.g., ("P_1_2", False) means "there is NO pit at (1,2)"
  - Clause: frozenset of Literals (represents a disjunction)
  - KB: set of Clauses (represents a conjunction of disjunctions = CNF)
"""


def make_lit(symbol, positive=True):
    """Create a literal tuple."""
    return (symbol, positive)


def negate_lit(literal):
    """Negate a literal."""
    return (literal[0], not literal[1])


def pit_symbol(r, c):
    """Symbol for pit at (r, c)."""
    return f"P_{r}_{c}"


def wumpus_symbol(r, c):
    """Symbol for wumpus at (r, c)."""
    return f"W_{r}_{c}"


def breeze_symbol(r, c):
    """Symbol for breeze at (r, c)."""
    return f"B_{r}_{c}"


def stench_symbol(r, c):
    """Symbol for stench at (r, c)."""
    return f"S_{r}_{c}"


class KnowledgeBase:
    """
    A propositional logic Knowledge Base that stores facts as CNF clauses.
    
    The KB is designed for the Wumpus World domain. It converts percept
    observations into propositional logic rules in Conjunctive Normal Form
    and provides the clause set for resolution-based inference.
    """

    def __init__(self):
        self.clauses = set()  # set of frozenset of (symbol, positive) tuples
        self._clause_log = []  # ordered log of added clauses for debugging

    def add_clause(self, clause):
        """
        Add a single CNF clause to the KB.
        
        Args:
            clause: frozenset of literal tuples, e.g., frozenset({("P_1_2", True), ("P_2_1", True)})
        """
        # Check for tautology (clause contains both P and ¬P)
        symbols_seen = {}
        for sym, pos in clause:
            if sym in symbols_seen and symbols_seen[sym] != pos:
                return  # Tautology, skip
            symbols_seen[sym] = pos
        
        if clause not in self.clauses:
            self.clauses.add(clause)
            self._clause_log.append(clause)

    def tell_visited_safe(self, r, c):
        """
        Assert that cell (r, c) is safe: ¬P_r_c AND ¬W_r_c.
        Called when the agent visits a cell and survives.
        """
        self.add_clause(frozenset({make_lit(pit_symbol(r, c), False)}))
        self.add_clause(frozenset({make_lit(wumpus_symbol(r, c), False)}))

    def tell_breeze(self, r, c, has_breeze, adjacents):
        """
        Tell the KB about a breeze observation at cell (r, c).
        
        If has_breeze is True:
          - Assert B_r_c
          - Add biconditional: B_r_c ⟺ (P_a1 ∨ P_a2 ∨ ...)
            Forward:  ¬B_r_c ∨ P_a1 ∨ P_a2 ∨ ...
            Backward: ¬P_ai ∨ B_r_c  (for each adjacent ai)
        
        If has_breeze is False:
          - Assert ¬B_r_c
          - Directly deduce ¬P_ai for each adjacent cell
        
        Args:
            r, c: Cell coordinates.
            has_breeze: Whether breeze was perceived.
            adjacents: List of (row, col) tuples of adjacent cells.
        """
        b_sym = breeze_symbol(r, c)

        if has_breeze:
            # Fact: B_r_c is true
            self.add_clause(frozenset({make_lit(b_sym, True)}))

            # Forward direction: B_r_c → (P_a1 ∨ P_a2 ∨ ...)
            # CNF: ¬B_r_c ∨ P_a1 ∨ P_a2 ∨ ...
            forward_clause = [make_lit(b_sym, False)]
            for ar, ac in adjacents:
                forward_clause.append(make_lit(pit_symbol(ar, ac), True))
            self.add_clause(frozenset(forward_clause))

            # Backward direction: P_ai → B_r_c (for each adjacent)
            # CNF: ¬P_ai ∨ B_r_c
            for ar, ac in adjacents:
                self.add_clause(frozenset({
                    make_lit(pit_symbol(ar, ac), False),
                    make_lit(b_sym, True),
                }))
        else:
            # Fact: ¬B_r_c
            self.add_clause(frozenset({make_lit(b_sym, False)}))

            # From ¬B_r_c and B_r_c ⟺ (P_a1 ∨ ...):
            # We deduce ¬P_ai for ALL adjacent cells
            for ar, ac in adjacents:
                self.add_clause(frozenset({make_lit(pit_symbol(ar, ac), False)}))

    def tell_stench(self, r, c, has_stench, adjacents):
        """
        Tell the KB about a stench observation at cell (r, c).
        
        Analogous to tell_breeze but for Wumpus instead of Pit.
        
        Args:
            r, c: Cell coordinates.
            has_stench: Whether stench was perceived.
            adjacents: List of (row, col) tuples of adjacent cells.
        """
        s_sym = stench_symbol(r, c)

        if has_stench:
            # Fact: S_r_c is true
            self.add_clause(frozenset({make_lit(s_sym, True)}))

            # Forward: S_r_c → (W_a1 ∨ W_a2 ∨ ...)
            # CNF: ¬S_r_c ∨ W_a1 ∨ W_a2 ∨ ...
            forward_clause = [make_lit(s_sym, False)]
            for ar, ac in adjacents:
                forward_clause.append(make_lit(wumpus_symbol(ar, ac), True))
            self.add_clause(frozenset(forward_clause))

            # Backward: W_ai → S_r_c
            # CNF: ¬W_ai ∨ S_r_c
            for ar, ac in adjacents:
                self.add_clause(frozenset({
                    make_lit(wumpus_symbol(ar, ac), False),
                    make_lit(s_sym, True),
                }))
        else:
            # Fact: ¬S_r_c
            self.add_clause(frozenset({make_lit(s_sym, False)}))

            # From ¬S_r_c: deduce ¬W_ai for all adjacent cells
            for ar, ac in adjacents:
                self.add_clause(frozenset({make_lit(wumpus_symbol(ar, ac), False)}))

    def tell_single_wumpus_constraint(self, rows, cols):
        """
        Add the constraint that there is exactly one Wumpus on the grid.
        
        At-least-one: W_0_0 ∨ W_0_1 ∨ ... ∨ W_(rows-1)_(cols-1)
        At-most-one:  ¬W_i_j ∨ ¬W_k_l  for all (i,j) ≠ (k,l)
        
        Note: We only add the at-least-one clause and handle at-most-one
        via pairwise constraints (limited to keep KB manageable).
        """
        # At least one wumpus
        all_wumpus_lits = []
        for r in range(rows):
            for c in range(cols):
                all_wumpus_lits.append(make_lit(wumpus_symbol(r, c), True))
        self.add_clause(frozenset(all_wumpus_lits))

        # At most one wumpus: for each pair, ¬W_i_j ∨ ¬W_k_l
        cells = [(r, c) for r in range(rows) for c in range(cols)]
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                r1, c1 = cells[i]
                r2, c2 = cells[j]
                self.add_clause(frozenset({
                    make_lit(wumpus_symbol(r1, c1), False),
                    make_lit(wumpus_symbol(r2, c2), False),
                }))

    def get_clauses(self):
        """Return the set of all CNF clauses in the KB."""
        return set(self.clauses)

    def get_clause_count(self):
        """Return the number of clauses in the KB."""
        return len(self.clauses)

    def get_clause_log(self):
        """Return human-readable clause log for debugging."""
        result = []
        for clause in self._clause_log:
            lits = []
            for sym, pos in sorted(clause):
                lits.append(sym if pos else f"¬{sym}")
            result.append(" ∨ ".join(lits))
        return result
