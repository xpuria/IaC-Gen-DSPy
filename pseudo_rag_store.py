# pseudo_rag_store.py
import json
import os

RAG_KB_FILE = "rag_kb.jsonl"
_RAG_SNIPPETS_CACHE = None 

def load_rag_snippets_from_file(kb_file=RAG_KB_FILE) -> list:
    global _RAG_SNIPPETS_CACHE
    if _RAG_SNIPPETS_CACHE is not None:
        return _RAG_SNIPPETS_CACHE

    snippets = []
    if not os.path.exists(kb_file):
        print(f"Warning: RAG knowledge base file '{kb_file}' not found.")
        print("Please run your 'build_rag_kb.py' (using Qwen) first to generate it.")
        print("Falling back to a minimal hardcoded list for now.")
        _RAG_SNIPPETS_CACHE = [ 
            {
                "keywords": ["ec2", "instance"], "snippet_name": "Fallback EC2 Example",
                "iac_code": 'resource "aws_instance" "fallback" {\n  ami = "ami-..."\n  instance_type = "t2.micro"\n}'
            }
        ]
        return _RAG_SNIPPETS_CACHE
        
    with open(kb_file, 'r') as f:
        for line in f: # Reads each line from your rag_kb.jsonl
            try:
                # Parses the JSON object expecting 'snippet_name', 'keywords', 'iac_code'
                snippets.append(json.loads(line)) 
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON line in '{kb_file}': {line.strip()}")
    
    if not snippets:
        print(f"Warning: No snippets loaded from '{kb_file}', even though it exists.")
    else:
        print(f"Loaded {len(snippets)} RAG snippets from '{kb_file}'.")
    
    _RAG_SNIPPETS_CACHE = snippets
    return snippets

def get_relevant_snippets(prompt_text: str, generated_code: str = "") -> str:
    all_snippets = load_rag_snippets_from_file() # This loads your Qwen-generated data
    if not all_snippets:
        return ""

    relevant_snippets_data = []
    prompt_lower = prompt_text.lower()
    code_lower = generated_code.lower() if generated_code else ""

    for item in all_snippets: # Iterates through your Qwen-generated snippets
        item_keywords = item.get("keywords", [])
        if not isinstance(item_keywords, list): 
            item_keywords = []

        prompt_match = any(keyword.lower() in prompt_lower for keyword in item_keywords)
        code_match = any(keyword.lower() in code_lower for keyword in item_keywords) if code_lower else False
        
        if prompt_match or code_match:
            # Uses the 'snippet_name' and 'iac_code' from your Qwen-generated data
            relevant_snippets_data.append(f"# Reference: {item.get('snippet_name', 'Untitled Snippet')}\n{item.get('iac_code', '')}")

    if not relevant_snippets_data:
        return "" 
    return "\n\n---\nRelevant IaC Reference Snippets:\n" + "\n\n".join(relevant_snippets_data)

if __name__ == "__main__":
    if not os.path.exists(RAG_KB_FILE):
        print(f"'{RAG_KB_FILE}' not found. Run your Qwen-based 'build_rag_kb.py' to create it before testing this module.")
    else:
        test_prompt = "Create an S3 bucket with versioning"
        snippets_text = get_relevant_snippets(test_prompt)
        if snippets_text:
            print(f"Snippets for '{test_prompt}':\n{snippets_text}")
        else:
            print(f"No snippets found for '{test_prompt}'.")