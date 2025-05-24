# iac_workflow.py ✅
import dspy
from pseudo_rag_store import get_relevant_snippets 
from validator import iac_validator

class IaCGeneration(dspy.Signature):
    """
    Given a natural language prompt, and potentially some reference IaC snippets,
    generate the corresponding Terraform HCL code for AWS.
    Ensure the code includes necessary provider blocks if not implicitly handled.
    The user's prompt describes the desired infrastructure.
    Produce only the HCL code block.
    """
    rag_context = dspy.InputField(desc="Relevant IaC snippets or templates to consider. If none, this will be 'No RAG snippets provided.'.", required=False)
    prompt = dspy.InputField(desc="User's natural language request for infrastructure.")
    iac_code = dspy.OutputField(desc="Generated Terraform HCL code.", prefix="```hcl\n", suffix="\n```")

class RetryRefinement(dspy.Signature):
    """
    Given an original prompt, the erroneous IaC code, and a specific error message (possibly including RAG hints),
    provide a corrected and complete version of the Terraform HCL code for AWS.
    Focus on fixing the identified error and ensuring all required fields are present.
    Produce only the HCL code block.
    """
    original_prompt = dspy.InputField(desc="The initial user request.")
    previous_iac_code = dspy.InputField(desc="The incorrect IaC code generated previously.")
    error_message_with_hints = dspy.InputField(desc="Specific error or missing information detected, potentially with RAG hints.")
    corrected_iac_code = dspy.OutputField(desc="Corrected and improved Terraform HCL code.", prefix="```hcl\n", suffix="\n```")

class IaCGenerator(dspy.Module):
    def __init__(self, max_retries=1, use_rag=True, use_terraform_cli_validator=True):
        super().__init__()
        self.max_retries = max_retries
        self.use_rag = use_rag
        self.use_terraform_cli_validator = use_terraform_cli_validator

        self.initial_generator = dspy.ChainOfThought(IaCGeneration)
        self.retry_generator = dspy.ChainOfThought(RetryRefinement)
        self.history = [] 

    def _get_rag_context(self, user_prompt: str, generated_code: str = "") -> str:
        if not self.use_rag:
            return ""
        # This now calls the function that loads from rag_kb.jsonl
        return get_relevant_snippets(user_prompt, generated_code)

    def forward(self, prompt: str): # Matches dspy.Example field name
        self.history = []
        current_prompt_text = prompt
        generated_iac = ""
        
        rag_info_for_initial = self._get_rag_context(current_prompt_text)
        rag_context_for_llm = rag_info_for_initial if rag_info_for_initial else "No RAG snippets provided."
        error_feedback = ""

        for attempt in range(self.max_retries + 1):
            current_step_log = {"attempt": attempt + 1}
            print(f"\nAttempt {attempt + 1} for prompt: '{current_prompt_text}'")
            
            if attempt == 0:
                current_step_log["type"] = "initial_generation"
                current_step_log["rag_context_used_summary"] = rag_context_for_llm[:100] + "..." if rag_context_for_llm != "No RAG snippets provided." else "None"
                current_step_log["prompt_to_llm"] = current_prompt_text
                
                prediction = self.initial_generator(
                    rag_context=rag_context_for_llm, 
                    prompt=current_prompt_text
                )
                generated_iac = prediction.iac_code.replace("```hcl", "").replace("```", "").strip() if hasattr(prediction, "iac_code") and prediction.iac_code else ""
                current_step_log["output_from_llm"] = generated_iac
                print(f"Initial LLM Output:\n{generated_iac if generated_iac else '[EMPTY OUTPUT]'}")
            else:
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
                generated_iac = retry_prediction.corrected_iac_code.replace("```hcl", "").replace("```", "").strip() if hasattr(retry_prediction, "corrected_iac_code") and retry_prediction.corrected_iac_code else ""
                current_step_log["output_from_llm"] = generated_iac
                print(f"Retry LLM Output:\n{generated_iac if generated_iac else '[EMPTY OUTPUT]'}")
            
            self.history.append(current_step_log)

            if not generated_iac:
                is_valid = False
                validation_error_or_msg = "LLM returned empty or malformed IaC code."
            elif self.use_terraform_cli_validator:
                is_valid, validation_error_or_msg = iac_validator.terraform_validate(generated_iac)
            else:
                is_valid, validation_error_or_msg = iac_validator.simple_heuristic_check(user_prompt=current_prompt_text, iac_code_to_validate=generated_iac)

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