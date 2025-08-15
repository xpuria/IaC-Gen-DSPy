"""
Configuration management system for IaC-Gen-DSPy.
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """
    Configuration manager for handling project settings and parameters.
    
    Supports loading configuration from YAML files, environment variables,
    and programmatic overrides with priority handling.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file (Optional[str]): Path to configuration file
        """
        self.config = {}
        self._load_default_config()
        
        if config_file:
            self._load_config_file(config_file)
        else:
            self._load_default_config_file()
            
        self._load_environment_overrides()
    
    def _load_default_config(self):
        """Load hardcoded default configuration."""
        self.config = {
            "llm": {
                "model": "openai/gpt-4o-mini",
                "max_tokens": 2000,
                "temperature": 0.1
            },
            "dataset": {
                "name": "autoiac-project/iac-eval",
                "split": "test",
                "max_examples_training": 20,
                "max_examples_evaluation": 50,
                "train_ratio": 0.7
            },
            "rag": {
                "enabled": True,
                "kb_file": "rag_kb.jsonl",
                "max_snippets_per_query": 3
            },
            "generation": {
                "max_retries": 2,
                "use_terraform_cli_validation": True,
                "use_rag": True
            },
            "validation": {
                "terraform_cli": True,
                "timeout_seconds": 60
            },
            "output": {
                "log_level": "INFO",
                "metrics_file": "metrics_report.json"
            }
        }
    
    def _load_default_config_file(self):
        """Load default configuration file if it exists."""
        # Try to find default config file
        possible_paths = [
            "config/default_config.yaml",
            "../config/default_config.yaml",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "default_config.yaml")
        ]
        
        for config_path in possible_paths:
            if os.path.exists(config_path):
                self._load_config_file(config_path)
                break
    
    def _load_config_file(self, config_file: str):
        """
        Load configuration from YAML file.
        
        Args:
            config_file (str): Path to configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._deep_update(self.config, file_config)
        except FileNotFoundError:
            print(f"Warning: Configuration file not found: {config_file}")
        except yaml.YAMLError as e:
            print(f"Warning: Error parsing configuration file: {e}")
    
    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables."""
        # Map environment variables to config keys
        env_mappings = {
            "OPENAI_API_KEY": ["api", "openai_key"],
            "IAC_MODEL": ["llm", "model"],
            "IAC_MAX_TOKENS": ["llm", "max_tokens"],
            "IAC_MAX_RETRIES": ["generation", "max_retries"],
            "IAC_USE_RAG": ["generation", "use_rag"],
            "IAC_USE_TERRAFORM_CLI": ["generation", "use_terraform_cli_validation"],
            "IAC_LOG_LEVEL": ["output", "log_level"],
            "IAC_DATASET_MAX_EXAMPLES": ["dataset", "max_examples_training"]
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '').isdigit():
                    value = float(value)
                
                # Set the configuration value
                self._set_nested_value(self.config, config_path, value)
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """
        Deep update dictionary with another dictionary.
        
        Args:
            base_dict (Dict[str, Any]): Base dictionary to update
            update_dict (Dict[str, Any]): Dictionary with updates
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _set_nested_value(self, dictionary: Dict[str, Any], path: list, value: Any):
        """
        Set a nested dictionary value using a path list.
        
        Args:
            dictionary (Dict[str, Any]): Target dictionary
            path (list): Path to the value as list of keys
            value (Any): Value to set
        """
        for key in path[:-1]:
            if key not in dictionary:
                dictionary[key] = {}
            dictionary = dictionary[key]
        dictionary[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key (str): Configuration key (e.g., "llm.model")
            default (Any): Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Args:
            key (str): Configuration key (e.g., "llm.model")
            value (Any): Value to set
        """
        keys = key.split('.')
        self._set_nested_value(self.config, keys, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section (str): Section name
            
        Returns:
            Dict[str, Any]: Section configuration
        """
        return self.config.get(section, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get full configuration as dictionary.
        
        Returns:
            Dict[str, Any]: Complete configuration
        """
        return self.config.copy()
    
    def save_config(self, output_file: str):
        """
        Save current configuration to YAML file.
        
        Args:
            output_file (str): Output file path
        """
        with open(output_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)

# Global configuration instance
_config_manager = None

def get_config() -> ConfigManager:
    """
    Get global configuration manager instance.
    
    Returns:
        ConfigManager: Global configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reload_config(config_file: Optional[str] = None):
    """
    Reload global configuration.
    
    Args:
        config_file (Optional[str]): Configuration file to load
    """
    global _config_manager
    _config_manager = ConfigManager(config_file)
