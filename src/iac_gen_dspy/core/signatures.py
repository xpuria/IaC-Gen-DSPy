"""
DSPy signatures for IaC generation workflow.
"""
import dspy

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
