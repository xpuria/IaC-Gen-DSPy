"""
Graph-based Retrieval Augmented Generation store.

Builds an in-memory heterogeneous graph that links IaC snippets to their
keywords and detected resource types, enabling richer retrieval than
simple keyword matching alone.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set

# Common stopwords to filter out from keyword extraction
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "will", "with", "this", "these", "those", "have",
    "can", "could", "should", "would", "may", "might", "must",
    "create", "using", "use", "set", "get", "make", "do", "does",
    "did", "done", "your", "my", "our", "their", "his", "her",
}


@dataclass
class GraphSnippet:
    """Metadata tracked for each snippet node."""

    snippet_id: int
    snippet_name: str
    keywords: Set[str]
    resource_types: Set[str]
    iac_code: str
    original_prompt: str


class GraphRAGStore:
    """
    Graph-based RAG store that augments keyword retrieval with resource-aware
    reasoning over a heterogeneous graph (snippets, keywords, resources).
    """

    def __init__(self, kb_file: str = "rag_kb.jsonl"):
        self.kb_file = kb_file
        self._graph_built = False
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._snippet_data: Dict[int, GraphSnippet] = {}
        self._keyword_to_snippets: Dict[str, Set[int]] = defaultdict(set)
        self._resource_to_snippets: Dict[str, Set[int]] = defaultdict(set)
        self._stats: Dict[str, Any] = {}
        self._resource_pattern = re.compile(r'resource\s+"(?P<type>[^"]+)"', re.IGNORECASE)
        # Updated pattern to keep underscores as part of tokens (for technical terms)
        # But also extract individual words from hyphenated or compound terms
        self._token_pattern = re.compile(r"[a-zA-Z0-9]+(?:_[a-zA-Z0-9]+)*")


    def load_graph(self) -> Dict[str, Any]:
        """
        Load snippets from the KB file and construct the graph.

        Returns:
            Dict[str, Any]: Basic statistics about the constructed graph.
        """
        if self._graph_built:
            return self._stats

        if not os.path.exists(self.kb_file):
            raise FileNotFoundError(
                f"RAG knowledge base '{self.kb_file}' not found. "
                "Run the RAG builder first to create it."
            )

        snippet_count = 0
        keyword_nodes = set()
        resource_nodes = set()

        with open(self.kb_file, "r", encoding="utf-8") as handle:
            for line in handle:
                snippet = json.loads(line)
                # Expand keywords to include both full terms and their components
                raw_keywords = {kw.strip().lower() for kw in snippet.get("keywords", []) if kw}
                keywords = set()
                for kw in raw_keywords:
                    keywords.add(kw)
                    # Add components of underscore-separated terms
                    if '_' in kw:
                        components = kw.split('_')
                        for comp in components:
                            if len(comp) > 2 and comp not in STOPWORDS:
                                keywords.add(comp)
                resource_types = self._extract_resource_types(snippet.get("iac_code", ""))

                graph_snippet = GraphSnippet(
                    snippet_id=snippet_count,
                    snippet_name=snippet.get("snippet_name", f"Snippet {snippet_count}"),
                    keywords=keywords,
                    resource_types=resource_types,
                    iac_code=snippet.get("iac_code", ""),
                    original_prompt=snippet.get("original_prompt", ""),
                )
                self._snippet_data[snippet_count] = graph_snippet

                snippet_node = self._snippet_node(snippet_count)

                for keyword in keywords:
                    keyword_nodes.add(keyword)
                    keyword_node = self._keyword_node(keyword)
                    self._graph[snippet_node].add(keyword_node)
                    self._graph[keyword_node].add(snippet_node)
                    self._keyword_to_snippets[keyword].add(snippet_count)

                for resource in resource_types:
                    resource_nodes.add(resource)
                    resource_node = self._resource_node(resource)
                    self._graph[snippet_node].add(resource_node)
                    self._graph[resource_node].add(snippet_node)
                    self._resource_to_snippets[resource].add(snippet_count)

                snippet_count += 1

        edge_count = sum(len(neighbors) for neighbors in self._graph.values()) // 2
        avg_degree = (
            sum(len(self._graph[self._snippet_node(idx)]) for idx in self._snippet_data)
            / snippet_count
            if snippet_count
            else 0.0
        )

        self._stats = {
            "snippets": snippet_count,
            "keywords": len(keyword_nodes),
            "resource_types": len(resource_nodes),
            "edges": edge_count,
            "avg_snippet_degree": round(avg_degree, 2),
        }
        self._graph_built = True
        return self._stats


    def query(self, prompt_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant snippets for the given prompt.

        Args:
            prompt_text: Natural language description of the desired IaC.
            top_k: Number of snippets to return.

        Returns:
            List[Dict[str, Any]]: Ranked snippets with metadata and scores.
        """
        if not self._graph_built:
            self.load_graph()

        prompt_keywords = self._extract_prompt_keywords(prompt_text)
        prompt_resources = self._detect_prompt_resources(prompt_text)

        candidate_snippets = set()
        for keyword in prompt_keywords:
            candidate_snippets.update(self._keyword_to_snippets.get(keyword, set()))
        for resource in prompt_resources:
            candidate_snippets.update(self._resource_to_snippets.get(resource, set()))

        if not candidate_snippets:
            candidate_snippets = set(self._snippet_data.keys())

        ranked = []
        for snippet_id in candidate_snippets:
            snippet = self._snippet_data[snippet_id]
            
            # Use Jaccard similarity for better scoring
            kw_jaccard = self._jaccard_similarity(snippet.keywords, prompt_keywords)
            resource_jaccard = self._jaccard_similarity(snippet.resource_types, prompt_resources)
            
            # Original overlap scores (recall-based)
            kw_overlap = self._overlap_score(snippet.keywords, prompt_keywords)
            resource_overlap = self._overlap_score(snippet.resource_types, prompt_resources)
            
            # Connectivity bonus
            connectivity = self._connectivity_score(snippet_id, prompt_keywords, prompt_resources)
            
            # Weighted scoring that balances precision (Jaccard) and recall (overlap)
            # Keywords are more important (0.5), resources secondary (0.3), connectivity tertiary (0.2)
            keyword_score = 0.6 * kw_jaccard + 0.4 * kw_overlap
            resource_score = 0.7 * resource_jaccard + 0.3 * resource_overlap
            
            total_score = (0.5 * keyword_score) + (0.3 * resource_score) + (0.2 * connectivity)

            ranked.append(
                {
                    "snippet_id": snippet_id,
                    "snippet_name": snippet.snippet_name,
                    "score": round(total_score, 4),
                    "keywords": sorted(snippet.keywords),
                    "resource_types": sorted(snippet.resource_types),
                    "iac_code": snippet.iac_code,
                    "original_prompt": snippet.original_prompt,
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[: max(1, top_k)]

    def get_statistics(self) -> Dict[str, Any]:
        """Return cached graph statistics (builds the graph if needed)."""
        if not self._graph_built:
            self.load_graph()
        return self._stats


    def _snippet_node(self, snippet_id: int) -> str:
        return f"s:{snippet_id}"

    def _keyword_node(self, keyword: str) -> str:
        return f"k:{keyword}"

    def _resource_node(self, resource: str) -> str:
        return f"r:{resource}"

    def _extract_resource_types(self, iac_code: str) -> Set[str]:
        resources = set()
        for match in self._resource_pattern.findall(iac_code or ""):
            resources.add(match.strip().lower())
        return resources

    def _extract_prompt_keywords(self, prompt_text: str) -> Set[str]:
        """
        Extract meaningful keywords from prompt, filtering stopwords.
        Extracts both full underscore-separated terms and their components.
        """
        tokens = set()
        
        # Extract full tokens (including underscores)
        for token in self._token_pattern.findall(prompt_text):
            token_lower = token.lower()
            if len(token_lower) > 2 and token_lower not in STOPWORDS:
                tokens.add(token_lower)
                
                # Also add individual components if token contains underscores
                if '_' in token_lower:
                    components = token_lower.split('_')
                    for comp in components:
                        if len(comp) > 2 and comp not in STOPWORDS:
                            tokens.add(comp)
        
        return tokens

    def _detect_prompt_resources(self, prompt_text: str) -> Set[str]:
        """Detect AWS resources from prompt using patterns and service name mapping."""
        prompt_lower = prompt_text.lower()
        explicit_resources = set(re.findall(r"aws_[a-z0-9_]+", prompt_lower))

        # Enhanced heuristic mapping common service names to resource tokens
        service_map = {
            "s3": "aws_s3_bucket",
            "bucket": "aws_s3_bucket",
            "ec2": "aws_instance",
            "instance": "aws_instance",
            "vpc": "aws_vpc",
            "subnet": "aws_subnet",
            "lambda": "aws_lambda_function",
            "function": "aws_lambda_function",
            "iam": "aws_iam_role",
            "role": "aws_iam_role",
            "policy": "aws_iam_policy",
            "dynamodb": "aws_dynamodb_table",
            "table": "aws_dynamodb_table",
            "rds": "aws_db_instance",
            "database": "aws_db_instance",
            "security group": "aws_security_group",
            "sg": "aws_security_group",
            "load balancer": "aws_lb",
            "alb": "aws_lb",
            "elb": "aws_elb",
            "route53": "aws_route53_zone",
            "dns": "aws_route53_zone",
            "cloudwatch": "aws_cloudwatch_log_group",
            "sns": "aws_sns_topic",
            "sqs": "aws_sqs_queue",
            "queue": "aws_sqs_queue",
            "elasticbeanstalk": "aws_elastic_beanstalk_environment",
            "beanstalk": "aws_elastic_beanstalk_environment",
            "ecs": "aws_ecs_cluster",
            "fargate": "aws_ecs_service",
            "eks": "aws_eks_cluster",
            "kubernetes": "aws_eks_cluster",
        }
        
        # Use word boundaries to avoid partial matches
        for term, resource in service_map.items():
            # Check if term appears as a standalone word or in common phrases
            if re.search(r'\b' + re.escape(term) + r'\b', prompt_lower):
                explicit_resources.add(resource)
        
        return explicit_resources

    def _jaccard_similarity(self, snippet_items: Set[str], prompt_items: Set[str]) -> float:
        """
        Calculate Jaccard similarity (intersection over union).
        This penalizes snippets with many irrelevant items.
        """
        if not snippet_items or not prompt_items:
            return 0.0
        intersection = len(snippet_items & prompt_items)
        union = len(snippet_items | prompt_items)
        return intersection / union if union > 0 else 0.0
    
    def _overlap_score(self, snippet_items: Set[str], prompt_items: Set[str]) -> float:
        """
        Calculate recall-based overlap score (intersection over prompt items).
        This measures how much of the prompt is covered.
        """
        if not snippet_items or not prompt_items:
            return 0.0
        return len(snippet_items & prompt_items) / len(prompt_items)

    def _connectivity_score(
        self, snippet_id: int, prompt_keywords: Set[str], prompt_resources: Set[str]
    ) -> float:
        """
        Calculate connectivity score based on graph structure.
        Returns the ratio of matched neighbors to total requested items.
        """
        snippet_node = self._snippet_node(snippet_id)
        neighbors = self._graph.get(snippet_node, set())
        if not neighbors:
            return 0.0

        matched_neighbors = 0
        total_requested = len(prompt_keywords) + len(prompt_resources)
        
        if total_requested == 0:
            return 0.0
        
        for keyword in prompt_keywords:
            if self._keyword_node(keyword) in neighbors:
                matched_neighbors += 1
        for resource in prompt_resources:
            if self._resource_node(resource) in neighbors:
                matched_neighbors += 1

        # Normalize by the number of items we're looking for, not total neighbors
        # This gives credit for matching relevant connections
        return matched_neighbors / total_requested