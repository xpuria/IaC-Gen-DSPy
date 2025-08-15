"""
Basic usage example for IaC-Gen-DSPy.

This example demonstrates how to use the IaC generation system
for simple infrastructure creation tasks.
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from iac_gen_dspy.core.workflow import IaCWorkflow

def main():
    """Basic usage example."""
    print("IaC-Gen-DSPy Basic Usage Example")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        return
    
    # Initialize workflow
    workflow = IaCWorkflow(api_key=api_key)
    
    # Load and prepare training data (small set for quick demo)
    print("Loading training data...")
    workflow.load_and_prepare_data(total_examples=15)
    
    # Optimize the generator
    print("Optimizing generator...")
    workflow.optimize_generator(
        max_retries=1, 
        use_rag=True, 
        use_terraform_cli=True
    )
    
    # Example prompts to test
    test_prompts = [
        "Create an EC2 instance with t2.micro instance type in us-west-2",
        "Create an S3 bucket with versioning enabled",
        "Create a VPC with a public subnet in the us-east-1 region"
    ]
    
    print("\nGenerating IaC for example prompts...")
    print("=" * 50)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nExample {i}: {prompt}")
        print("-" * 40)
        
        try:
            generated_code = workflow.generate_single(prompt)
            print("Generated Terraform code:")
            print(generated_code)
            
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\nBasic usage example completed!")

if __name__ == "__main__":
    main()
