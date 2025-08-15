"""
IaC Gen DSPy - Infrastructure as Code Generation with DSPy Framework

A powerful toolkit for generating Infrastructure as Code using Large Language Models
with DSPy optimization framework, RAG integration, and comprehensive validation.
"""

__version__ = "0.2.0"
__author__ = "IaC-Gen-DSPy Team"

# Import components individually to avoid circular dependencies
from .core.generator import IaCGenerator
from .rag.store import RAGStore
from .validation.validator import TerraformValidator
from .metrics.evaluator import MetricsEvaluator

# Import IaCWorkflow separately to avoid circular imports
# from .core.workflow import IaCWorkflow

__all__ = [
    "IaCGenerator",
    # "IaCWorkflow",  # Import directly from .core.workflow when needed
    "RAGStore",
    "TerraformValidator",
    "MetricsEvaluator"
]
