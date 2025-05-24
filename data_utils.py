# data_utils.py - tested✅
import dspy
from datasets import load_dataset
import pandas as pd

def load_iac_dataset(split="test", max_examples=None, dataset_name="autoiac-project/iac-eval"):
    try:
        dataset = load_dataset(dataset_name, split=split, trust_remote_code=True)
        print(f"Successfully loaded '{dataset_name}' dataset, split '{split}'. Found {len(dataset)} examples.")
    except Exception as e:
        print(f"Failed to load dataset '{dataset_name}': {e}")
        print("Please ensure the dataset is accessible or use a local copy.")
        return []

    dspy_examples = []
    count = 0
    for item in dataset:
        if max_examples and count >= max_examples:
            break
        prompt_text = item.get('Prompt')
        reference_output = item.get('Reference output')

        if prompt_text and reference_output:
            cleaned_reference_output = reference_output.replace("```hcl", "").replace("```", "").strip()
            example = dspy.Example(
                prompt=prompt_text,
                expected_iac_code=cleaned_reference_output
            ).with_inputs("prompt")
            dspy_examples.append(example)
            count += 1
        else:
            print(f"Skipping item due to missing 'Prompt' or 'Reference output': {item}")
            
    print(f"Converted {len(dspy_examples)} items to dspy.Example objects.")
    if not dspy_examples and (max_examples is None or max_examples > 0) :
        print("Warning: No examples were loaded. Check dataset name, structure, and connectivity.")
    return dspy_examples


if __name__ == "__main__":
    # Example usage
    examples = load_iac_dataset(split="test", max_examples=1)
    for example in examples:
        print(example)
        print("Inputs:", example.inputs)
        print("Expected Output:", example.expected_iac_code)
        print()