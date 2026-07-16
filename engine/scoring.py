def compute_severity_score(graph_distance: int, cochange_frequency: int) -> float:
    """
    Combine dependency-graph proximity and git co-change history into a single
    severity score between 0.0 and 1.0 representing how likely a file is to
    break when another file changes.

    This is a pure function — no I/O, no graph access, no side effects.

    Formula:
        graph_score    = 1 / (graph_distance + 1)
        cochange_score = min(cochange_frequency / 5, 1.0)
        final_score    = (graph_score * 0.6) + (cochange_score * 0.4)

    WHY the 60/40 weighting:
        The dependency graph captures *structural* coupling — if File A directly
        imports File B, a change in B can break A at compile/run time. This is
        the strongest and most reliable signal, so it gets the majority weight
        (60%).

        Co-change frequency captures *behavioral* coupling — even when two files
        have no import link, if developers consistently change them together,
        there's likely a hidden functional relationship (shared assumptions,
        coordinated config, implicit contracts). This is the whole reason
        RippleGuard mines git history: to catch risks the import graph misses.
        But co-change is inherently noisier (two files might just live near each
        other in the directory and get edited together by coincidence), so it
        gets the minority weight (40%).

        The 60/40 split ensures that a direct import always produces a high
        score on its own (~0.30 from graph alone at distance 1), while co-change
        can boost a file from invisible (~0.0) to visible (~0.40 at 5+ co-changes
        even with no graph connection), allowing the tool to surface hidden risks
        without drowning in noise.
    """
    # Graph proximity: inversely proportional to distance. Distance 1 (direct
    # import) → 0.50, distance 2 → 0.33, distance 999 (no path) → ~0.001.
    graph_score = 1.0 / (graph_distance + 1)

    # Co-change frequency: linearly scaled, capped at 1.0 once a pair has
    # co-changed 5+ times (diminishing returns beyond that).
    cochange_score = min(cochange_frequency / 5.0, 1.0)

    final_score = (graph_score * 0.6) + (cochange_score * 0.4)
    return round(final_score, 4)
