# Examples

This directory contains example scripts demonstrating various features of IaC-Gen-DSPy.

## Available Examples

### 1. Basic Usage (`basic_usage.py`)
A simple introduction to the IaC generation system:
- Initialize the workflow
- Load training data
- Optimize the generator
- Generate IaC for common prompts

**Run:**
```bash
cd examples
python basic_usage.py
```

### 2. Advanced Usage (`advanced_usage.py`)
Comprehensive example showcasing advanced features:
- Dataset analysis and statistics
- RAG system analysis
- Configuration comparison
- Complex prompt handling
- Detailed metrics reporting

**Run:**
```bash
cd examples
python advanced_usage.py
```

### 3. RAG Builder (`rag_builder_example.py`)
Learn how to build and optimize RAG knowledge bases:
- Build metadata generator
- Create knowledge base from datasets
- Test retrieval capabilities
- Analyze knowledge base statistics

**Prerequisites:**
- Ollama installed and running
- qwen2:7b model available

**Setup:**
```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the required model
ollama pull qwen2:7b

# Start Ollama server
ollama serve
```

**Run:**
```bash
cd examples
python rag_builder_example.py
```

### 4. Graph RAG Comparison (`graph_rag_comparison.py`)
Compare the classic keyword RAG against the new Graph RAG backend:
- Builds an in-memory graph that links snippets, keywords, and resources
- Prints side-by-side retrieval outputs for curated prompts
- Runs a lightweight evaluation (~10 prompts) and stores metrics in `graph_rag_comparison_results.json`

**Run:**
```bash
cd examples
python graph_rag_comparison.py
```

**Outputs:**
- Console comparison of both retrieval approaches
- Summary metrics written to `graph_rag_comparison_results.json`

## Prerequisites for All Examples

1. **Environment Setup:**
```bash
pip install -r requirements.txt
```

2. **API Key:**
Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```
Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

3. **Terraform (Optional but Recommended):**
Install Terraform CLI for full validation features:
```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.0.0/terraform_1.0.0_linux_amd64.zip
unzip terraform_1.0.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

## Expected Outputs

Each example generates different outputs:

- **Basic Usage:** Console output with generated Terraform code
- **Advanced Usage:** Console output + `advanced_usage_report.json`
- **RAG Builder:** Console output + `optimized_metadata_generator.json` + `rag_kb.jsonl`

## Troubleshooting

### Common Issues

1. **API Key Error:**
```
Please set OPENAI_API_KEY environment variable
```
**Solution:** Set your OpenAI API key as described above.

2. **RAG Builder Connection Error:**
```
Error: Connection refused to localhost:11434
```
**Solution:** Ensure Ollama is running with `ollama serve`.

3. **Dataset Loading Issues:**
```
Failed to load dataset
```
**Solution:** Check internet connection and HuggingFace access.

### Performance Tips

- Start with smaller example counts for faster execution
- Use the basic example first to verify setup
- RAG building can take 5-10 minutes depending on dataset size

## Next Steps

After running the examples:

1. **Explore Benchmarks:** Run `scripts/run_benchmarks.py` for comprehensive evaluation
2. **Customize Configurations:** Modify parameters in examples to test different settings
3. **Build Production Systems:** Use the patterns from examples in your own applications
