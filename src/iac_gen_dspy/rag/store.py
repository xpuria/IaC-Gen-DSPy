"""
RAG Store implementation for IaC code snippets.
"""
import json
import os
from typing import List, Dict, Any

class RAGStore:
    """
    Retrieval Augmented Generation store for IaC code snippets.
    
    This class manages a knowledge base of IaC code snippets with associated
    keywords and metadata, enabling retrieval of relevant examples during generation.
    """
    
    def __init__(self, kb_file: str = "rag_kb.jsonl"):
        self.kb_file = kb_file
        self._snippets_cache = None
        
    def load_snippets(self) -> List[Dict[str, Any]]:
        """
        Load RAG snippets from the knowledge base file.
        
        Returns:
            List[Dict[str, Any]]: List of snippet dictionaries
        """
        if self._snippets_cache is not None:
            return self._snippets_cache

        snippets = []
        if not os.path.exists(self.kb_file):
            print(f"Warning: RAG knowledge base file '{self.kb_file}' not found.")
            print("Please run the RAG builder first to generate it.")
            print("Falling back to a minimal hardcoded list for now.")
            self._snippets_cache = [ 
                {
                    "keywords": ["ec2", "instance"], 
                    "snippet_name": "Fallback EC2 Example",
                    "iac_code": 'resource "aws_instance" "fallback" {\n  ami = "ami-0abcdef1234567890"\n  instance_type = "t2.micro"\n}'
                }
            ]
            return self._snippets_cache
            
        with open(self.kb_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    snippets.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON line {line_num} in '{self.kb_file}': {line.strip()}")
        
        if not snippets:
            print(f"Warning: No snippets loaded from '{self.kb_file}', even though it exists.")
        else:
            print(f"Loaded {len(snippets)} RAG snippets from '{self.kb_file}'.")
        
        self._snippets_cache = snippets
        return snippets

    def get_relevant_snippets(self, prompt_text: str, generated_code: str = "") -> str:
        """
        Get relevant IaC snippets based on prompt and optionally generated code.
        
        Args:
            prompt_text (str): User's natural language prompt
            generated_code (str): Previously generated code (for retry scenarios)
            
        Returns:
            str: Formatted relevant snippets or empty string if none found
        """
        all_snippets = self.load_snippets()
        if not all_snippets:
            return ""

        relevant_snippets_data = []
        prompt_lower = prompt_text.lower()
        code_lower = generated_code.lower() if generated_code else ""

        for item in all_snippets:
            item_keywords = item.get("keywords", [])
            if not isinstance(item_keywords, list): 
                item_keywords = []

            prompt_match = any(keyword.lower() in prompt_lower for keyword in item_keywords)
            code_match = any(keyword.lower() in code_lower for keyword in item_keywords) if code_lower else False
            
            if prompt_match or code_match:
                relevant_snippets_data.append(
                    f"# Reference: {item.get('snippet_name', 'Untitled Snippet')}\n{item.get('iac_code', '')}"
                )

        if not relevant_snippets_data:
            return "" 
        return "\n\n---\nRelevant IaC Reference Snippets:\n" + "\n\n".join(relevant_snippets_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG knowledge base.
        
        Returns:
            Dict[str, Any]: Statistics including total snippets, unique keywords, etc.
        """
        snippets = self.load_snippets()
        if not snippets:
            return {"total_snippets": 0, "unique_keywords": 0, "avg_keywords_per_snippet": 0}
            
        all_keywords = set()
        keyword_counts = []
        
        for snippet in snippets:
            keywords = snippet.get("keywords", [])
            if isinstance(keywords, list):
                all_keywords.update(kw.lower() for kw in keywords)
                keyword_counts.append(len(keywords))
                
        return {
            "total_snippets": len(snippets),
            "unique_keywords": len(all_keywords),
            "avg_keywords_per_snippet": sum(keyword_counts) / len(keyword_counts) if keyword_counts else 0,
            "most_common_keywords": list(all_keywords)[:10]  # Top 10 for brevity
        }
