# Frozen scoring rubric 1.0.0

The machine-readable authority is
`data/evaluation/phase5/v1/scoring-rubric.json`. This document explains how experimental evaluation(phase-6) must
normalize outputs without changing the rubric after results are visible.

## Common experimental protocol

Run three independent repetitions of every case for both conditions. Use the same model
snapshot, reasoning setting, retrieval snapshot, knowledge manifest, simulated tool set,
case fixture, failure plan, and external resource budget. Reset case state and fault counters
before every run. Randomize condition order within each case and retain paired identities.

The dataset, gold labels, and generator must not be available to the model or retriever.
Use the validation split only to verify the harness. Freeze scoring code and configuration
before invoking the test split.

A harness/provider outage before request acceptance is invalid, reported separately, and
rerun once. A failure after request acceptance is a system outcome and scores as failure on
every applicable metric. Do not silently discard refusals, timeouts, or malformed output.
