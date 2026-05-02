"""Minimum-weight perfect matching for grouping speakers into pairs.

For 8 speakers there are exactly 105 possible perfect matchings (ways to
partition 8 items into 4 unordered pairs). We enumerate all of them and
pick the one with the lowest total cost. No external library needed.
"""


def _enumerate_perfect_matchings(items):
    """Yield all perfect matchings of `items` (must have even length).

    Each matching is a tuple of pairs, e.g. ((0,1),(2,3),(4,5),(6,7)).
    Uses a recursive algorithm: pair the first element with each remaining
    element, then recursively match the rest.
    """
    if len(items) == 0:
        yield ()
        return
    first = items[0]
    rest = items[1:]
    for i, partner in enumerate(rest):
        remaining = rest[:i] + rest[i+1:]
        for matching in _enumerate_perfect_matchings(remaining):
            yield ((first, partner),) + matching


def minimum_cost_matching(speakers, pair_cost_fn):
    """Find the minimum-cost perfect matching for a list of speakers.

    Args:
        speakers: List of speaker objects/IDs (must have even length).
        pair_cost_fn: Callable(speaker_a, speaker_b) -> float cost.

    Returns:
        List of (speaker_a, speaker_b) pairs forming the optimal matching.

    For 8 speakers, this evaluates 105 matchings — trivially fast.
    For 4 speakers, only 3 matchings.
    """
    best_matching = None
    best_cost = float('inf')

    for matching in _enumerate_perfect_matchings(speakers):
        cost = sum(pair_cost_fn(a, b) for a, b in matching)
        if cost < best_cost:
            best_cost = cost
            best_matching = matching

    return list(best_matching)
