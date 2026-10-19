# 5. Data Model

Design principles:
- **Provenance everywhere**: published data is traceable to a source document + page.
- **Staging vs published are separated**: extraction creates a draft; only an approved, atomic
  publish promotes it.
- **Uncertainty is first-class**: every extracted field can be flagged; nothing uncertain is
  silently published.
- **Avoid speculative entities**: start with the tables the MVP actually uses.

## 5.1 Entities (MVP)

```
institution 1─* programme 1─* cohort
academic_period 1─* timetable_version *─1 source_document
timetable_version 1─* timetable_session
timetable_session *─* cohort              (session_cohorts; shared classes)
timetable_session *─1 course
timetable_session *─1 lecturer  (nullable, via session_lecturers)
timetable_session *─1 venue      (nullable)
timetable_session 1─* session_field_evidence
timetable_version 1─* import_job 1─* validation_issue
timetable_version 1─* publication_record
admin_user 1─* audit_event
```

### `institution`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| name | text | "Dar es Salaam Institute of Technology" |
| code | text unique | "DIT" |

### `programme`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| institution_id | uuid FK | |
| name | text | e.g. "BEng Civil Engineering" |
| code | text | e.g. "BENG-CE" [OPEN: mapping] |
| level | enum | `beng` / `diploma` / `masters` / `btech` |
| department | text nullable | e.g. "CIVIL" |

### `cohort` (class/group)
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| programme_id | uuid FK | |
| code | text unique | raw page id, e.g. `BENG24CE-1` |
| intake_year | smallint nullable | 24 → 2024 [ASSUMPTION] |
| section | text nullable | `1`, `2` |

### `academic_period`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| institution_id | uuid FK | |
| year_label | text | "2025/2026" |
| semester | enum | `1` / `2` / `annual` |
| is_active | boolean | at most one active per institution |

### `source_document`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| period_id | uuid FK nullable | |
| original_filename | text | |
| sha256 | char(64) unique | content hash (dedupe uploads) |
| page_count | int | |
| storage_key | text | protected object-storage path |
| uploaded_by | uuid FK admin_user | |
| uploaded_at | timestamptz | |

### `timetable_version`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| period_id | uuid FK | |
| source_document_id | uuid FK | |
| label | text | e.g. "Semester I — rev 2026-03-10" |
| status | enum | `draft` / `review` / `published` / `superseded` / `failed` |
| is_active | boolean | exactly one published active version per period |
| published_at | timestamptz nullable | |
| created_by | uuid FK | |

Constraint: `UNIQUE(period_id) WHERE is_active` (partial unique index) — one active published
version per period. Publishing is a single transaction that flips the old to `superseded` and the
new to `published`/active.

### `course`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| name | text | from PDF; may be shared across cohorts |
| code | text | e.g. `CEU 08109`; nullable if unextractable |
| department | text nullable | |

Unique on `(code)` where code is not null; otherwise dedupe by normalised name.

### `lecturer`
| id | uuid PK · name text · raw_variants text[] |
Names are free text; keep raw string on the session and an optional normalised lecturer row to allow
future grouping without forcing identity resolution now. **[OPEN]**

### `venue`
| id | uuid PK · code text · name text nullable · kind enum(`room`,`lab`,`other`) nullable |
Venues are free text (`CEITT1-C4`, `Rafic- F1-9 (Analog electronics lab)`). Keep decoded code + raw.

### `timetable_session`
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| version_id | uuid FK | |
| day_of_week | smallint 1–5 | Mon=1 |
| start_time | time | |
| end_time | time | |
| course_id | uuid FK nullable | null ⇒ missing code |
| course_name_raw | text | always store raw title |
| course_code_raw | text nullable | |
| venue_id | uuid FK nullable | |
| venue_raw | text nullable | |
| lecturer_raw | text nullable | may be multiple; also 1–* via join |
| session_type | enum nullable | `lecture`/`practical`/`other` (from -L/-P) |
| extraction_method | enum | `geometry` / `pdfplumber` / `manual` |
| confidence | enum | `high` / `low` |
| source_page | int | 1-based page in source document |
| source_cell_bbox | jsonb | for evidence/highlight |
| source_text_raw | text | exact cell text |
| created_at / updated_at | timestamptz | |

Indexes: `(version_id, day_of_week, start_time)`, `(version_id, course_id)`, `(version_id, cohort_id)`.

### `session_cohorts` (join; shared classes)
| session_id | cohort_id | is_primary |
Supports `BENG24MNE-1, BENG23OG-1` being **one** session linked to two cohorts.

### `session_lecturers` (join)
| session_id | lecturer_id | raw_name |

### `session_field_evidence`
| id | session_id | field_name | value | confidence | reason |
Records per-field uncertainty and its cause; drives the admin review queue.

### `import_job`
| id | job_id | version_id | source_document_id | status enum(`queued`,`running`,`succeeded`,`failed`) |
| progress | int | started_at/finished_at | errors jsonb | summary jsonb |

### `validation_issue`
| id | version_id | session_id nullable | code | severity | message | page | resolved_by | resolved_at |

### `publication_record`
| id | version_id | published_by | published_at | action enum(`publish`,`rollback`) | diff_summary jsonb | previous_version_id |

### `admin_user`
| id | email unique | password_hash | role enum(`admin`,`reviewer`,`owner`) | is_active | created_at |

### `audit_event`
| id | actor_id | action | entity_type | entity_id | before jsonb | after jsonb | at | ip |

## 5.2 Example normalised records

Source page 2, cell Tuesday 08:00–09:00:
`Solid Waste Management (CEU 08109) CIVIL / Dr. OBERLIN Aisa / R1-1`

```json
{
  "version": "Semester I — rev 2026-03-10",
  "cohort": "BENG23CE-1",
  "day_of_week": 2,
  "start_time": "08:00",
  "end_time": "09:00",
  "course_name_raw": "Solid Waste Management",
  "course_code_raw": "CEU 08109",
  "department": "CIVIL",
  "lecturer_raw": "Dr. OBERLIN Aisa",
  "venue_raw": "R1-1",
  "session_type": "lecture",
  "extraction_method": "geometry",
  "confidence": "high",
  "source_page": 2,
  "source_text_raw": "Solid Waste Management (CEU\n08109) CIVIL\nDr. OBERLIN Aisa\nR1-1"
}
```

Shared session (p.147):
`OD26CST-1, OD26ERE-1 / Basics of Technical Drawing (MET 04121)(P) Mech / Isaac Sima / ...`

```json
{
  "cohorts": ["OD26CST-1", "OD26ERE-1"],
  "course_name_raw": "Basics of Technical Drawing",
  "course_code_raw": "MET 04121",
  "session_type": "practical",
  "is_shared": true,
  "confidence": "high",
  "source_page": 147
}
```

Missing value is represented explicitly, never guessed:

```json
{ "course_code_raw": null, "confidence": "low",
  "evidence": [{"field": "course_code_raw", "reason": "MISSING_CODE"}] }
```

## 5.3 Comparison / session identity (for version diffs)

Do **not** match sessions by course name alone. Proposed stable identity key:

```
key = hash(day_of_week, start_time, end_time,
           normalised(course_code or normalised(course_name)),
           sorted(cohort_codes))
```

Diff classes: **added**, **removed**, **changed** (any field differs), using field-level comparison.
Normalisation rules: uppercase, collapse whitespace, normalise code spacing, canonicalise time.

## 5.4 Retention & preservation

- Keep every `source_document` (immutable, hash-addressed) and its `publication_record`.
- Keep all versions/sessions; superseded versions remain queryable (archived, not deleted).
- Keep extraction reports and admin corrections; audit events are append-only.
- Define retention duration with DIT (proposal: >= 3 academic years). **[OPEN]**
