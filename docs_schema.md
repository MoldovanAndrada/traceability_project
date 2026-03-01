# Canonical traceability JSON schema (MVP)

Acest proiect folosește două colecții JSONL:

- `artifacts.jsonl`
- `edges.jsonl`

## Structură artifact

Câmpuri principale:

- `artifact_id` (ID stabil, format de tip `prefix:value`, ex. `story:S1`, `tc:TC12`, `commit:abc1234`)
- `type` ∈ `{story, acceptance_criteria, test_case, code_entity, defect, commit, issue, doc}`
- `dataset_id`
- `title`, `text`, `lang` (`ro/en`), `tokens`
- `source` ∈ `{CSV, XLSX, GitHub, Defects4J}`
- opțional: `source_uri`, `version {commit_sha, timestamp, branch}`, `metadata`

## Structură edge

Câmpuri principale:

- `edge_id`, `src_id`, `dst_id`
- `edge_type` ∈ `{implements, verifies, fails_on, fixes, mentions, touches, calls, imports, cochanges, related_to}`
- `label` ∈ `{pos, neg, unknown}`
- `evidence`: listă de obiecte `{kind, payload_ref, score_component}`
- `split` ∈ `{train, dev, test}`
- `provenance`: `{method, annotator, date}`

## Validare

Validatorul este în `src/schema_validator.py` și folosește JSON Schema Draft 2020-12.

Exemplu:

```bash
python -m src.schema_validator \
  --artifacts data/artifacts.jsonl \
  --edges data/edges.jsonl
```
