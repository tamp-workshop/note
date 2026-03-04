"""
tamp_core.stats
~~~~~~~~~~~~~~~
Local statistical analysis of your corpus. No API calls. No data leaves
your machine. Requires a minimum of COLD_START_DAYS days of history before
pattern-based insights are shown; before that, falls back to plain counts.

Used by:
  tamp-note  → welcome screen summary, /stats command
  tamp-insight (future) → deeper analysis and reports
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, stdev
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .corpus import Corpus

COLD_START_DAYS = 14   # minimum history before ML insights activate
ANOMALY_SIGMA   = 1.5  # standard deviations from mean = "unusual"


@dataclass
class Signal:
    """A single surface-worthy insight."""
    text:     str
    kind:     str     # "overdue" | "anomaly" | "streak" | "info"
    priority: int = 0 # higher = shown first


@dataclass
class CorpusStats:
    """Full statistical picture of the corpus."""
    total_logs:       int
    total_entries:    int
    active_days:      int
    open_signals:     int
    open_todos:       int
    oldest_open_days: int
    top_contexts:     list[tuple[str, int]]
    top_actions:      list[tuple[str, int]]
    avg_entries_day:  float
    peak_hour:        int | None
    completion_rate:  float        # 0.0 – 1.0
    insights:         list[Signal]
    has_enough_data:  bool


def analyse(corpus: Corpus) -> CorpusStats:
    """
    Run the full statistical analysis. Safe to call on an empty corpus —
    returns sensible defaults when there's not enough data.
    """
    logs    = corpus.all_logs()
    entries = corpus.all_entries()

    if not logs:
        return _empty_stats()

    # ── basic counts ─────────────────────────────────────────────────────────
    total_logs    = len(logs)
    total_entries = len(entries)
    active_days   = sum(1 for log in logs if log.entries)
    open_sigs     = corpus.open_signals()
    open_todos    = corpus.open_todos()

    oldest_open   = max((e.age_days for e in open_sigs), default=0)

    # ── tag frequencies ───────────────────────────────────────────────────────
    tag_counts   = corpus.tag_counts()
    ctx_counts   = [(k, v) for k, v in tag_counts.items() if k.startswith("@")]
    act_counts   = [(k, v) for k, v in tag_counts.items() if k.startswith("+")]

    top_contexts = sorted(ctx_counts, key=lambda x: x[1], reverse=True)[:3]
    top_actions  = sorted(act_counts, key=lambda x: x[1], reverse=True)[:3]

    # ── completion rate ───────────────────────────────────────────────────────
    all_with_actions = [e for e in entries if e.actions]
    done_count       = sum(1 for e in all_with_actions if e.done)
    completion_rate  = done_count / len(all_with_actions) if all_with_actions else 0.0

    # ── average entries per active day ───────────────────────────────────────
    avg_entries_day = total_entries / active_days if active_days else 0.0

    # ── peak hour ─────────────────────────────────────────────────────────────
    hour_counts: dict[int, int] = defaultdict(int)
    for e in entries:
        try:
            h = int(e.time.split(":")[0])
            hour_counts[h] += 1
        except (ValueError, IndexError):
            pass
    peak_hour = max(hour_counts, key=hour_counts.__getitem__) if hour_counts else None

    # ── ML insights (require minimum history) ────────────────────────────────
    has_enough = total_logs >= COLD_START_DAYS
    insights   = []

    if has_enough and corpus.config.stats_enabled:
        insights = _generate_insights(corpus, logs, entries, open_sigs, avg_entries_day)

    return CorpusStats(
        total_logs       = total_logs,
        total_entries    = total_entries,
        active_days      = active_days,
        open_signals     = len(open_sigs),
        open_todos       = len(open_todos),
        oldest_open_days = oldest_open,
        top_contexts     = top_contexts,
        top_actions      = top_actions,
        avg_entries_day  = avg_entries_day,
        peak_hour        = peak_hour,
        completion_rate  = completion_rate,
        insights         = insights,
        has_enough_data  = has_enough,
    )


def welcome_signals(corpus: Corpus) -> list[Signal]:
    """
    Return a short list of signals for the welcome screen.
    Kept deliberately brief — the full picture is behind /stats.
    """
    signals: list[Signal] = []
    todos   = corpus.open_todos()

    if not todos:
        return signals

    # overdue todos (age > personal average resolution time)
    avg_res = _avg_resolution_days(corpus)
    for todo in todos:
        threshold = max(3, round(avg_res * 1.5)) if avg_res else 7
        if todo.age_days >= threshold:
            signals.append(Signal(
                text     = f"{todo.clean_text}  ({todo.age_days}d open)",
                kind     = "overdue",
                priority = todo.age_days,
            ))

    signals.sort(key=lambda s: s.priority, reverse=True)
    return signals[:3]   # max 3 on welcome screen — don't overwhelm


# ── Internal helpers ──────────────────────────────────────────────────────────

def _empty_stats() -> CorpusStats:
    return CorpusStats(
        total_logs=0, total_entries=0, active_days=0,
        open_signals=0, open_todos=0, oldest_open_days=0,
        top_contexts=[], top_actions=[],
        avg_entries_day=0.0, peak_hour=None,
        completion_rate=0.0, insights=[], has_enough_data=False,
    )


def _avg_resolution_days(corpus: Corpus) -> float | None:
    """Average days between creation and completion for done entries."""
    logs        = corpus.all_logs()
    all_entries = corpus.all_entries()
    done        = [e for e in all_entries if e.done]

    if len(done) < 5:
        return None

    # We use age_days as a proxy — imperfect but doesn't need extra metadata
    # A more accurate version would track completion timestamps separately
    ages = [e.age_days for e in done]
    return mean(ages) if ages else None


def _generate_insights(corpus, logs, entries, open_sigs, avg_entries_day) -> list[Signal]:
    insights: list[Signal] = []

    # ── 1. entry volume anomaly ───────────────────────────────────────────────
    # Compare today's count to historical mean ± stdev
    recent_counts = [len(log.entries) for log in logs[1:30]]  # last 30 days excl. today
    if len(recent_counts) >= 7:
        mu    = mean(recent_counts)
        sigma = stdev(recent_counts) if len(recent_counts) > 1 else 0
        today_count = len(logs[0].entries) if logs else 0

        if sigma > 0 and today_count < mu - ANOMALY_SIGMA * sigma and today_count < 3:
            insights.append(Signal(
                text     = f"quieter than usual today ({today_count} entries, avg {mu:.0f})",
                kind     = "anomaly",
                priority = 1,
            ))

    # ── 2. todo backlog trend ─────────────────────────────────────────────────
    # Count open todos over the last 4 weeks in weekly bins
    today = date.today()
    bins  = []
    for week in range(4):
        start = today - timedelta(days=7 * (week + 1))
        end   = today - timedelta(days=7 * week)
        count = sum(
            1 for e in entries
            if not e.done and "todo" in e.actions
            and start <= e.date <= end
        )
        bins.append(count)

    if len(bins) == 4 and all(b > 0 for b in bins[:3]):
        # monotonically increasing backlog = signal worth surfacing
        if bins[0] > bins[1] > bins[2]:
            insights.append(Signal(
                text     = "todo backlog growing — 4-week trend increasing",
                kind     = "anomaly",
                priority = 2,
            ))

    # ── 3. resolution rate drop ───────────────────────────────────────────────
    recent_todos = [e for e in entries if "todo" in e.actions and e.date >= today - timedelta(days=14)]
    if len(recent_todos) >= 4:
        recent_done = sum(1 for e in recent_todos if e.done)
        recent_rate = recent_done / len(recent_todos)
        if recent_rate < 0.3:
            insights.append(Signal(
                text     = f"recent completion rate {recent_rate:.0%} — lower than usual",
                kind     = "anomaly",
                priority = 3,
            ))

    # ── 4. streak ─────────────────────────────────────────────────────────────
    streak = _active_streak(logs)
    if streak >= 7:
        insights.append(Signal(
            text     = f"{streak}-day logging streak",
            kind     = "streak",
            priority = 0,
        ))

    return sorted(insights, key=lambda s: s.priority, reverse=True)


def _active_streak(logs) -> int:
    """Count consecutive days with at least one entry ending at today."""
    today  = date.today()
    log_map = {log.date: log for log in logs}
    streak  = 0
    cursor  = today
    while cursor in log_map and log_map[cursor].entries:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
