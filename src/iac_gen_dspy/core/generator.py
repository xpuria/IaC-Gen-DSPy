"""
Core IaC Generator using DSPy framework.
"""
import dspy
from ..rag.store import RAGStore
from ..validation.validator import TerraformValidator
from .signatures import IaCGeneration, RetryRefinement

class IaCGenerator(dspy.Module):
    """
    Main IaC Generator class using DSPy with RAG and validation.
    
    This class implements a sophisticated IaC generation pipeline that:
    1. Uses RAG to provide relevant context
    2. Employs DSPy optimization for better prompts
    3. Implements retry mechanisms with error feedback
    4. Validates generated code with Terraform CLI
    """
    
    def __init__(self, max_retries=1, use_rag=True, use_terraform_cli_validator=True):
        super().__init__()
        self.max_retries = max_retries
        self.use_rag = use_rag
        self.use_terraform_cli_validator = use_terraform_cli_validator

        # Initialize DSPy modules
        self.initial_generator = dspy.ChainOfThought(IaCGeneration)
        self.retry_generator = dspy.ChainOfThought(RetryRefinement)
        
        # Initialize supporting components
        self.rag_store = RAGStore() if use_rag else None
        self.validator = TerraformValidator()
        
        # Track generation history for analysis
        self.history = [] 

    def _get_rag_context(self, user_prompt: str, generated_code: str = "") -> str:
        """Get relevant RAG context for the given prompt and code."""
        if not self.use_rag or not self.rag_store:
            return ""
        return self.rag_store.get_relevant_snippets(user_prompt, generated_code)

    def forward(self, prompt: str):
        """
        Generate IaC code for the given prompt with retry mechanism.
        
        Args:
            prompt (str): Natural language description of infrastructure
            
        Returns:
            str: Generated Terraform HCL code
        """
        self.history = []
        current_prompt_text = prompt
        generated_iac = ""
        
        # Get initial RAG context
        rag_info_for_initial = self._get_rag_context(current_prompt_text)
        rag_context_for_llm = rag_info_for_initial if rag_info_for_initial else "No RAG snippets provided."
        error_feedback = ""

        for attempt in range(self.max_retries + 1):
            current_step_log = {"attempt": attempt + 1}
            print(f"\nAttempt {attempt + 1} for prompt: '{current_prompt_text}'")
            
            if attempt == 0:
                # Initial generation
                current_step_log["type"] = "initial_generation"
                current_step_log["rag_context_used_summary"] = rag_context_for_llm[:100] + "..." if rag_context_for_llm != "No RAG snippets provided." else "None"
                current_step_log["prompt_to_llm"] = current_prompt_text
                
                prediction = self.initial_generator(
                    rag_context=rag_context_for_llm, 
                    prompt=current_prompt_text
                )
                generated_iac = self._clean_iac_output(prediction.iac_code)
                current_step_log["output_from_llm"] = generated_iac
                print(f"Initial LLM Output:\n{generated_iac if generated_iac else '[EMPTY OUTPUT]'}")
            else:
                # Retry generation with error feedback
                current_step_log["type"] = "retry_generation"
                current_step_log["error_feedback_to_llm"] = error_feedback
                
                rag_info_for_retry = self._get_rag_context(current_prompt_text, self.history[-1]['output_from_llm'])
                error_message_with_hints = f"Error encountered: {error_feedback}\n"
                if rag_info_for_retry:
                    error_message_with_hints += f"Consider these RAG snippets for correction:\n{rag_info_for_retry}\n"
                else:
                    error_message_with_hints += "No specific RAG snippets found for this error, focus on the error message and original prompt.\n"
                error_message_with_hints += "Please provide the corrected Terraform code."

                retry_prediction = self.retry_generator(
                    original_prompt=current_prompt_text,
                    previous_iac_code=self.history[-1]['output_from_llm'],
                    error_message_with_hints=error_message_with_hints
                )
                generated_iac = self._clean_iac_output(retry_prediction.corrected_iac_code)
                current_step_log["output_from_llm"] = generated_iac
                print(f"Retry LLM Output:\n{generated_iac if generated_iac else '[EMPTY OUTPUT]'}")
            
            self.history.append(current_step_log)

            # Validate generated code
            if not generated_iac:
                is_valid = False
                validation_error_or_msg = "LLM returned empty or malformed IaC code."
            elif self.use_terraform_cli_validator:
                is_valid, validation_error_or_msg = self.validator.terraform_validate(generated_iac)
            else:
                is_valid, validation_error_or_msg = self.validator.simple_heuristic_check(
                    user_prompt=current_prompt_text, 
                    iac_code_to_validate=generated_iac
                )

            self.history[-1]['validation_status'] = "Valid" if is_valid else "Invalid"
            self.history[-1]['validation_message'] = validation_error_or_msg

            if is_valid:
                print(f"IaC Validated Successfully after {attempt + 1} attempts: {validation_error_or_msg}")
                return generated_iac
            else:
                error_feedback = validation_error_or_msg
                print(f"Validation Failed: {error_feedback}")
                if attempt >= self.max_retries:
                    print(f"Max retries ({self.max_retries + 1} attempts) reached. Returning last generated (invalid) IaC.")
                    return generated_iac
                    
        return generated_iac
    
    def _clean_iac_output(self, raw_output):
        """Clean the IaC output from DSPy prediction."""
        if not raw_output:
            return ""
        return raw_output.replace("```hcl", "").replace("```", "").strip()
    
    def get_generation_metrics(self):
        """Get metrics about the last generation process."""
        if not self.history:
            return {}
            
        total_attempts = len(self.history)
        successful = any(step.get('validation_status') == 'Valid' for step in self.history)
        
        return {
            'total_attempts': total_attempts,
            'successful': successful,
            'attempts_until_success': next(
                (i + 1 for i, step in enumerate(self.history) if step.get('validation_status') == 'Valid'), 
                total_attempts
            ) if successful else None,
            'rag_used': any('rag_context_used_summary' in step and step['rag_context_used_summary'] != 'None' for step in self.history),
            'final_validation_status': self.history[-1].get('validation_status', 'Unknown') if self.history else 'Unknown'
        }
