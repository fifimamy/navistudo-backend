# Frontend Payload — Status and Assumptions

> **IMPORTANT — READ FIRST**
>
> The file `frontend_payload_sample.json` in this directory is a
> **RECONSTRUCTED fixture**, not Faouzi's original file. Faouzi's
> `docs/frontend_payload_sample.json` was **not present** in the repository
> when this work was performed.
>
> The reconstruction is based only on the field names described in the task:
> `student_profile`, `interests`, `future_direction`, `problem_preferences`,
> `current_stage_id`, and `subject_performance` with `min_score` / `max_score`.
>
> **Every mapping in this reconstruction must be confirmed with the frontend
> team before production use.** Once the real file is available, replace
> `frontend_payload_sample.json` and re-run the payload tests.

## What the backend does with unknown fields

The backend schema is intentionally permissive (`extra="allow"`). Unknown
frontend fields are **preserved** in the persisted `questionnaire` document and
are **not** silently dropped. This means a payload with extra fields will not
be rejected.

## Documented mapping decisions (require confirmation)

| Frontend field | Backend field | Rule | Status |
|---|---|---|---|
| `student_profile.current_stage_id` | `school_year` | See `STAGE_ID_TO_SCHOOL_YEAR` | **Needs confirmation** |
| `student_profile.subject_performance[].max_score` | `grades[subject_id]` | Upper bound of the range | **Needs confirmation** |
| `student_profile.subject_performance[].min_score` | `subject_performance[].min_score` | Preserved as-is | **Needs confirmation** |
| `student_profile.wilaya_code` | `wilaya` | Code preserved | **Needs confirmation** |
| `interests.*`, `future_direction.*`, `problem_preferences.*` | `free_text_answers` | Flattened to text for Model 1 | **Needs confirmation** |

## Subject ID normalization

The knowledge base uses subject codes such as `mathematiques`,
`physique_chimie`, `svt`, `francais`. The frontend may send different subject
IDs (e.g. `mathematics`, `physics`). **No automatic normalization is applied**,
because inventing a mapping could corrupt eligibility filtering. The raw
`subject_id` is preserved and the mapping must be agreed with the frontend
and data teams.

## Malformed key note

The task mentioned an apparent malformed key near `abstract_concrete_preference`.
The reconstructed file contains the corrected key
`"abstract_concrete_preference"`. A separate malformed test fixture is kept in
`tests/fixtures/frontend_payload_malformed.json` to verify the validator
reports malformed JSON rather than crashing.

## How to validate the real file

```powershell
python -c "import json; json.load(open('docs/frontend_payload_sample.json', encoding='utf-8')); print('valid JSON')"
python -m pytest tests/test_frontend_payload.py -v
```
