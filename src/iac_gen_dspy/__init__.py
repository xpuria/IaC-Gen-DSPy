"""
IaC Gen DSPy - Infrastructure as Code Generation with DSPy Framework

A powerful toolkit for generating Infrastructure as Code using Large Language Models
with DSPy optimization framework, RAG integration, and comprehensive validation.
"""

__version__ = "0.2.0"
__author__ = "IaC-Gen-DSPy Team"

# Lazy attribute loading keeps import time light and avoids circular deps.
__all__ = ["IaCGenerator", "RAGStore", "TerraformValidator", "MetricsEvaluator"]


def __getattr__(name):
    if name == "IaCGenerator":
        from .core.generator import IaCGenerator as _IaCGenerator

        return _IaCGenerator
    if name == "RAGStore":
        from .rag.store import RAGStore as _RAGStore

        return _RAGStore
    if name == "TerraformValidator":
        from .validation.validator import TerraformValidator as _TerraformValidator

        return _TerraformValidator
    if name == "MetricsEvaluator":
        from .metrics.evaluator import MetricsEvaluator as _MetricsEvaluator

        return _MetricsEvaluator
    raise AttributeError(f"module {__name__} has no attribute {name}")
