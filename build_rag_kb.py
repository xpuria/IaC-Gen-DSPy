# build_rag_kb.py
import dspy
import os
import json
from dotenv import load_dotenv
from data_utils import load_iac_dataset 
from typing import List 

#DSPy Signatures for Metadata Generation
class SnippetTitleGeneratorSignature(dspy.Signature):
    """Given a user prompt and its corresponding IaC code, generate a concise, descriptive title for the IaC code block."""
    original_prompt:str = dspy.InputField(desc="The original user prompt that led to the IaC code.")
    iac_code:str = dspy.InputField(desc="The Terraform HCL code block.")
    snippet_title:str = dspy.OutputField(desc="A short, descriptive title for the IaC code (e.g., 'S3 Bucket with Versioning').")

class SnippetKeywordExtractorSignature(dspy.Signature):
    """Given an original prompt and an IaC code block, extract 5-7 relevant keywords for retrieving this IaC snippet. 
    Focus on resource types, key actions (create, deploy, configure), important parameters, and cloud services mentioned."""
    original_prompt:str = dspy.InputField(desc="The user prompt.")
    iac_code:str = dspy.InputField(desc="The IaC code.")
    #the output field should ideally be a string that we can parse, 
    #as direct List output can be tricky across different LMs with Predict.
    keywords_string:str = dspy.OutputField(desc="A comma-separated list of 5-7 relevant keywords (e.g., aws, s3, bucket, versioning, encryption).")

#DSPy Module for Metadata Generation
class MetadataGenerationModule(dspy.Module):
    def __init__(self):
        super().__init__()

        self.title_generator = dspy.ChainOfThought(SnippetTitleGeneratorSignature)
        self.keyword_extractor = dspy.ChainOfThought(SnippetKeywordExtractorSignature)

    def forward(self, original_prompt: str, iac_code: str) -> tuple[str, List[str]]:
        title_result = self.title_generator(original_prompt=original_prompt, iac_code=iac_code)
        snippet_title = title_result.snippet_title.strip() if title_result.snippet_title else original_prompt[:70]

        keyword_result = self.keyword_extractor(original_prompt=original_prompt, iac_code=iac_code)
        keywords_str = keyword_result.keywords_string if keyword_result.keywords_string else ""
        keywords_list = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
        

        if not keywords_list:
            prompt_keywords = [word.lower() for word in original_prompt.split() if len(word) > 3 and word.isalnum()]
            keywords_list = list(set(prompt_keywords))[:7]
            
        return snippet_title, list(set(keywords_list))


def metadata_metric(gold_example: dspy.Example, prediction: tuple[str, List[str]], trace=None) -> float:
    """
    A simple metric for metadata generation.
    `gold_example` is the input (prompt, iac_code).
    `prediction` is a tuple (generated_title, generated_keywords_list).
    """
    generated_title, generated_keywords_list = prediction
    score = 0.0
    if generated_title and generated_title != gold_example.original_prompt[:70]: 
        score += 0.5
    if generated_keywords_list and len(generated_keywords_list) > 1 :
        score += 0.5
    return score

def build_and_optimize_metadata_generator(
        train_examples_for_optimizer: List[dspy.Example], 
        eval_examples_for_optimizer: List[dspy.Example] = None,
        optimizer_output_path="optimized_metadata_generator.json"
    ):
    """Optimizes the MetadataGenerationModule and saves it."""
    
    student_metadata_module = MetadataGenerationModule()
    

    if not eval_examples_for_optimizer and len(train_examples_for_optimizer) > 1:
        eval_examples_for_optimizer = train_examples_for_optimizer[:max(1, len(train_examples_for_optimizer) // 10)]



    from dspy.teleprompt import BootstrapFewShot

    config = dict(max_bootstrapped_demos=2, max_labeled_demos=2, max_rounds=1) 
    
    teleprompter = BootstrapFewShot(
        metric=metadata_metric,

        **config
    )
    
    print(f"\nOptimizing MetadataGenerationModule with {len(train_examples_for_optimizer)} training examples...")
    
    metadata_trainset = [
        dspy.Example(original_prompt=ex.prompt, iac_code=ex.expected_iac_code).with_inputs('original_prompt', 'iac_code') 
        for ex in train_examples_for_optimizer
    ]

    optimized_metadata_module = teleprompter.compile(
        student=student_metadata_module,
        trainset=metadata_trainset, 
        #eval_kwargs={'num_threads': 1, 'display_progress': True, 'display_table': 0}
    )
    
    optimized_metadata_module.save(optimizer_output_path)
    print(f"Optimized metadata generator saved to {optimizer_output_path}")
    return optimized_metadata_module

def build_knowledge_base_with_optimized_module(
        optimized_module_path="optimized_metadata_generator.json",
        output_file="rag_kb.jsonl", 
        dataset_to_process: List[dspy.Example] = None,
        max_examples_for_kb=10 
    ):
    """
    Uses a pre-optimized metadata generator to build the RAG knowledge base.
    """

    loaded_metadata_module = MetadataGenerationModule() 
    try:
        loaded_metadata_module.load(optimized_module_path)
        print(f"Loaded optimized metadata generator from {optimized_module_path}")
    except FileNotFoundError:
        print(f"Error: Optimized module not found at {optimized_module_path}. Please run optimization first.")
        print("Falling back to unoptimized module for KB generation.")


    if not dataset_to_process:
        print("No dataset provided to process for KB. Aborting KB generation.")
        return

    examples_for_kb = dataset_to_process[:min(len(dataset_to_process), max_examples_for_kb)]
    print(f"Generating KB for {len(examples_for_kb)} examples using the metadata generator...")

    processed_snippets = []
    for i, example in enumerate(examples_for_kb): # example has .prompt and .expected_iac_code
        print(f"  Generating metadata for KB entry {i+1}/{len(examples_for_kb)}: {example.prompt[:50]}...")
        try:

            snippet_title, keywords_list = loaded_metadata_module(
                original_prompt=example.prompt, 
                iac_code=example.expected_iac_code
            )
            
            processed_snippets.append({
                "snippet_name": snippet_title,
                "keywords": keywords_list,
                "iac_code": example.expected_iac_code,
                "original_prompt": example.prompt
            })
        except Exception as e:
            print(f"    Error generating metadata for example: {e}")

            processed_snippets.append({
                "snippet_name": example.prompt[:70],
                "keywords": [word.lower() for word in example.prompt.split() if len(word) > 3 and word.isalnum()][:7],
                "iac_code": example.expected_iac_code,
                "original_prompt": example.prompt
            })

    with open(output_file, 'w') as f:
        for snippet in processed_snippets:
            f.write(json.dumps(snippet) + '\n')
    
    print(f"\nSuccessfully built RAG knowledge base with {len(processed_snippets)} snippets at: {output_file}")

if __name__ == "__main__":
    load_dotenv()

    llm_preproc_config = dspy.LM(model='ollama_chat/qwen2:7b', api_base="http://localhost:11434", max_tokens=250)


    dspy.settings.configure(lm=llm_preproc_config)


    optimizer_train_dev_examples = load_iac_dataset(split="test", max_examples=10)
    
    if not optimizer_train_dev_examples or len(optimizer_train_dev_examples) < 2:
        print("Not enough examples to train/optimize the metadata generator. Aborting.")
        exit()


    opt_train_split = max(1, int(len(optimizer_train_dev_examples) * 0.7))
    optimizer_train_examples = optimizer_train_dev_examples[:opt_train_split]


    build_and_optimize_metadata_generator(
        train_examples_for_optimizer=optimizer_train_examples,

        optimizer_output_path="optimized_metadata_generator.json"
    )
    

    

    kb_source_dataset = load_iac_dataset(split="test", max_examples=20)
    
    if not kb_source_dataset:
        print("No source dataset to build the knowledge base from. Aborting.")
        exit()

    build_knowledge_base_with_optimized_module(
        optimized_module_path="optimized_metadata_generator.json",
        output_file="rag_kb.jsonl",
        dataset_to_process=kb_source_dataset,
        max_examples_for_kb=10 
    )
    
    print("\nProcess complete. 'optimized_metadata_generator.json' and 'rag_kb.jsonl' should be created.")
    print("You can now run main.py which will use rag_kb.jsonl.")
