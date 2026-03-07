# (iii) Graph Store + PPR Baseline

Acest document descrie extensia POC-ului la un pipeline **multi-signal, graph-aware, feedback-driven**, în linie cu cerința de integrare a dependențelor de cod direct în inferență.

## Pipeline țintă (POC -> research system)

```mermaid
flowchart LR
  A[IDE: change detected] --> B[Change summarizer]
  B --> C[Artifact store: JSON schema]
  C --> D1[BM25 index]
  C --> D2[Dense index (FAISS)]
  C --> D3[Graph store (nodes/edges)]
  B --> E[Candidate retrieval: hybrid]
  E --> F[Fusion & confidence engine]
  F --> G[Graph propagation (PPR/RW) optional]
  G --> H[LLM/RAG re-ranker + verifier]
  H --> I[Factorized explanations + JSON report]
  I --> J[Human-in-the-loop feedback]
  J --> C
```

## Model de graf (MVP)

### Noduri
- `story`
- `code_entity`
- `test_case`
- `defect`
- `commit` (opțional)
- `issue` (opțional)

### Muchii + clase de link-uri

În versiunea curentă, graful modelează **două clase de muchii**:

1. **Explicit links** (academically auditable):
   - muchii din `embeddings/edges.json` (dacă există), plus
   - muchii construite din referințe explicite: story IDs (`US-*`), test IDs (`TC-*`), issue/bug IDs (`BUG-*`/`ISSUE-*`), file paths, commit mentions.
2. **Inferred links**:
   - muchii inferate din similaritate semantică embedding-to-embedding (top-k neighbors),
   - utilizate în propagare (PPR).

Se expune și un mod **combined** = `explicit ∪ inferred`.

## Ce s-a introdus în cod

- `src/graph_store.py`: graph store in-memory cu:
  - adiacențe separate: `explicit`, `inferred`, `combined`;
  - inferență explicită din IDs/paths/mentions;
  - inferență semantică din embeddings (top-k similaritate);
  - propagare `personalized_pagerank` cu `link_mode` (`explicit` / `inferred` / `combined`).
- `src/agents.py` folosește acum:
  - BM25 lexical;
  - dense FAISS;
  - scor structural PPR din graph store pe `link_mode` configurabil;
  - explicații factorized care includ explicit metoda `personalized_pagerank[mode]`.
- `src/evaluate_link_modes.py`:
  - benchmark simplu care raportează separat:
    - `explicit-only performance`
    - `inferred-only performance`
    - `combined performance`
  - metrici: precision@10, recall@10, F1@10.

## Cum rulezi evaluarea pe moduri

```bash
python -m src.evaluate_link_modes
```

Output-ul include cele trei rezultate separate (`explicit`, `inferred`, `combined`) pentru comparabilitate academică.

## Observații baseline

- PPR e folosit ca **baseline structural** (rapid, explicabil).
- Distincția explicit/inferred crește credibilitatea experimentală, deoarece separă semnalele observabile direct de cele obținute prin generalizare semantică/propagare.
- Dacă nu există graf explicit, fallback-ul menține pipeline-ul funcțional.
- Structura pregătește integrarea ulterioară cu reranker LLM/RAG și feedback loops.
