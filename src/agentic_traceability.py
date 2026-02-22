import csv
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


from src.agents import search


CODE_DIR_NAMES = {"code", "src"}
CODE_EXTENSIONS = {".java"}
STORY_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@dataclass
class ToolContext:
    dataset: str | None = None


class BaseTool:
    def run(self, *args, **kwargs):
        raise NotImplementedError


class DatasetResolverTool(BaseTool):
    def run(self, filename: str) -> str | None:
        parts = PurePosixPath(filename).parts
        if not parts:
            return None
        root = parts[0]
        return root if root.startswith("traceability_") else None


class GitDiffTool(BaseTool):
    def run(self, commit_payload: dict[str, Any]) -> list[dict[str, Any]]:
        return commit_payload.get("files", [])


class JavaSymbolExtractorTool(BaseTool):
    _class_pattern = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")
    _method_pattern = re.compile(
        r"\b(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )

    def run(self, patch_text: str) -> dict[str, list[str]]:
        classes = self._class_pattern.findall(patch_text or "")
        methods = [m for m in self._method_pattern.findall(patch_text or "") if m not in {"if", "for", "while", "switch"}]
        return {"classes": sorted(set(classes)), "methods": sorted(set(methods))}


class StoryDeltaTool(BaseTool):
    def run(self, file_change: dict[str, Any]) -> list[dict[str, str]]:
        filename = file_change.get("filename", "")
        patch_text = file_change.get("patch", "") or ""
        ext = PurePosixPath(filename).suffix.lower()
        if ext == ".csv":
            return self._from_csv_patch(patch_text)
        if ext in {".xlsx", ".xls"}:
            return self._from_sheet_paths(file_change)
        return []

    def _from_csv_patch(self, patch_text: str) -> list[dict[str, str]]:
        changed: list[dict[str, str]] = []
        for line in patch_text.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            content = line[1:].strip()
            if not content:
                continue
            row = next(csv.reader([content]), None)
            if not row:
                continue
            row = [c.strip() for c in row]
            if len(row) >= 2:
                changed.append({"id": row[0], "text": row[1]})
            elif row:
                changed.append({"id": str(len(changed) + 1), "text": row[0]})
        return changed

    def _from_sheet_paths(self, file_change: dict[str, Any]) -> list[dict[str, str]]:
        previous_path = file_change.get("previous_local_path")
        current_path = file_change.get("current_local_path")
        if not previous_path or not current_path:
            return []
        if not (Path(previous_path).exists() and Path(current_path).exists()):
            return []

        try:
            import pandas as pd
        except ModuleNotFoundError:
            return []

        prev_df = pd.read_excel(previous_path)
        curr_df = pd.read_excel(current_path)

        text_col = self._find_col(curr_df.columns, ["feature_sentence", "story", "text"])
        id_col = self._find_col(curr_df.columns, ["user_story_id", "id", "story_id"])
        if not text_col:
            return []

        prev_records = {(str(r.get(id_col, i)) if id_col else str(i)): str(r.get(text_col, "")) for i, r in prev_df.iterrows()}
        changed = []
        for i, row in curr_df.iterrows():
            sid = str(row.get(id_col, i)) if id_col else str(i)
            text = str(row.get(text_col, ""))
            if prev_records.get(sid) != text:
                changed.append({"id": sid, "text": text})
        return changed

    @staticmethod
    def _find_col(columns: Any, aliases: list[str]) -> str | None:
        normalized = {str(c).strip().lower(): c for c in columns}
        for a in aliases:
            if a.lower() in normalized:
                return normalized[a.lower()]
        return None


class ArtifactRetrieverTool(BaseTool):
    def run(self, query: str, dataset: str | None, k: int = 10, mode: str = "embedding") -> list[dict[str, Any]]:
        if mode == "embedding":
            results = search(query, k=k, dataset=dataset)
            return results
        return self._bm25_fallback(query, dataset=dataset, k=k)

    def _bm25_fallback(self, query: str, dataset: str | None, k: int = 10) -> list[dict[str, Any]]:
        # lightweight fallback built on indexed metadata only
        corpus = search("traceability", k=500, dataset=dataset)
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return corpus[:k]

        doc_tokens = [self._tokenize((r.get("text") or "") + " " + (r.get("id") or "")) for r in corpus]
        avgdl = sum(len(t) for t in doc_tokens) / max(len(doc_tokens), 1)
        df = Counter(t for toks in doc_tokens for t in set(toks))

        scores = []
        for record, toks in zip(corpus, doc_tokens):
            score = 0.0
            freqs = Counter(toks)
            for t in q_tokens:
                if t not in df:
                    continue
                idf = math.log((len(corpus) - df[t] + 0.5) / (df[t] + 0.5) + 1)
                tf = freqs[t]
                denom = tf + 1.5 * (1 - 0.75 + 0.75 * len(toks) / max(avgdl, 1))
                score += idf * ((tf * (1.5 + 1)) / max(denom, 1e-9))
            if score > 0:
                scores.append((score, record))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scores[:k]]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", (text or "").lower())


class GraphPropagatorTool(BaseTool):
    def run(self, dataset: str | None, retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Hook for a future dependency-graph expansion step.
        # If graph image exists, keep a marker for report transparency.
        graph_exists = False
        if dataset and Path(dataset).exists():
            graph_exists = any(p.suffix == ".png" and "dependency" in p.name for p in Path(dataset).glob("*.png"))
        if graph_exists:
            return retrieved + [{"type": "note", "id": "graph", "text": "dependency graph detected (propagation stubbed)"}]
        return retrieved


class RerankerTool(BaseTool):
    def run(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        q = set(ArtifactRetrieverTool._tokenize(query))

        def score(record: dict[str, Any]) -> float:
            text = f"{record.get('id', '')} {record.get('text', '')}"
            tokens = set(ArtifactRetrieverTool._tokenize(text))
            overlap = len(q & tokens)
            type_bonus = {"story": 0.8, "test_case": 0.7, "fault": 0.6, "code": 0.5}.get(record.get("type"), 0.1)
            return overlap + type_bonus

        return sorted(results, key=score, reverse=True)


class VerifierTool(BaseTool):
    def run(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        ids = [f"{r.get('type')}::{r.get('id')}" for r in results]
        unique = len(set(ids))
        total = len(ids)
        duplicate_ratio = 0.0 if total == 0 else (total - unique) / total
        has_evidence = any(r.get("type") in {"test_case", "fault", "code"} for r in results)
        return {
            "ok": duplicate_ratio < 0.4 and has_evidence,
            "duplicate_ratio": round(duplicate_ratio, 3),
            "has_evidence": has_evidence,
        }


class MemoryStore(BaseTool):
    def __init__(self, base_dir: str = ".agent_memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, dataset: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", dataset)
        return self.base_dir / f"{safe}.json"

    def run(self, dataset: str) -> dict[str, Any]:
        path = self._path(dataset)
        if not path.exists():
            return {"runs": 0, "avg_confidence": 0.5, "temperature": 1.0}
        return json.loads(path.read_text())

    def save(self, dataset: str, confidence: float) -> None:
        state = self.run(dataset)
        runs = state.get("runs", 0) + 1
        avg = ((state.get("avg_confidence", 0.5) * state.get("runs", 0)) + confidence) / runs
        # simple temperature update: lower temp if model tends to be overconfident
        temperature = max(0.7, min(1.5, 1.0 + (avg - 0.7)))
        path = self._path(dataset)
        path.write_text(json.dumps({"runs": runs, "avg_confidence": avg, "temperature": temperature}, indent=2))


class ReportComposerTool(BaseTool):
    def run(
        self,
        sha: str,
        dataset: str,
        trigger_type: str,
        query: str,
        results: list[dict[str, Any]],
        confidence: float,
        verifier: dict[str, Any],
        reflections: list[str],
    ) -> dict[str, Any]:
        return {
            "sha": sha,
            "dataset": dataset,
            "trigger_type": trigger_type,
            "query": query,
            "confidence": round(confidence, 3),
            "verification": verifier,
            "reflections": reflections,
            "evidence": results[:20],
        }


class Planner:
    def run(self, trigger_type: str, has_symbols: bool) -> dict[str, Any]:
        if trigger_type == "code_class_modified":
            return {"mode": "embedding", "k": 12, "expand_with_symbols": has_symbols}
        return {"mode": "embedding", "k": 10, "expand_with_symbols": False}


class AgenticTraceabilityEngine:
    def __init__(self):
        self.dataset_resolver = DatasetResolverTool()
        self.git_diff = GitDiffTool()
        self.symbols = JavaSymbolExtractorTool()
        self.story_delta = StoryDeltaTool()
        self.retriever = ArtifactRetrieverTool()
        self.graph = GraphPropagatorTool()
        self.reranker = RerankerTool()
        self.verifier = VerifierTool()
        self.memory = MemoryStore()
        self.reporter = ReportComposerTool()
        self.planner = Planner()

    def analyze_commit(self, commit_payload: dict[str, Any]) -> dict[str, Any]:
        sha = commit_payload.get("sha", "unknown")
        reports = []
        for file_change in self.git_diff.run(commit_payload):
            filename = file_change.get("filename", "")
            dataset = self.dataset_resolver.run(filename)
            if not dataset:
                continue

            ext = PurePosixPath(filename).suffix.lower()
            is_code = ext in CODE_EXTENSIONS and any(p in CODE_DIR_NAMES for p in PurePosixPath(filename).parts)
            is_story = ext in STORY_EXTENSIONS and ("story" in filename.lower() or "stories" in filename.lower())
            if not (is_code or is_story):
                continue

            trigger = "code_class_modified" if is_code else "user_story_modified"
            symbols = self.symbols.run(file_change.get("patch", "")) if is_code else {"classes": [], "methods": []}
            changed_stories = self.story_delta.run(file_change) if is_story else []

            base_query = file_change.get("patch", "") if is_code else " ".join(s["text"] for s in changed_stories)
            plan = self.planner.run(trigger, has_symbols=bool(symbols["classes"] or symbols["methods"]))
            if plan["expand_with_symbols"]:
                base_query = f"{base_query}\nclasses: {' '.join(symbols['classes'])}\nmethods: {' '.join(symbols['methods'])}\nfile:{filename}"

            retrieval_mode = plan["mode"]
            k = plan["k"]
            results = self.retriever.run(base_query, dataset=dataset, k=k, mode=retrieval_mode)
            results = self.graph.run(dataset, results)
            results = self.reranker.run(base_query, results)
            verifier_result = self.verifier.run(results)

            mem = self.memory.run(dataset)
            base_conf = min(0.95, 0.35 + 0.04 * len(results))
            calibrated = max(0.05, min(0.99, base_conf / mem.get("temperature", 1.0)))

            reflections: list[str] = []
            if calibrated < 0.65 or not verifier_result["ok"]:
                reflections.append("Low confidence/inconsistency detected; running one refinement loop.")
                expanded = f"{base_query}\nfilename:{filename}\nsymbols:{' '.join(symbols['classes'] + symbols['methods'])}"
                retrieval_mode = "bm25" if retrieval_mode == "embedding" else "embedding"
                k += 8
                results = self.retriever.run(expanded, dataset=dataset, k=k, mode=retrieval_mode)
                results = self.reranker.run(expanded, results)
                verifier_result = self.verifier.run(results)
                calibrated = max(calibrated, min(0.99, (0.4 + 0.03 * len(results)) / mem.get("temperature", 1.0)))
                reflections.append(f"Refinement used mode={retrieval_mode}, k={k}, and re-verification.")

            self.memory.save(dataset, calibrated)
            reports.append(
                self.reporter.run(
                    sha=sha,
                    dataset=dataset,
                    trigger_type=trigger,
                    query=base_query[:1200],
                    results=results,
                    confidence=calibrated,
                    verifier=verifier_result,
                    reflections=reflections,
                )
            )

        return {"sha": sha, "reports": reports}
