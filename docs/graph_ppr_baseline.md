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

### Muchii
- `story -> code_entity`
- `story -> test_case`
- `defect -> code_entity`
- `defect -> test_case`
- `code_entity -> test_case`
- `commit -> code_entity`
- `issue -> commit`

În MVP-ul implementat aici, muchiile sunt:
1. încărcate din `embeddings/edges.json` dacă fișierul există;
2. altfel inferate din referințe comune la story-uri (ex: `US-01`) din text/ID.

## Ce s-a introdus în cod

- `src/graph_store.py`: graph store in-memory cu:
  - încărcare edges JSON;
  - inferență fallback pentru muchii;
  - propagare `personalized_pagerank` (PPR).
- `src/agents.py` folosește acum:
  - BM25 lexical;
  - dense FAISS;
  - scor structural PPR din graph store;
  - fuziune cu explicații factorized care includ metoda `personalized_pagerank`.

## Observații baseline

- PPR e folosit ca **baseline structural** (rapid, explicabil).
- Dacă nu există graf explicit, fallback-ul menține pipeline-ul funcțional.
- Structura pregătește integrarea ulterioară cu reranker LLM/RAG și feedback loops.
