"""
RAG Builder usage example for IaC-Gen-DSPy.

This example shows how to build and optimize a RAG knowledge base
for the IaC generation system.
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from iac_gen_dspy.rag.builder import RAGBuilder

def main():
    """RAG builder example."""
    print("IaC-Gen-DSPy RAG Builder Example")
    print("=" * 40)
    
    # Note: This example uses a local LLM (Qwen) for RAG building
    # Make sure you have Ollama running locally with qwen2:7b model
    print("Note: This example requires Ollama with qwen2:7b model running locally")
    print("   Install: ollama pull qwen2:7b")
    print("   Run: ollama serve")
    
    # Initialize RAG builder
    builder = RAGBuilder(
        llm_model="ollama_chat/qwen2:7b",
        api_base="http://localhost:11434"
    )
    
    try:
        # Build complete RAG system
        print("\nBuilding complete RAG system...")
        builder.build_complete_rag_system(
            max_examples_total=25,    # Total examples for optimization
            max_examples_for_kb=15    # Examples to include in knowledge base
        )
        
        print("\nRAG system built successfully!")
        print("Files created:")
        print("  • optimized_metadata_generator.json - Optimized metadata generator")
        print("  • rag_kb.jsonl - Knowledge base with IaC snippets")
        
        # Test the knowledge base
        print("\nTesting the knowledge base...")
        from iac_gen_dspy.rag.store import RAGStore
        
        rag_store = RAGStore("rag_kb.jsonl")
        
        # Test queries
        test_queries = [
            "Create an S3 bucket with versioning",
            "Set up EC2 instance with security group",
            "VPC with public subnet configuration"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            relevant = rag_store.get_relevant_snippets(query)
            if relevant:
                print("Found relevant snippets:")
                print(relevant[:200] + "..." if len(relevant) > 200 else relevant)
            else:
                print("No relevant snippets found")
        
        # Show statistics
        stats = rag_store.get_statistics()
        print(f"\nKnowledge Base Statistics:")
        print(f"  • Total snippets: {stats['total_snippets']}")
        print(f"  • Unique keywords: {stats['unique_keywords']}")
        print(f"  • Average keywords per snippet: {stats['avg_keywords_per_snippet']:.1f}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Make sure qwen2:7b is installed: ollama pull qwen2:7b")
        print("3. Check if port 11434 is accessible")
    
    print("\nRAG builder example completed!")

if __name__ == "__main__":
    main()
