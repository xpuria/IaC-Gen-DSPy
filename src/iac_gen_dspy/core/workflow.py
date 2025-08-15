"""
High-level workflow orchestration for IaC generation.
"""
import dspy
from typing import List, Dict, Any
from .generator import IaCGenerator
from ..data.utils import load_iac_dataset
from ..metrics.evaluator import iac_validation_metric

class IaCWorkflow:
    """
    High-level workflow for IaC generation with DSPy optimization.
    
    This class orchestrates the entire process from dataset loading to model optimization
    and evaluation, providing a convenient interface for running IaC generation tasks.
    """
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini", max_tokens: int = 2000):
        """
        Initialize the workflow with LLM configuration.
        
        Args:
            api_key (str): OpenAI API key
            model (str): Model to use for generation
            max_tokens (int): Maximum tokens for generation
        """
        self.llm = dspy.LM(model=model, api_key=api_key, max_tokens=max_tokens)
        dspy.settings.configure(lm=self.llm, trace=[])
        
        self.generator = None
        self.optimized_generator = None
        self.train_examples = []
        self.dev_examples = []
        
    def load_and_prepare_data(self, total_examples: int = 20, train_ratio: float = 0.7):
        """
        Load and prepare training/dev datasets.
        
        Args:
            total_examples (int): Total number of examples to load
            train_ratio (float): Ratio of training examples
        """
        print(f"Loading dataset for DSPy optimization ({total_examples} examples)...")
        all_examples = load_iac_dataset(split="test", max_examples=total_examples)
        
        if not all_examples:
            raise ValueError("No data loaded from 'autoiac-project/iac-eval' dataset")
            
        # Split into train/dev
        import random
        random.seed(42)
        random.shuffle(all_examples)
        
        if len(all_examples) < 4:
            self.train_examples = all_examples
            self.dev_examples = random.sample(all_examples, min(len(all_examples), 2)) if all_examples else []
        else:
            split_point = max(2, int(len(all_examples) * train_ratio))
            if len(all_examples) - split_point < 2 and len(all_examples) > 2:
                split_point = len(all_examples) - 2
            self.train_examples = all_examples[:split_point]
            self.dev_examples = all_examples[split_point:]
            if not self.dev_examples and self.train_examples:
                self.dev_examples = random.sample(self.train_examples, min(len(self.train_examples), 2))
        
        print(f"Dataset prepared: Training set size: {len(self.train_examples)}, Dev set size: {len(self.dev_examples)}")
        
    def optimize_generator(self, max_retries: int = 1, use_rag: bool = True, use_terraform_cli: bool = True):
        """
        Create and optimize the IaC generator using DSPy.
        
        Args:
            max_retries (int): Maximum retry attempts for validation failures
            use_rag (bool): Whether to use RAG for context
            use_terraform_cli (bool): Whether to use Terraform CLI for validation
        """
        if not self.train_examples:
            raise ValueError("No training examples available. Call load_and_prepare_data() first.")
            
        # Create base generator
        self.generator = IaCGenerator(
            max_retries=max_retries, 
            use_rag=use_rag, 
            use_terraform_cli_validator=use_terraform_cli
        )
        
        # Configure optimizer
        from dspy.teleprompt import BootstrapFewShot
        optimizer_config = dict(
            max_bootstrapped_demos=3, 
            max_labeled_demos=3, 
            max_rounds=1
        )
        teleprompter = BootstrapFewShot(metric=iac_validation_metric, **optimizer_config)
        
        print("\nStarting DSPy optimization process (BootstrapFewShot)...")
        self.optimized_generator = teleprompter.compile(
            student=self.generator,
            trainset=self.train_examples
        )
        print("--- Optimization complete! ---")
        
    def evaluate_generator(self) -> Dict[str, Any]:
        """
        Evaluate the optimized generator on dev set.
        
        Returns:
            Dict[str, Any]: Evaluation results
        """
        if not self.optimized_generator:
            raise ValueError("No optimized generator available. Call optimize_generator() first.")
            
        if not self.dev_examples:
            print("No dev examples available for evaluation.")
            return {}
            
        print(f"\nEvaluating optimized pipeline on {len(self.dev_examples)} dev examples...")
        
        total_score = 0.0
        successful_generations = 0
        total_attempts = 0
        rag_usage_count = 0
        
        detailed_results = []
        
        for i, dev_example in enumerate(self.dev_examples):
            print(f"\n--- Dev Example {i+1}/{len(self.dev_examples)} ---")
            print(f"Prompt: {dev_example.prompt}")
            
            try:
                prediction_iac = self.optimized_generator(prompt=dev_example.prompt)
                print(f"Generated IaC:\n{prediction_iac if prediction_iac else '[EMPTY OUTPUT]'}")
                
                score = iac_validation_metric(dev_example, prediction_iac)
                total_score += score
                print(f"Score for this dev example: {score:.2f}")
                
                if score > 0:
                    successful_generations += 1
                
                # Get generation metrics
                gen_metrics = self.optimized_generator.get_generation_metrics()
                total_attempts += gen_metrics.get('total_attempts', 1)
                
                if gen_metrics.get('rag_used', False):
                    rag_usage_count += 1
                
                detailed_results.append({
                    'prompt': dev_example.prompt,
                    'generated_code': prediction_iac,
                    'score': score,
                    'metrics': gen_metrics
                })
                
            except Exception as e:
                print(f"Error during evaluation of dev example: {e}")
                detailed_results.append({
                    'prompt': dev_example.prompt,
                    'error': str(e),
                    'score': 0.0
                })
        
        avg_score = total_score / len(self.dev_examples) if self.dev_examples else 0.0
        success_rate = successful_generations / len(self.dev_examples) if self.dev_examples else 0.0
        avg_attempts = total_attempts / len(self.dev_examples) if self.dev_examples else 0.0
        rag_usage_rate = rag_usage_count / len(self.dev_examples) if self.dev_examples else 0.0
        
        results = {
            'average_score': avg_score,
            'success_rate': success_rate,
            'successful_generations': successful_generations,
            'total_examples': len(self.dev_examples),
            'average_attempts_per_example': avg_attempts,
            'rag_usage_rate': rag_usage_rate,
            'detailed_results': detailed_results
        }
        
        print(f"\nEvaluation Results:")
        print(f"Average Terraform validation score: {avg_score:.2f}")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Average attempts per example: {avg_attempts:.1f}")
        print(f"RAG usage rate: {rag_usage_rate:.2%}")
        
        return results
        
    def generate_single(self, prompt: str) -> str:
        """
        Generate IaC for a single prompt.
        
        Args:
            prompt (str): Natural language description
            
        Returns:
            str: Generated Terraform HCL code
        """
        if not self.optimized_generator:
            if not self.generator:
                raise ValueError("No generator available. Call optimize_generator() first.")
            generator = self.generator
        else:
            generator = self.optimized_generator
            
        # Clear history for clean generation
        if hasattr(generator, 'history'):
            generator.history = []
            
        return generator(prompt=prompt)
