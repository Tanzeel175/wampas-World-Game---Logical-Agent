"""
Resolution Refutation Engine
=============================
Implements the Resolution Refutation algorithm for propositional logic.

To prove KB ⊨ α (KB entails α):
  1. Negate α to get ¬α
  2. Add ¬α clauses to the KB clause set
  3. Repeatedly resolve pairs of clauses
  4. If the empty clause {} is derived → KB ⊨ α (contradiction found)
  5. If no new clauses can be derived → KB ⊭ α
"""

from knowledge_base import make_lit, negate_lit, pit_symbol, wumpus_symbol


MAX_RESOLUTION_STEPS = 100000
MAX_CLAUSE_SET_SIZE = 8000
MAX_CLAUSE_LENGTH = 12


def resolve_pair(clause1, clause2):
    """
    Attempt to resolve two clauses on a complementary literal pair.
    
    Two clauses can be resolved if one contains literal L and the other
    contains ¬L. The resolvent is (clause1 - {L}) ∪ (clause2 - {¬L}).
    
    Args:
        clause1: frozenset of (symbol, positive) tuples.
        clause2: frozenset of (symbol, positive) tuples.
    
    Returns:
        List of resolvent clauses (may be empty if no resolution possible).
    """
    resolvents = []

    for lit in clause1:
        complement = negate_lit(lit)
        if complement in clause2:
            # Build the resolvent: union minus the complementary pair
            new_clause = (clause1 - {lit}) | (clause2 - {complement})

            # Skip if resolvent is too large (performance guard)
            if len(new_clause) > MAX_CLAUSE_LENGTH:
                continue

            # Check for tautology: if clause contains both P and ¬P, skip
            symbols = {}
            is_tautology = False
            for sym, pos in new_clause:
                if sym in symbols:
                    if symbols[sym] != pos:
                        is_tautology = True
                        break
                else:
                    symbols[sym] = pos

            if not is_tautology:
                resolvents.append(frozenset(new_clause))

    return resolvents


def resolution_refutation(kb_clauses, negated_query_clauses):
    """
    Prove entailment using Resolution Refutation.
    
    Attempts to derive the empty clause (contradiction) from
    KB ∧ ¬query, which proves KB ⊨ query.
    
    Uses an optimized approach:
      - Only resolves NEW clauses with existing ones (avoids re-resolving old pairs)
      - Applies unit propagation for efficiency
      - Limits clause set size and step count
    
    Args:
        kb_clauses: set of frozenset clauses from the Knowledge Base.
        negated_query_clauses: list of frozenset clauses representing ¬query.
    
    Returns:
        tuple: (entailed: bool, inference_steps: int, resolution_trace: list[str])
    """
    # Combine all clauses
    all_clauses = set(kb_clauses)
    for c in negated_query_clauses:
        all_clauses.add(c)

    steps = 0
    trace = []

    # Phase 1: Unit propagation
    all_clauses, prop_steps, prop_trace = _unit_propagate(all_clauses)
    steps += prop_steps
    trace.extend(prop_trace)

    # Check if empty clause was produced during unit propagation
    if frozenset() in all_clauses:
        trace.append("Empty clause derived during unit propagation → ENTAILED")
        return True, steps, trace

    # Phase 2: Resolution loop
    new_clauses = set(all_clauses)  # Start by treating all as "new"
    processed_pairs = set()

    while steps < MAX_RESOLUTION_STEPS:
        generated = set()
        clause_list = sorted(list(all_clauses), key=len)  # Prefer shorter clauses

        found_empty = False
        for clause in list(new_clauses):
            for other in clause_list:
                if clause is other:
                    continue

                # Create a canonical pair key to avoid duplicate work
                pair_key = (min(id(clause), id(other)), max(id(clause), id(other)))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                steps += 1
                resolvents = resolve_pair(clause, other)

                for resolvent in resolvents:
                    if len(resolvent) == 0:
                        # Empty clause found → contradiction → ENTAILED
                        trace.append(
                            f"Step {steps}: Resolved {_clause_str(clause)} with "
                            f"{_clause_str(other)} → EMPTY CLAUSE (contradiction)"
                        )
                        return True, steps, trace

                    if resolvent not in all_clauses and resolvent not in generated:
                        generated.add(resolvent)

                if steps >= MAX_RESOLUTION_STEPS:
                    break
            if steps >= MAX_RESOLUTION_STEPS:
                break

        if not generated:
            # No new clauses can be derived → NOT ENTAILED
            trace.append(f"No new clauses after {steps} steps → NOT ENTAILED")
            return False, steps, trace

        # Guard against explosion
        if len(all_clauses) + len(generated) > MAX_CLAUSE_SET_SIZE:
            trace.append(f"Clause set limit reached ({MAX_CLAUSE_SET_SIZE}) → INCONCLUSIVE")
            return False, steps, trace

        all_clauses |= generated
        new_clauses = generated  # Next iteration only resolves new clauses

        # Unit propagation on updated set
        all_clauses, prop_steps, prop_trace = _unit_propagate(all_clauses)
        steps += prop_steps
        trace.extend(prop_trace)

        if frozenset() in all_clauses:
            trace.append("Empty clause derived after propagation → ENTAILED")
            return True, steps, trace

    trace.append(f"Step limit reached ({MAX_RESOLUTION_STEPS}) → INCONCLUSIVE")
    return False, steps, trace


def _unit_propagate(clauses):
    """
    Apply unit propagation: if a unit clause {L} exists, remove ¬L from
    all other clauses and remove clauses that contain L.
    
    Returns:
        tuple: (simplified_clauses, steps, trace)
    """
    clauses = set(clauses)
    steps = 0
    trace = []
    changed = True

    while changed:
        changed = False
        unit_clauses = [c for c in clauses if len(c) == 1]

        for unit in unit_clauses:
            lit = next(iter(unit))
            comp = negate_lit(lit)
            new_clauses = set()

            for clause in clauses:
                if clause is unit or clause == unit:
                    new_clauses.add(clause)
                    continue

                if lit in clause:
                    # Clause is satisfied by the unit literal, remove it
                    steps += 1
                    changed = True
                    continue

                if comp in clause:
                    # Remove the complementary literal from the clause
                    reduced = clause - {comp}
                    steps += 1
                    changed = True
                    new_clauses.add(reduced)
                else:
                    new_clauses.add(clause)

            clauses = new_clauses

    return clauses, steps, trace


def is_cell_safe(kb, r, c):
    """
    Ask the KB whether cell (r, c) is provably safe.
    
    Proves ¬P_r_c ∧ ¬W_r_c by separately proving each conjunct
    via resolution refutation.
    
    Args:
        kb: KnowledgeBase instance.
        r, c: Cell coordinates.
    
    Returns:
        dict: {
            "safe": bool,
            "pit_safe": bool,
            "wumpus_safe": bool,
            "total_steps": int,
            "trace": list[str],
        }
    """
    kb_clauses = kb.get_clauses()
    total_steps = 0
    all_trace = []

    # 1) Prove ¬P_r_c: negate it → assume P_r_c, find contradiction
    pit_neg_query = [frozenset({make_lit(pit_symbol(r, c), True)})]
    pit_safe, pit_steps, pit_trace = resolution_refutation(kb_clauses, pit_neg_query)
    total_steps += pit_steps
    all_trace.append(f"--- Proving ¬P_{r}_{c} ({pit_steps} steps) → {'SAFE' if pit_safe else 'UNKNOWN'}")
    all_trace.extend(pit_trace)

    # 2) Prove ¬W_r_c: negate it → assume W_r_c, find contradiction
    wumpus_neg_query = [frozenset({make_lit(wumpus_symbol(r, c), True)})]
    wumpus_safe, wumpus_steps, wumpus_trace = resolution_refutation(kb_clauses, wumpus_neg_query)
    total_steps += wumpus_steps
    all_trace.append(f"--- Proving ¬W_{r}_{c} ({wumpus_steps} steps) → {'SAFE' if wumpus_safe else 'UNKNOWN'}")
    all_trace.extend(wumpus_trace)

    return {
        "safe": pit_safe and wumpus_safe,
        "pit_safe": pit_safe,
        "wumpus_safe": wumpus_safe,
        "total_steps": total_steps,
        "trace": all_trace,
    }


def _clause_str(clause):
    """Format a clause as a human-readable string."""
    if not clause:
        return "{}"
    lits = []
    for sym, pos in sorted(clause):
        lits.append(sym if pos else f"¬{sym}")
    return "{" + ", ".join(lits) + "}"
