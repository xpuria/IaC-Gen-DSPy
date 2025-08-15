"""
Advanced usage example for IaC-Gen-DSPy.

This example demonstrates advanced features including custom evaluation,
detailed metrics analysis, and RAG system usage.
"""
import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from iac_gen_dspy.core.workflow import IaCWorkflow
from iac_gen_dspy.metrics.evaluator import MetricsEvaluator
from iac_gen_dspy.rag.store import RAGStore
from iac_gen_dspy.data.utils import load_iac_dataset, DatasetProcessor

def main():
    """Advanced usage example with comprehensive analysis."""
    print("IaC-Gen-DSPy Advanced Usage Example")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        return
    
    # 1. Dataset Analysis
    print("\nAnalyzing Dataset...")
    examples = load_iac_dataset(split="test", max_examples=30)
    processor = DatasetProcessor()
    analysis = processor.analyze_dataset(examples)
    
    print(f"Dataset Statistics:")
    print(f"  • Total Examples: {analysis['total_examples']}")
    print(f"  • Avg Prompt Length: {analysis['avg_prompt_length_words']} words")
    print(f"  • Avg Code Length: {analysis['avg_code_length_lines']} lines")
    print(f"  • Unique Resource Types: {analysis['unique_resource_types']}")
    print(f"  • Common Resources: {', '.join([r[0] for r in analysis['common_resource_types'][:3]])}")
    
    # 2. RAG System Analysis
    print("\nAnalyzing RAG System...")
    rag_store = RAGStore()
    rag_stats = rag_store.get_statistics()
    
    print(f"RAG Knowledge Base:")
    print(f"  • Total Snippets: {rag_stats['total_snippets']}")
    print(f"  • Unique Keywords: {rag_stats['unique_keywords']}")
    print(f"  • Avg Keywords/Snippet: {rag_stats['avg_keywords_per_snippet']:.1f}")
    
    # 3. Comprehensive Workflow with Evaluation
    print("\nSetting up Advanced Workflow...")
    workflow = IaCWorkflow(api_key=api_key)
    workflow.load_and_prepare_data(total_examples=25)
    
    # Test different configurations
    configurations = [
        {"name": "Standard", "retries": 1, "rag": True},
        {"name": "High-Retry", "retries": 3, "rag": True},
        {"name": "No-RAG", "retries": 1, "rag": False}
    ]
    
    results_comparison = {}
    evaluator = MetricsEvaluator()
    
    for config in configurations:
        print(f"\nTesting Configuration: {config['name']}")
        
        workflow.optimize_generator(
            max_retries=config["retries"], 
            use_rag=config["rag"], 
            use_terraform_cli=True
        )
        
        # Evaluate on a small test set
        test_examples = workflow.dev_examples[:5] if workflow.dev_examples else []
        if test_examples:
            results = evaluator.evaluate_generator(
                workflow.optimized_generator, 
                test_examples, 
                detailed=True
            )
            
            results_comparison[config["name"]] = {
                "config": config,
                "success_rate": results["performance_metrics"]["success_rate_percentage"],
                "avg_time": results["efficiency_metrics"]["average_generation_time_seconds"],
                "rag_usage": results["quality_metrics"]["rag_utilization_rate_percentage"]
            }
    
    # 4. Results Comparison
    print("\nConfiguration Comparison:")
    print("-" * 60)
    print(f"{'Config':<12} {'Success Rate':<12} {'Avg Time':<10} {'RAG Usage':<10}")
    print("-" * 60)
    
    for name, data in results_comparison.items():
        print(f"{name:<12} {data['success_rate']:<12.1f}% {data['avg_time']:<10.3f}s {data['rag_usage']:<10.1f}%")
    
    # 5. Best Configuration Demo
    best_config = max(results_comparison.items(), 
                     key=lambda x: x[1]["success_rate"])
    
    print(f"\nBest Configuration: {best_config[0]}")
    
    # Re-configure with best settings
    best_settings = best_config[1]["config"]
    workflow.optimize_generator(
        max_retries=best_settings["retries"], 
        use_rag=best_settings["rag"], 
        use_terraform_cli=True
    )
    
    # Demo with complex prompts
    complex_prompts = [
        "Create a complete web application infrastructure with EC2 instances, load balancer, RDS database, and S3 bucket for static assets in AWS us-west-2 region",
        "Set up a secure VPC with private and public subnets, NAT gateway, and security groups for a three-tier architecture",
        "Create an auto-scaling group with launch configuration for web servers behind an Application Load Balancer"
    ]
    
    print(f"\nDemo with Complex Prompts using {best_config[0]} configuration:")
    print("=" * 70)
    
    for i, prompt in enumerate(complex_prompts, 1):
        print(f"\nComplex Example {i}:")
        print(f"Prompt: {prompt}")
        print("-" * 50)
        
        try:
            generated_code = workflow.generate_single(prompt)
            
            # Get generation metrics
            if hasattr(workflow.optimized_generator, 'get_generation_metrics'):
                metrics = workflow.optimized_generator.get_generation_metrics()
                print(f"Metrics: {metrics['total_attempts']} attempts, "
                      f"{'RAG used' if metrics.get('rag_used') else 'No RAG'}, "
                      f"Status: {metrics['final_validation_status']}")
            
            print("Generated code (first 200 chars):")
            print(generated_code[:200] + "..." if len(generated_code) > 200 else generated_code)
            
        except Exception as e:
            print(f"ERROR: {e}")
    
    # 6. Save detailed report
    report = {
        "dataset_analysis": analysis,
        "rag_statistics": rag_stats,
        "configuration_comparison": results_comparison,
        "best_configuration": {
            "name": best_config[0],
            "settings": best_config[1]
        }
    }
    
    with open("advanced_usage_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: advanced_usage_report.json")
    print("\nAdvanced usage example completed!")

if __name__ == "__main__":
    main()
