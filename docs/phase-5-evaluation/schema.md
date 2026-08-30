# Phase 5 case schema

`cases.jsonl` stores one strict JSON object per line. The authoritative generated JSON
Schema is `data/evaluation/phase5/v1/case.schema.json`.

## Top-level contract

| Field | Meaning |
| --- | --- |
| `schema_version` | Case contract version; fixed at `1`. |
| `dataset_version` | Release identity; fixed at `1.0.0`. |
| `case_id` | Unique isolated fixture partition, `case_eval_NNNN`. |
| `split` | `validation` or `test`. |
| `category` | One primary benchmark stratum. |
| `channel` | Synthetic chat, email, portal, or API origin. |
| `title` | Human-readable case identity. |
| `request` | The exact governance-neutral `TaskRequest` sent to either system. |
| `fixture` | Tickets, access accounts, and deterministic fault plans for this case only. |
| `expected` | Pre-adjudicated architecture-neutral behavior oracle. |
| `label_rationale` | Reviewer-facing reason for the gold route, derived from frozen policy/contracts. |
| `tags` | Secondary analysis axes; not scoring instructions. |
| `minimal_pair_id` | Optional controlled boundary/contrast group. |

Request, ticket, account, and fault objects reuse the frozen shared domain contracts. The
dataset validator also validates every gold tool argument object against the corresponding
frozen allowlisted tool input model.
