# Absolute Gap Detector — Design Spec

## Summary
Add a new signal type `large_divergence` that fires based on the absolute gap between Polymarket implied probability and sportsbook implied probability. This is additive to the existing delta-based `divergence_change` detector, which only fires when the gap *changes* between runs.

## Motivation
Large persistent gaps (Celtics -3.4pp, Spurs -2.8pp, OKC -2.9pp) are currently invisible because the delta detector requires a ≥1pp *change* between runs. These steady divergences are valuable signal for paid subscribers.

## Design

### New Detector: `detect_large_divergence()`
- **File:** `scripts/signal_engine.py`
- **Signal type:** `large_divergence`
- **Trigger:** `abs(gap) >= 0.025` (2.5pp)
- **Frequency:** Fires every run for every team meeting threshold
- **Severity:**
  - `abs(gap) >= 0.04` → `high`
  - `abs(gap) >= 0.03` → `medium`
  - `abs(gap) >= 0.025` → `low`
- **Direction:** `gap > 0` → "PM above books", `gap < 0` → "books above PM"
- **Message template:** `"{team} PM {pm_prob:.0%} vs Books {book_prob:.0%} ({abs(gap):.1f}pp gap, {direction})"`

### Formatter Updates
- **`alert_formatter.py`:**
  - Add entry: `"large_divergence": "[DIVERGE]"` to `TYPE_PREFIX`
  - Add simple formatting branch to `fmt_twitter()` for the new type

### What Stays the Same
- Existing `divergence_change` delta detector — unchanged
- All other signal types — unchanged
- Orchestrator, bots, workflow — no changes needed

### Current Teams That Would Fire (as of Apr 26)
| Team | Gap | Severity |
|------|-----|----------|
| Boston Celtics | -3.4pp | medium |
| San Antonio Spurs | -2.8pp | low |
| Oklahoma City Thunder | -2.9pp | low |

## Implementation
- ~30 lines in `signal_engine.py` (detector function + wiring)
- ~10 lines in `alert_formatter.py` (prefix + twitter format)
- No new dependencies, no new files
