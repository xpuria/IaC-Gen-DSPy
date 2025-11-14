"""
Graph RAG vs keyword RAG comparison example.

This script:
1. Loads both retrieval backends (keyword RAG and Graph RAG).
2. Shows qualitative, side-by-side results for curated prompts.
3. Runs a lightweight evaluation on ~10 prompts and stores metrics.
"""
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence, Set

# Ensure the src package is importable when running from the repo root.
EXAMPLES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXAMPLES_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from iac_gen_dspy.data.utils import load_iac_dataset  # noqa: E402
from iac_gen_dspy.rag import RAGStore, GraphRAGStore  # noqa: E402


def detect_resources(text: str) -> Set[str]:
    """Extract Terraform resource identifiers from text."""
    if not text:
        return set()
    return set(re.findall(r"aws_[a-z0-9_]+", text.lower()))


def keyword_store_retrieve(store: RAGStore, prompt_text: str, top_k: int = 3) -> List[Dict]:
    """Replicate the keyword-based retrieval to obtain structured results."""
    snippets = store.load_snippets()
    prompt_lower = prompt_text.lower()
    matches = []

    for snippet_id, snippet in enumerate(snippets):
        snippet_keywords = [kw.lower() for kw in snippet.get("keywords", []) if isinstance(kw, str)]
        if not snippet_keywords:
            continue
        matched = {kw for kw in snippet_keywords if kw in prompt_lower}
        if not matched:
            continue

        score = len(matched) / max(len(snippet_keywords), 1)
        matches.append(
            {
                "snippet_id": snippet_id,
                "snippet_name": snippet.get("snippet_name", f"Snippet {snippet_id}"),
                "keywords": snippet_keywords,
                "resource_types": sorted(detect_resources(snippet.get("iac_code", ""))),
                "iac_code": snippet.get("iac_code", ""),
                "score": round(score, 4),
            }
        )

    if not matches and snippets:
        # Fallback to the first snippet to avoid empty results in demos.
        first_snippet = snippets[0]
        matches.append(
            {
                "snippet_id": 0,
                "snippet_name": first_snippet.get("snippet_name", "Snippet 0"),
                "keywords": first_snippet.get("keywords", []),
                "resource_types": sorted(detect_resources(first_snippet.get("iac_code", ""))),
                "iac_code": first_snippet.get("iac_code", ""),
                "score": 0.0,
            }
        )

    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[: max(1, top_k)]


def qualitative_demo(prompts: Sequence[str], rag_store: RAGStore, graph_store: GraphRAGStore) -> None:
    """Print side-by-side retrieval outputs for curated prompts."""
    divider = "-" * 72
    for prompt in prompts:
        print(divider)
        print(f"Prompt: {prompt}")
        print(divider)

        keyword_results = keyword_store_retrieve(rag_store, prompt, top_k=2)
        graph_results = graph_store.query(prompt, top_k=2)

        print("\nKeyword RAG Results:")
        for idx, item in enumerate(keyword_results, 1):
            print(f"  {idx}. {item['snippet_name']} (score={item['score']})")

        print("\nGraph RAG Results:")
        for idx, item in enumerate(graph_results, 1):
            print(f"  {idx}. {item['snippet_name']} (score={item['score']})")
        print()


def evaluation_metrics(
    examples: Sequence, rag_store: RAGStore, graph_store: GraphRAGStore, top_k: int = 3
) -> Dict[str, Dict[str, float]]:
    """Compute lightweight comparison metrics for both retrieval strategies."""
    if not examples:
        return {"keyword_rag": {}, "graph_rag": {}}

    def compute_hit(results: List[Dict], target_resources: Set[str]) -> bool:
        if not results:
            return False
        if not target_resources:
            return True
        return any(target_resources & set(item.get("resource_types", [])) for item in results)

    keyword_latencies = []
    graph_latencies = []
    keyword_hits = 0
    graph_hits = 0
    keyword_scores = []
    graph_scores = []
    keyword_snippet_ids = set()
    graph_snippet_ids = set()

    for example in examples:
        prompt = example.prompt
        target_resources = detect_resources(example.expected_iac_code)

        start = time.perf_counter()
        keyword_results = keyword_store_retrieve(rag_store, prompt, top_k=top_k)
        keyword_latencies.append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        graph_results = graph_store.query(prompt, top_k=top_k)
        graph_latencies.append((time.perf_counter() - start) * 1000)

        if compute_hit(keyword_results, target_resources):
            keyword_hits += 1
        if compute_hit(graph_results, target_resources):
            graph_hits += 1

        if keyword_results:
            keyword_scores.append(keyword_results[0]["score"])
            keyword_snippet_ids.add(keyword_results[0]["snippet_id"])
        if graph_results:
            graph_scores.append(graph_results[0]["score"])
            graph_snippet_ids.add(graph_results[0]["snippet_id"])

    total = len(examples)
    return {
        "keyword_rag": {
            "hit_rate": round(keyword_hits / total, 2),
            "avg_latency_ms": round(mean(keyword_latencies), 2),
            "avg_top_score": round(mean(keyword_scores), 3) if keyword_scores else 0.0,
            "unique_snippets_used": len(keyword_snippet_ids),
        },
        "graph_rag": {
            "hit_rate": round(graph_hits / total, 2),
            "avg_latency_ms": round(mean(graph_latencies), 2),
            "avg_top_score": round(mean(graph_scores), 3) if graph_scores else 0.0,
            "unique_snippets_used": len(graph_snippet_ids),
        },
    }


def main() -> None:
    print("IaC-Gen-DSPy Graph RAG Comparison")
    print("=" * 60)

    rag_store = RAGStore()
    graph_store = GraphRAGStore()

    print("\nLoading keyword RAG snippets…")
    rag_store.load_snippets()

    print("Building Graph RAG representation…")
    graph_stats = graph_store.load_graph()
    print(f"Graph stats: {graph_stats}")

    curated_prompts = [
        "Create an S3 bucket with versioning and encryption",
        "Provision an EC2 instance behind a security group",
        "Build a VPC with public and private subnets",
    ]
    qualitative_demo(curated_prompts, rag_store, graph_store)

    print("Sampling evaluation prompts (up to 10)…")
    eval_examples = load_iac_dataset(split="test", max_examples=10)
    metrics = evaluation_metrics(eval_examples, rag_store, graph_store, top_k=3)

    output_path = PROJECT_ROOT / "graph_rag_comparison_results.json"
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump({"metrics": metrics, "graph_stats": graph_stats}, handle, indent=2)

    print("\nComparison Metrics:")
    print(json.dumps(metrics, indent=2))
    print(f"\nMetrics saved to: {output_path}")


if __name__ == "__main__":
    main()

