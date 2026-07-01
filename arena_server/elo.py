"""Standard Elo with a soft, asymptotic ceiling instead of a hard cap.

Below TAPER_START every win/loss swings a full K_BASE points, same as
classic Elo. From TAPER_START up to SOFT_CAP, K shrinks linearly down to
K_MIN — climbing the last few hundred points takes drastically more wins
than the first thousand. SOFT_CAP itself isn't a wall (K_MIN keeps it
non-zero, you can always inch past it), it's just glacially slow enough
that the playerbase realistically never sees it cleared by much. Both
players use their OWN current rating to pick their own K — an underdog
beating a much higher-rated opponent still gets a full-K swing even if the
opponent's own gain that round is tapered.
"""

K_BASE = 32
K_MIN = 2
TAPER_START = 1800
SOFT_CAP = 2500
ELO_FLOOR = 100  # rating never drops below this, regardless of losing streak


def k_factor(rating: int) -> float:
    if rating < TAPER_START:
        return K_BASE
    if rating >= SOFT_CAP:
        return K_MIN
    frac = (rating - TAPER_START) / (SOFT_CAP - TAPER_START)
    return K_BASE - frac * (K_BASE - K_MIN)


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(winner_elo: int, loser_elo: int) -> tuple[int, int]:
    """Returns (new_winner_elo, new_loser_elo)."""
    exp_winner = expected_score(winner_elo, loser_elo)
    exp_loser = expected_score(loser_elo, winner_elo)
    new_winner = winner_elo + k_factor(winner_elo) * (1 - exp_winner)
    new_loser = loser_elo + k_factor(loser_elo) * (0 - exp_loser)
    return max(ELO_FLOOR, round(new_winner)), max(ELO_FLOOR, round(new_loser))
