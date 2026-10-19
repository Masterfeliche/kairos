# 12. Risk Register

Scale: Likelihood (L) and Impact (I) = Low/Med/High. Score = L×I priority.

| ID | Risk | Type | L | I | Mitigation |
|----|------|------|---|---|------------|
| R1 | Extraction loses wrapped course codes (`(CSEU` / `07102)`) | Data quality | High | High | Geometry-first parser; regression fixture p42; gold-set gate; low-confidence flags |
| R2 | Column/day misalignment on merged rows | Data quality | Med | High | Assign words by coordinates; cross-check extractors; admin review of flagged rows |
| R3 | Multi-hour session encoding misread (merged vs repeated) | Data quality | Med | Med | Confirm semantics (Open Decisions); detect tall/merged cells; merge only on exact match |
| R4 | Shared classes wrongly flagged as conflicts | Data quality | Med | Med | Model shared cohorts explicitly; conflict detector excludes shared overlaps |
| R5 | Continuation pages break one-page-one-cohort rule | Data quality | Med | Med | Carry-forward cohort; continuation-page handling + fixture p75 |
| R6 | Ambiguous `-x-` vs `---` semantics | Requirements | High | Med | Confirm with DIT; store raw plus "not scheduled"/"free" mapping; easy to re-map |
| R7 | Source PDF format changes next semester | Maintenance | High | High | Layout classification + validation alarms; keep fallback extractor; admin can force manual fixes |
| R8 | Admin publishes bad data | Operational | Med | High | Atomic publish, blocking error gate, diff review, rollback, audit |
| R9 | Successful import but no active version / partial state | Operational | Low | High | Staging vs active separation; single publish transaction; concurrency lock |
| R10 | Malicious/oversized PDF upload | Security | Low | High | Type/magic checks, size/page limits, encryption/JS rejection, sandboxed worker |
| R11 | Unauthorised timetable modification | Security | Low | High | Restricted auth + roles, CSRF, audit trail, MFA for owner |
| R12 | Single-VM outage / data loss | Operational | Med | Med | Nightly backups + storage versioning; restore drills; RPO/RTO targets |
| R13 | Cost creep from OCR/ML/heavy infra | Operational | Med | Med | No OCR/ML in MVP; single VM + managed DB; measure before scaling |
| R14 | Low student adoption | Adoption | Med | Med | Fast mobile UX, memorable URL/QR, "Today" default, remembered selection, version trust |
| R15 | Students trust stale/incorrect data | Adoption | Med | High | Prominent last-updated indicator; never fabricate; show "not provided" |
| R16 | Venue/lecturer free-text inconsistency | Data quality | High | Low | Store raw + optional normalised value; don't over-normalise; defer identity resolution |
| R17 | Lecturer name privacy concerns | Legal/Privacy | Low | Med | Display as published (professional directory); restrict admin evidence; policy review |
| R18 | Scope creep into full UMIS/chatbot | Delivery | Med | Med | MVP scope guardrails (artifact 3); explicit out-of-scope list |

Top priorities to resolve before build: **R1, R2, R6, R7**.
