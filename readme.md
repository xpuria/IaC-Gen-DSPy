# **LLM-Powered IaC Generator for AWS with DSPy (Data-Driven RAG)**

This project generates Infrastructure-as-Code (IaC) for AWS from natural language prompts using a Language Model (LLM) augmented by an agentic workflow.



## **Key Features**
1. **Data-Driven Pseudo-RAG**:  
   - Builds a knowledge base of IaC snippets by processing the `autti/iac-eval` dataset (or similar sources).  
   - Titles and keywords for each snippet are generated using an LLM in a preprocessing step, creating a `rag_kb.jsonl` file.

2. **Optimized Few-Shot Prompting**:  
   - Uses the [DSPy framework](https://github.com/stanfordnlp/dspy) to define the IaC generation pipeline.  
   - An optimizer like `BootstrapFewShot` selects effective few-shot examples from `autti/iac-eval` to enhance generation modules.

3. **Retry Mechanism**:  
   - Detects invalid or incomplete IaC (using `terraform validate`) and re-prompts the LLM with corrective context.

4. **Target Infrastructure**:  
   - Generates Terraform HCL output for AWS.

