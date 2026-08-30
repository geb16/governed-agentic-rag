# Phase 5 dataset release

Phase 5 is an offline evaluation-data layer. It does not modify or import into either
frozen runtime. The baseline and governed systems receive identical request objects,
case fixtures, knowledge, simulated tools, fault schedules, and model configuration.

## Scope and claim

Version `1.0.0` contains 100 fully synthetic enterprise-support cases:

| Primary stratum | Cases |
| --- | ---: |
| Normal | 17 |
| Ambiguous | 16 |
| Policy-sensitive | 17 |
| High-risk | 17 |
| Missing information | 16 |
| Tool failure | 17 |

Twenty cases are assigned to `validation` for harness verification and rubric
calibration. The remaining 80 are assigned to `test`. Test labels must remain unchanged
after comparative evaluation begins.

This is a production-grade **research artifact**. It is not production data and not evidence
that the sample represents every enterprise deployment. It is deployment-like within
the declared synthetic support domain. It contains no personal, customer, employee, or
confidential business data.

The near-balanced primary strata deliberately over-sample rare but costly failures. This
is a stratified challenge set, not a prevalence sample. Its raw aggregate result must not
be interpreted as the expected success or incident rate in a live support population.
