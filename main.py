# main.py
import dspy
import os
from dotenv import load_dotenv
import random

from iac_workflow import IaCGenerator
from data_utils import load_iac_dataset 
from validator import iac_validator 
import pseudo_rag_store 

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in .env file.")

llm = dspy.LM(model='openai/gpt-4o-mini', api_key=OPENAI_API_KEY, max_tokens=2000)
dspy.settings.configure(lm=llm, trace=[])

def iac_validation_metric(gold: dspy.Example, pred_iac_code: str, trace=None) -> float:
    if not pred_iac_code or not pred_iac_code.strip():
        print(f"Metric: Empty prediction for prompt: '{gold.prompt[:50]}...' -> Score: 0.0")
        return 0.0
    is_valid, _ = iac_validator.terraform_validate(pred_iac_code)
    score = 1.0 if is_valid else 0.0
    print(f"Metric: Prompt: '{gold.prompt[:50]}...' -> Valid (TF CLI): {is_valid}, Score: {score}")
    return score

def main():
    if not os.path.exists(pseudo_rag_store.RAG_KB_FILE):
        print(f"'{pseudo_rag_store.RAG_KB_FILE}' not found!")
        print(f"Please run 'python build_rag_kb.py' first to generate the RAG knowledge base.")
        print("This script will now exit.")
        return

    print("Loading dataset for DSPy optimization (train/dev sets)...")
    total_examples_to_load_for_optimizer = 20 
    all_optimizer_examples = load_iac_dataset(split="test", max_examples=total_examples_to_load_for_optimizer)

    if not all_optimizer_examples:
        print("No data loaded from 'autti/iac-eval' for optimizer train/dev sets, exiting.")
        return

    random.seed(42)
    random.shuffle(all_optimizer_examples)
    
    if len(all_optimizer_examples) < 4:
        train_examples = all_optimizer_examples
        dev_examples = random.sample(all_optimizer_examples, min(len(all_optimizer_examples), 2)) if all_optimizer_examples else []
    else:
        split_point = max(2, int(len(all_optimizer_examples) * 0.7))
        if len(all_optimizer_examples) - split_point < 2 and len(all_optimizer_examples) > 2:
            split_point = len(all_optimizer_examples) - 2
        train_examples = all_optimizer_examples[:split_point]
        dev_examples = all_optimizer_examples[split_point:]
        if not dev_examples and train_examples :
             dev_examples = random.sample(train_examples, min(len(train_examples),2))

    print(f"Optimizer Dataset: Training set size: {len(train_examples)}, Dev set size: {len(dev_examples)}")

    if not train_examples:
        print("Cannot proceed with optimization: No training examples available for optimizer.")
        return

    student_pipeline = IaCGenerator(max_retries=1, use_rag=True, use_terraform_cli_validator=True)

    from dspy.teleprompt import BootstrapFewShot
    optimizer_config = dict(max_bootstrapped_demos=3, max_labeled_demos=3, max_rounds=1) 
    teleprompter = BootstrapFewShot(metric=iac_validation_metric, **optimizer_config)
    
    print("\nStarting DSPy optimization process (BootstrapFewShot)...")
    optimized_pipeline = teleprompter.compile(
        student=student_pipeline, 
        trainset=train_examples,

    )
    print("\n--- Optimization complete! ---")

    if dev_examples:
        print(f"\nEvaluating optimized pipeline on {len(dev_examples)} dev examples...")
        # ... (evaluation loop - same as before, ensure it prints useful info) ...
        total_score = 0.0
        for i, dev_example in enumerate(dev_examples):
            print(f"\n--- Dev Example {i+1}/{len(dev_examples)} ---")
            print(f"Prompt: {dev_example.prompt}")
            try:
                prediction_iac = optimized_pipeline(prompt=dev_example.prompt)
                print(f"Generated IaC:\n{prediction_iac if prediction_iac else '[EMPTY OUTPUT]'}")
                score = iac_validation_metric(dev_example, prediction_iac) # gold, pred
                total_score += score
                print(f"Score for this dev example: {score:.2f}")
                if hasattr(optimized_pipeline, 'history') and optimized_pipeline.history:
                    print("\n  Generation History for this Dev Example:")
                    for step_idx, step in enumerate(optimized_pipeline.history):
                        rag_info = f"(RAG: {step.get('rag_context_used_summary', 'N/A')})"
                        error_info = f"(Error: {step.get('error_feedback_to_llm', 'N/A')[:50]}...)" if 'error_feedback_to_llm' in step else ""
                        print(f"    Attempt {step.get('attempt', step_idx + 1)} [{step.get('type', 'N/A')}] {rag_info}{error_info} -> Valid: {step.get('validation_status','N/A')} ({step.get('validation_message','N/A')[:100]}...)")
            except Exception as e:
                print(f"Error during evaluation of dev example: {e}")
        avg_score = total_score / len(dev_examples) if dev_examples else 0.0
        print(f"\nAverage Terraform validation score on dev set: {avg_score:.2f}")

    print("\n--- Running a single test prompt with the optimized pipeline (Challenge Deliverable Example) ---")
    test_prompt_challenge = "Create an Ubuntu VM with 4 CPUs and 16GB RAM on AWS in the us-west-2 region."
    print(f"Input Prompt: {test_prompt_challenge}")
    
    if hasattr(optimized_pipeline, 'history'): optimized_pipeline.history = [] # Clear history
    final_iac = optimized_pipeline(prompt=test_prompt_challenge)
    
    print("\nLLM Outputs (Initial and Final for the test prompt):")
    # ... (display logic for initial/final and history - same as before) ...
    if hasattr(optimized_pipeline, 'history') and optimized_pipeline.history:
        initial_output = ""
        final_output_from_history = optimized_pipeline.history[-1]['output_from_llm'] if optimized_pipeline.history else final_iac
        if optimized_pipeline.history[0]['type'] == 'initial_generation':
            initial_output = optimized_pipeline.history[0]['output_from_llm']
            print(f"\nInitial LLM Output (Attempt 1):\n{initial_output if initial_output else '[EMPTY]'}")
        if len(optimized_pipeline.history) > 1:
             for i_step, step in enumerate(optimized_pipeline.history):
                if step['type'] == 'retry_generation':
                     print(f"\nRetry Attempt LLM Output (Error that triggered: {step.get('error_feedback_to_llm', 'N/A')}):\n{step['output_from_llm'] if step['output_from_llm'] else '[EMPTY]'}")
        print(f"\nFinal Output (from history for this run):\n{final_output_from_history if final_output_from_history else '[EMPTY]'}")
    else:
        print(f"Final LLM Output (direct):\n{final_iac if final_iac else '[EMPTY]'}")


    print("\nFew-Shot Examples (Selected by Optimizer for internal modules):")

    if hasattr(optimized_pipeline, 'initial_generator') and hasattr(optimized_pipeline.initial_generator, 'demos') and optimized_pipeline.initial_generator.demos:
        print(f"  Optimizer selected {len(optimized_pipeline.initial_generator.demos)} demos for the 'initial_generator' module.")
        for idx, demo in enumerate(optimized_pipeline.initial_generator.demos):

            # Check the structure of demo objects if this part errors out. It expects fields used in the metric and forward pass.
            demo_prompt = demo.get('prompt', 'N/A')
            demo_iac = demo.get('iac_code', demo.get('expected_iac_code', 'N/A')) # Check for common field names
            print(f"    Demo {idx+1} - Prompt: {str(demo_prompt)[:80]}... IaC: {str(demo_iac)[:100]}...")
    else:
        print("  Demos for 'initial_generator' not readily available or not set by optimizer for inspection here.")


    print("\nReference Examples Used (Pseudo-RAG snippets triggered for the test prompt from rag_kb.jsonl):")
    rag_for_test_prompt = pseudo_rag_store.get_relevant_snippets(test_prompt_challenge)
    if rag_for_test_prompt:
        print(rag_for_test_prompt)
    else:
        print("  No specific RAG snippets were triggered by this test prompt's keywords from the KB.")

    if final_iac:
        is_valid, msg = iac_validator.terraform_validate(final_iac)
        print(f"\nValidation of Final IaC for test prompt (Terraform CLI): {'Valid' if is_valid else 'Invalid'} - {msg}")

if __name__ == "__main__":
    main()