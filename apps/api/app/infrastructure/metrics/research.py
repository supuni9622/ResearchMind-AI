RESEARCH_RUNS_TOTAL = "research_runs_total"

RESEARCH_RUNS_COMPLETED_TOTAL = "research_runs_completed_total"

RESEARCH_RUNS_FAILED_TOTAL = "research_runs_failed_total"

RESEARCH_DURATION = "research"

RESEARCH_RUN_DURATION = "deep_research_run"
"""E17 follow-up (`EVALUATION_IMPLEMENTATION_TRACKER.md`): Deep Research's
own end-to-end run duration, `run.completed_at - run.started_at` --
distinct from `RESEARCH_DURATION` above (Chat/Linear Research's
single-turn latency). A Deep Research run's wall-clock duration
legitimately includes human-approval wait time (plan/report/web-search
checkpoints), which can span minutes to hours -- an order of magnitude
different scale than `RUNTIME_BUCKETS`, so this gets its own metric name
and bucket set (`DEEP_RESEARCH_RUN_BUCKETS`) rather than reusing
`RESEARCH_DURATION`'s (a single Prometheus histogram has one fixed
bucket set shared across every label value, so Chat/Linear Research's
existing seconds-scale buckets can't also serve this metric)."""

RESEARCH_REVIEW_DECISIONS_TOTAL = "research_review_decisions_total"
