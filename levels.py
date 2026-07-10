"""
Replicates the onm/decider ladder from the original Excel sheet:

  diff        = High - Low   (and Low - High, for the low-side ladder)
  onm step    = diff * 0.146
  decider step = diff * 0.236

  High-side ladder (resistance / breakout targets), 10 rungs each:
    onm_1     = High + onm_step
    onm_n     = onm_(n-1) + onm_step
    decider_1 = High + decider_step
    decider_n = decider_(n-1) + decider_step

  Low-side ladder (support / breakdown targets) mirrors this using Low and
  the negative diff, so it descends below Low.
"""
from __future__ import annotations

from dataclasses import dataclass, field


N_RUNGS = 10
ONM_RATIO = 0.146
DECIDER_RATIO = 0.236


@dataclass
class Ladder:
    base: float          # High or Low
    onm: list[float] = field(default_factory=list)      # 10 rungs
    decider: list[float] = field(default_factory=list)  # 10 rungs


def build_ladder(anchor: float, other: float) -> Ladder:
    """anchor=High,other=Low for the high-side ladder; swap for the low-side ladder."""
    diff = anchor - other
    onm_step = diff * ONM_RATIO
    decider_step = diff * DECIDER_RATIO

    onm_levels = []
    level = anchor
    for _ in range(N_RUNGS):
        level = level + onm_step
        onm_levels.append(level)

    decider_levels = []
    level = anchor
    for _ in range(N_RUNGS):
        level = level + decider_step
        decider_levels.append(level)

    return Ladder(base=anchor, onm=onm_levels, decider=decider_levels)


@dataclass
class TickerLevels:
    ticker: str
    prev_high: float
    prev_low: float
    high_ladder: Ladder
    low_ladder: Ladder


def compute_levels(ticker: str, prev_high: float, prev_low: float) -> TickerLevels:
    high_ladder = build_ladder(prev_high, prev_low)   # rungs go up, above High
    low_ladder = build_ladder(prev_low, prev_high)    # rungs go down, below Low
    return TickerLevels(ticker, prev_high, prev_low, high_ladder, low_ladder)


def classify(ltp: float | None, tl: TickerLevels) -> str:
    """Same two-tier signal used in the Excel Screener tab."""
    if ltp is None:
        return "No live price"
    high_onm_1, high_decider_1 = tl.high_ladder.onm[0], tl.high_ladder.decider[0]
    low_onm_1, low_decider_1 = tl.low_ladder.onm[0], tl.low_ladder.decider[0]

    if ltp > high_decider_1:
        return "BREAKOUT above Decider"
    if ltp > high_onm_1:
        return "Above Onm (watch)"
    if ltp < low_decider_1:
        return "BREAKDOWN below Decider"
    if ltp < low_onm_1:
        return "Below Onm (watch)"
    return "Neutral / inside range"
