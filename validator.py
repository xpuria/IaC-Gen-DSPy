# validator.py
import dspy
import subprocess
import tempfile
import os
import json
import shutil

class BasicValidator(dspy.Module):
    def __init__(self):
        super().__init__()

    def simple_heuristic_check(self, user_prompt: str, iac_code_to_validate: str) -> tuple[bool, str]:
        if not iac_code_to_validate or not iac_code_to_validate.strip():
            return False, "Generated IaC is empty."
        if "resource" not in iac_code_to_validate.lower():
            return False, "Generated IaC does not contain any 'resource' block."
        if 'resource "aws_instance"' in iac_code_to_validate:
            if 'ami' not in iac_code_to_validate or 'ami = ""' in iac_code_to_validate or 'ami=""' in iac_code_to_validate or 'ami = "ami-..."' in iac_code_to_validate:
                return False, "Heuristic check: Missing or placeholder 'ami' field in aws_instance."
            if 'instance_type' not in iac_code_to_validate or 'instance_type = ""' in iac_code_to_validate or 'instance_type=""' in iac_code_to_validate:
                return False, "Heuristic check: Missing 'instance_type' field in aws_instance."
        if 'resource "aws_s3_bucket"' in iac_code_to_validate:
            if 'bucket = ""' in iac_code_to_validate or 'bucket=""' in iac_code_to_validate or 'bucket = "my-unique-bucket' in iac_code_to_validate or 'bucket = "example-bucket' in iac_code_to_validate :
                 return False, "Heuristic check: Missing or placeholder 'bucket' name in aws_s3_bucket."
        return True, "Basic heuristic checks passed."

    def terraform_validate(self, iac_code: str, working_dir_parent: str = None) -> tuple[bool, str]:
        if not iac_code or not iac_code.strip():
            return False, "Cannot validate empty IaC code."
        base_temp_dir = tempfile.gettempdir() if working_dir_parent is None else working_dir_parent
        run_temp_dir = tempfile.mkdtemp(dir=base_temp_dir, prefix="tf_validate_")
        original_dir = os.getcwd()
        try:
            os.chdir(run_temp_dir)
            with open("main.tf", "w") as f:
                f.write(iac_code)
            init_process = subprocess.run(
                ["terraform", "init", "-upgrade", "-no-color"], 
                capture_output=True, text=True, check=False, timeout=60
            )
            if init_process.returncode != 0:
                return False, f"Terraform init failed in {run_temp_dir}: {init_process.stderr or init_process.stdout}"
            validate_process = subprocess.run(
                ["terraform", "validate", "-json", "-no-color"], 
                capture_output=True, text=True, check=False, timeout=60
            )
            if not validate_process.stdout.strip() and validate_process.returncode == 0:
                 return True, "Valid Terraform (validation produced empty JSON but exited successfully)."
            elif not validate_process.stdout.strip() and validate_process.returncode != 0:
                 return False, f"Terraform validation failed with empty JSON. Stderr: {validate_process.stderr or 'N/A'}. Stdout: {validate_process.stdout or 'N/A'}"
            try:
                validation_output = json.loads(validate_process.stdout)
            except json.JSONDecodeError:
                if validate_process.returncode == 0:
                    return True, f"Valid Terraform (non-JSON output but success exit code). Output: {validate_process.stdout}"
                return False, f"Failed to parse Terraform validation JSON. RC: {validate_process.returncode}. Output: {validate_process.stdout}. Stderr: {validate_process.stderr}"
            if validation_output.get("valid", False):
                return True, "Valid Terraform."
            else:
                errors = [
                    f"{diag.get('severity', 'error').upper()}: {diag.get('summary', 'Unknown error')}" + 
                    (f" (Detail: {diag.get('detail', '')})" if diag.get('detail') else "") +
                    (f" (File: {diag.get('range', {}).get('filename', 'N/A')}, Line: {diag.get('range', {}).get('start', {}).get('line', 'N/A')})" if diag.get('range') else "")
                    for diag in validation_output.get('diagnostics', [])
                ]
                error_summary = "Validation errors: " + "; ".join(errors) if errors else "Terraform validation reported issues (no specific error summaries found)."
                if validate_process.stderr and not any(e_msg in validate_process.stderr for e_msg in errors if e_msg): # Check if e_msg is not None
                    error_summary += f" Stderr: {validate_process.stderr.strip()}"
                return False, error_summary
        except FileNotFoundError:
            return False, "Terraform CLI not found. Please ensure it's installed and in your PATH."
        except subprocess.TimeoutExpired:
            return False, "Terraform command timed out."
        except Exception as e:
            return False, f"An unexpected error occurred during Terraform validation: {str(e)}"
        finally:
            os.chdir(original_dir)
            try:
                shutil.rmtree(run_temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp directory {run_temp_dir}: {e}")

iac_validator = BasicValidator()