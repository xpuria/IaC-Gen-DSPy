# **LLM-Powered IaC Generator for AWS with DSPy (Data-Driven RAG)**

This project generates Infrastructure-as-Code (IaC) for AWS from natural language prompts using a Language Model (LLM) augmented by an agentic workflow.

---

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

---

## **Project Structure**

```plaintext
iac_generator_project/
├── [main.py](http://_vscodecontentref_/1)                   # Main script for optimization and running IaC generation
├── [iac_workflow.py](http://_vscodecontentref_/2)           # DSPy Signatures and the main IaCGenerator Module
├── [data_utils.py](http://_vscodecontentref_/3)             # Utilities for loading the 'autti/iac-eval' dataset
├── [pseudo_rag_store.py](http://_vscodecontentref_/4)       # Loads and queries the RAG knowledge base from [rag_kb.jsonl](http://_vscodecontentref_/5)
├── [validator.py](http://_vscodecontentref_/6)              # Implements IaC validation logic (including Terraform CLI)
├── [build_rag_kb.py](http://_vscodecontentref_/7)           # Preprocessing script to build [rag_kb.jsonl](http://_vscodecontentref_/8) using LLM for metadata
├── [requirements.txt](http://_vscodecontentref_/9)          # Python dependencies
├── [README.md](http://_vscodecontentref_/10)                 # This file
├── .env                      # For API keys (user-created)
└── [rag_kb.jsonl](http://_vscodecontentref_/11)              # Generated RAG knowledge base file