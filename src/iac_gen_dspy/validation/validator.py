"""
Terraform validation functionality for IaC code.
"""
import subprocess
import tempfile
import os
import json
import shutil
from typing import Tuple

class TerraformValidator:
    """
    Validator for Terraform IaC code with both heuristic and CLI-based validation.
    
    Provides multiple validation methods:
    1. Simple heuristic checks for common issues
    2. Full Terraform CLI validation with proper error reporting
    """
    
    def __init__(self):
        pass

    def simple_heuristic_check(self, user_prompt: str, iac_code_to_validate: str) -> Tuple[bool, str]:
        """
        Perform simple heuristic validation checks on IaC code.
        
        Args:
            user_prompt (str): Original user prompt (for context)
            iac_code_to_validate (str): Generated IaC code to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not iac_code_to_validate or not iac_code_to_validate.strip():
            return False, "Generated IaC is empty."
            
        if "resource" not in iac_code_to_validate.lower():
            return False, "Generated IaC does not contain any 'resource' block."
            
        # AWS Instance specific checks
        if 'resource "aws_instance"' in iac_code_to_validate:
            if ('ami' not in iac_code_to_validate or 
                'ami = ""' in iac_code_to_validate or 
                'ami=""' in iac_code_to_validate or 
                'ami = "ami-..."' in iac_code_to_validate):
                return False, "Heuristic check: Missing or placeholder 'ami' field in aws_instance."
                
            if ('instance_type' not in iac_code_to_validate or 
                'instance_type = ""' in iac_code_to_validate or 
                'instance_type=""' in iac_code_to_validate):
                return False, "Heuristic check: Missing 'instance_type' field in aws_instance."
                
        # S3 Bucket specific checks
        if 'resource "aws_s3_bucket"' in iac_code_to_validate:
            if ('bucket = ""' in iac_code_to_validate or 
                'bucket=""' in iac_code_to_validate or 
                'bucket = "my-unique-bucket' in iac_code_to_validate or 
                'bucket = "example-bucket' in iac_code_to_validate):
                return False, "Heuristic check: Missing or placeholder 'bucket' name in aws_s3_bucket."
                
        return True, "Basic heuristic checks passed."

    def terraform_validate(self, iac_code: str, working_dir_parent: str = None) -> Tuple[bool, str]:
        """
        Validate Terraform code using the Terraform CLI.
        
        Args:
            iac_code (str): Terraform HCL code to validate
            working_dir_parent (str): Parent directory for temporary validation
            
        Returns:
            Tuple[bool, str]: (is_valid, validation_message)
        """
        if not iac_code or not iac_code.strip():
            return False, "Cannot validate empty IaC code."
            
        base_temp_dir = tempfile.gettempdir() if working_dir_parent is None else working_dir_parent
        run_temp_dir = tempfile.mkdtemp(dir=base_temp_dir, prefix="tf_validate_")
        original_dir = os.getcwd()
        
        try:
            os.chdir(run_temp_dir)
            
            # Write the IaC code to main.tf
            with open("main.tf", "w") as f:
                f.write(iac_code)
            
            # Run terraform init
            init_process = subprocess.run(
                ["terraform", "init", "-upgrade", "-no-color"], 
                capture_output=True, text=True, check=False, timeout=60
            )
            
            if init_process.returncode != 0:
                return False, f"Terraform init failed: {init_process.stderr or init_process.stdout}"
            
            # Run terraform validate
            validate_process = subprocess.run(
                ["terraform", "validate", "-json", "-no-color"], 
                capture_output=True, text=True, check=False, timeout=60
            )
            
            # Handle empty output
            if not validate_process.stdout.strip() and validate_process.returncode == 0:
                return True, "Valid Terraform (validation produced empty JSON but exited successfully)."
            elif not validate_process.stdout.strip() and validate_process.returncode != 0:
                return False, f"Terraform validation failed with empty JSON. Stderr: {validate_process.stderr or 'N/A'}"
            
            # Parse validation JSON output
            try:
                validation_output = json.loads(validate_process.stdout)
            except json.JSONDecodeError:
                if validate_process.returncode == 0:
                    return True, f"Valid Terraform (non-JSON output but success exit code). Output: {validate_process.stdout}"
                return False, f"Failed to parse Terraform validation JSON. RC: {validate_process.returncode}. Output: {validate_process.stdout}"
            
            if validation_output.get("valid", False):
                return True, "Valid Terraform."
            else:
                # Parse error diagnostics
                errors = []
                for diag in validation_output.get('diagnostics', []):
                    error_msg = f"{diag.get('severity', 'error').upper()}: {diag.get('summary', 'Unknown error')}"
                    
                    if diag.get('detail'):
                        error_msg += f" (Detail: {diag.get('detail')})"
                    
                    if diag.get('range'):
                        range_info = diag['range']
                        filename = range_info.get('filename', 'N/A')
                        line = range_info.get('start', {}).get('line', 'N/A')
                        error_msg += f" (File: {filename}, Line: {line})"
                    
                    errors.append(error_msg)
                
                error_summary = "Validation errors: " + "; ".join(errors) if errors else "Terraform validation reported issues."
                
                if validate_process.stderr and not any(e_msg in validate_process.stderr for e_msg in errors if e_msg):
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
    
    def validate(self, iac_code: str, use_terraform_cli: bool = True) -> Tuple[bool, str]:
        """
        Validate IaC code using the appropriate method.
        
        Args:
            iac_code (str): IaC code to validate
            use_terraform_cli (bool): Whether to use Terraform CLI validation
            
        Returns:
            Tuple[bool, str]: (is_valid, validation_message)
        """
        if use_terraform_cli:
            return self.terraform_validate(iac_code)
        else:
            return self.simple_heuristic_check("", iac_code)
