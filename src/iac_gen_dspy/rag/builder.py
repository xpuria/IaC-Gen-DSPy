"""
RAG knowledge base builder using DSPy optimization.
"""
import json
import os
from typing import List, Tuple

import dspy

from ..data.utils import load_iac_dataset


class SnippetTitleGeneratorSignature(dspy.Signature):
    """Generate a concise, descriptive title for an IaC code block."""

    original_prompt: str = dspy.InputField(desc="The original user prompt that led to the IaC code.")
    iac_code: str = dspy.InputField(desc="The Terraform HCL code block.")
    snippet_title: str = dspy.OutputField(
        desc="A short, descriptive title for the IaC code (e.g., 'S3 Bucket with Versioning')."
    )


class SnippetKeywordExtractorSignature(dspy.Signature):
    """Extract relevant keywords for retrieving an IaC snippet."""

    original_prompt: str = dspy.InputField(desc="The user prompt.")
    iac_code: str = dspy.InputField(desc="The IaC code.")
    keywords_string: str = dspy.OutputField(
        desc="A comma-separated list of 5-7 relevant keywords (e.g., aws, s3, bucket, versioning, encryption)."
    )


class MetadataGenerationModule(dspy.Module):
    """DSPy module for generating metadata for IaC snippets."""

    def __init__(self):
        super().__init__()
        self.title_generator = dspy.ChainOfThought(SnippetTitleGeneratorSignature)
        self.keyword_extractor = dspy.ChainOfThought(SnippetKeywordExtractorSignature)

    def forward(self, original_prompt: str, iac_code: str) -> Tuple[str, List[str]]:
        """
        Generate title and keywords for an IaC snippet.

        Args:
            original_prompt (str): Original user prompt
            iac_code (str): IaC code to generate metadata for

        Returns:
            Tuple[str, List[str]]: (snippet_title, keywords_list)
        """
        title_result = self.title_generator(original_prompt=original_prompt, iac_code=iac_code)
        snippet_title = title_result.snippet_title.strip() if title_result.snippet_title else original_prompt[:70]

        keyword_result = self.keyword_extractor(original_prompt=original_prompt, iac_code=iac_code)
        keywords_str = keyword_result.keywords_string if keyword_result.keywords_string else ""
        keywords_list = [kw.strip().lower() for kw in keywords_str.split(",") if kw.strip()]

        if not keywords_list:
            prompt_keywords = [word.lower() for word in original_prompt.split() if len(word) > 3 and word.isalnum()]
            keywords_list = list(set(prompt_keywords))[:7]

        return snippet_title, list(set(keywords_list))


class RAGBuilder:
    """
    Builder for creating and optimizing RAG knowledge bases.
    """

    def __init__(self, llm_model: str = "ollama_chat/qwen2:7b", api_base: str = "http://localhost:11434"):
        """
        Initialize RAG builder with LLM configuration.

        Args:
            llm_model (str): LLM model to use for metadata generation
            api_base (str): API base URL for local models
        """
        self.llm_config = dspy.LM(model=llm_model, api_base=api_base, max_tokens=250)
        self.metadata_module = MetadataGenerationModule()

    def metadata_metric(self, gold_example: dspy.Example, prediction: Tuple[str, List[str]], trace=None) -> float:
        """
        Metric for metadata generation quality.

        Args:
            gold_example (dspy.Example): Input example
            prediction (Tuple[str, List[str]]): Generated (title, keywords)
            trace: Optional trace information

        Returns:
            float: Quality score between 0.0 and 1.0
        """
        generated_title, generated_keywords_list = prediction
        score = 0.0

        if generated_title and generated_title != gold_example.original_prompt[:70]:
            score += 0.5
        if generated_keywords_list and len(generated_keywords_list) > 1:
            score += 0.5

        return score

    def build_and_optimize_metadata_generator(
        self,
        train_examples: List[dspy.Example],
        eval_examples: List[dspy.Example] = None,
        optimizer_output_path: str = "optimized_metadata_generator.json",
    ) -> MetadataGenerationModule:
        """
        Build and optimize the metadata generation module.

        Args:
            train_examples (List[dspy.Example]): Training examples
            eval_examples (List[dspy.Example]): Evaluation examples (optional)
            optimizer_output_path (str): Path to save optimized module

        Returns:
            MetadataGenerationModule: Optimized metadata generator
        """
        print(f" Optimizing MetadataGenerationModule with {len(train_examples)} training examples...")

        dspy.settings.configure(lm=self.llm_config)

        if not eval_examples and len(train_examples) > 1:
            eval_examples = train_examples[: max(1, len(train_examples) // 10)]

        metadata_trainset = [
            dspy.Example(original_prompt=ex.prompt, iac_code=ex.expected_iac_code).with_inputs("original_prompt", "iac_code")
            for ex in train_examples
        ]

        from dspy.teleprompt import BootstrapFewShot

        config = dict(max_bootstrapped_demos=2, max_labeled_demos=2, max_rounds=1)

        teleprompter = BootstrapFewShot(metric=self.metadata_metric, **config)

        optimized_metadata_module = teleprompter.compile(
            student=self.metadata_module,
            trainset=metadata_trainset,
        )

        optimized_metadata_module.save(optimizer_output_path)
        print(f" Optimized metadata generator saved to {optimizer_output_path}")

        return optimized_metadata_module

    def build_knowledge_base(
        self,
        optimized_module_path: str = "optimized_metadata_generator.json",
        output_file: str = "rag_kb.jsonl",
        dataset_to_process: List[dspy.Example] = None,
        max_examples_for_kb: int = 10,
    ) -> None:
        """
        Build the RAG knowledge base using optimized metadata generator.

        Args:
            optimized_module_path (str): Path to optimized metadata generator
            output_file (str): Output JSONL file for knowledge base
            dataset_to_process (List[dspy.Example]): Dataset to process
            max_examples_for_kb (int): Maximum examples to include in KB
        """
        print(" Building RAG knowledge base...")

        loaded_metadata_module = MetadataGenerationModule()
        try:
            loaded_metadata_module.load(optimized_module_path)
            print(f" Loaded optimized metadata generator from {optimized_module_path}")
        except FileNotFoundError:
            print(f" Optimized module not found at {optimized_module_path}. Using unoptimized module.")

        if not dataset_to_process:
            print(" No dataset provided to process for KB. Aborting KB generation.")
            return

        examples_for_kb = dataset_to_process[: min(len(dataset_to_process), max_examples_for_kb)]
        print(f" Generating KB for {len(examples_for_kb)} examples...")

        processed_snippets = []
        for i, example in enumerate(examples_for_kb):
            print(f" Processing KB entry {i+1}/{len(examples_for_kb)}: {example.prompt[:50]}...")

            try:
                snippet_title, keywords_list = loaded_metadata_module(
                    original_prompt=example.prompt,
                    iac_code=example.expected_iac_code,
                )

                processed_snippets.append(
                    {
                        "snippet_name": snippet_title,
                        "keywords": keywords_list,
                        "iac_code": example.expected_iac_code,
                        "original_prompt": example.prompt,
                    }
                )

            except Exception as e:
                print(f" Error generating metadata for example: {e}")
                processed_snippets.append(
                    {
                        "snippet_name": example.prompt[:70],
                        "keywords": [
                            word.lower()
                            for word in example.prompt.split()
                            if len(word) > 3 and word.isalnum()
                        ][:7],
                        "iac_code": example.expected_iac_code,
                        "original_prompt": example.prompt,
                    }
                )

        with open(output_file, "w") as file_obj:
            for snippet in processed_snippets:
                file_obj.write(json.dumps(snippet) + "\n")

        print(f" Successfully built RAG knowledge base with {len(processed_snippets)} snippets at: {output_file}")

    def build_complete_rag_system(self, max_examples_total: int = 30, max_examples_for_kb: int = 10) -> None:
        """
        Complete RAG system build process from start to finish.

        Args:
            max_examples_total (int): Total examples to load for optimization
            max_examples_for_kb (int): Examples to use for KB
        """
        print(" Building complete RAG system...")

        print("📥 Loading dataset...")
        optimizer_train_dev_examples = load_iac_dataset(split="test", max_examples=max_examples_total)

        if not optimizer_train_dev_examples or len(optimizer_train_dev_examples) < 2:
            print(" Not enough examples to train/optimize the metadata generator. Aborting.")
            return

        opt_train_split = max(1, int(len(optimizer_train_dev_examples) * 0.7))
        optimizer_train_examples = optimizer_train_dev_examples[:opt_train_split]

        print(" Optimizing metadata generator...")
        self.build_and_optimize_metadata_generator(
            train_examples=optimizer_train_examples,
            optimizer_output_path="optimized_metadata_generator.json",
        )

        print(" Loading source dataset for knowledge base...")
        kb_source_dataset = load_iac_dataset(split="test", max_examples=max_examples_total)

        if not kb_source_dataset:
            print(" No source dataset to build the knowledge base from. Aborting.")
            return

        print(" Building knowledge base...")
        self.build_knowledge_base(
            optimized_module_path="optimized_metadata_generator.json",
            output_file="rag_kb.jsonl",
            dataset_to_process=kb_source_dataset,
            max_examples_for_kb=max_examples_for_kb,
        )

        print(" Complete RAG system build finished successfully!")
        print(" • optimized_metadata_generator.json created")
        print(" • rag_kb.jsonl created")
        print(" • Ready for use with main IaC generation system")
