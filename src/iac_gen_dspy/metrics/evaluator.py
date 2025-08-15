"""
Comprehensive metrics and evaluation system for IaC generation.
"""
import dspy
import time
import json
from typing import List, Dict, Any, Tuple
from ..validation.validator import TerraformValidator
from ..data.utils import load_iac_dataset

def iac_validation_metric(gold: dspy.Example, pred_iac_code: str, trace=None) -> float:
"""
Core validation metric for IaC generation quality.

Args:
gold (dspy.Example): Gold standard example with expected output
pred_iac_code (str): Generated IaC code to validate
trace: Optional trace information (unused)

Returns:
float: Score between 0.0 and 1.0
"""
if not pred_iac_code or not pred_iac_code.strip():
print(f"Metric: Empty prediction for prompt: '{gold.prompt[:50]}...' -> Score: 0.0")
return 0.0

validator = TerraformValidator()
is_valid, error_msg = validator.terraform_validate(pred_iac_code)
score = 1.0 if is_valid else 0.0

print(f"Metric: Prompt: '{gold.prompt[:50]}...' -> Valid (TF CLI): {is_valid}, Score: {score}")
return score

class MetricsEvaluator:
"""
Comprehensive metrics evaluation system for IaC generation.

Provides detailed performance analysis including validation rates,
generation quality, efficiency metrics, and comparative benchmarks.
"""

def __init__(self):
self.validator = TerraformValidator()
self.results_history = []

def evaluate_generator(self, generator, test_examples: List[dspy.Example], 
detailed: bool = True) -> Dict[str, Any]:
"""
Comprehensive evaluation of an IaC generator.

Args:
generator: The IaC generator to evaluate
test_examples: List of test examples
detailed: Whether to include detailed per-example results

Returns:
Dict[str, Any]: Comprehensive evaluation results
"""
print(f"\n Starting comprehensive evaluation on {len(test_examples)} examples...")

start_time = time.time()
results = {
'evaluation_metadata': {
'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
'total_examples': len(test_examples),
'detailed_analysis': detailed
},
'performance_metrics': {},
'quality_metrics': {},
'efficiency_metrics': {},
'detailed_results': [] if detailed else None
}

# Core metrics tracking
total_score = 0.0
successful_generations = 0
total_attempts = 0
total_generation_time = 0.0
rag_usage_count = 0
validation_failures = []

for i, example in enumerate(test_examples):
print(f"\n--- Evaluating Example {i+1}/{len(test_examples)} ---")
print(f"Prompt: {example.prompt[:100]}...")

example_start_time = time.time()

try:
# Generate IaC code
if hasattr(generator, 'history'):
generator.history = []

generated_code = generator(prompt=example.prompt)
generation_time = time.time() - example_start_time
total_generation_time += generation_time

# Evaluate the generated code
score = iac_validation_metric(example, generated_code)
total_score += score

if score > 0:
successful_generations += 1

# Get generation metrics if available
gen_metrics = {}
if hasattr(generator, 'get_generation_metrics'):
gen_metrics = generator.get_generation_metrics()
total_attempts += gen_metrics.get('total_attempts', 1)

if gen_metrics.get('rag_used', False):
rag_usage_count += 1
else:
total_attempts += 1

# Track validation failures
if score == 0:
is_valid, error_msg = self.validator.terraform_validate(generated_code)
validation_failures.append({
'example_index': i,
'prompt': example.prompt[:100],
'error': error_msg
})

# Detailed per-example results
if detailed:
results['detailed_results'].append({
'example_index': i,
'prompt': example.prompt,
'generated_code': generated_code,
'expected_code': example.expected_iac_code,
'score': score,
'generation_time_seconds': round(generation_time, 3),
'generation_metrics': gen_metrics
})

print(f" Score: {score:.2f}, Time: {generation_time:.2f}s")

except Exception as e:
print(f" Error: {e}")
validation_failures.append({
'example_index': i,
'prompt': example.prompt[:100],
'error': str(e)
})

if detailed:
results['detailed_results'].append({
'example_index': i,
'prompt': example.prompt,
'error': str(e),
'score': 0.0,
'generation_time_seconds': 0.0
})

total_time = time.time() - start_time

# Calculate comprehensive metrics
avg_score = total_score / len(test_examples) if test_examples else 0.0
success_rate = successful_generations / len(test_examples) if test_examples else 0.0
avg_attempts = total_attempts / len(test_examples) if test_examples else 0.0
rag_usage_rate = rag_usage_count / len(test_examples) if test_examples else 0.0
avg_generation_time = total_generation_time / len(test_examples) if test_examples else 0.0

# Performance metrics
results['performance_metrics'] = {
'average_validation_score': round(avg_score, 4),
'success_rate_percentage': round(success_rate * 100, 2),
'successful_generations': successful_generations,
'failed_generations': len(test_examples) - successful_generations,
'total_examples_evaluated': len(test_examples)
}

# Quality metrics
results['quality_metrics'] = {
'terraform_cli_validation_rate': round(success_rate * 100, 2),
'average_attempts_per_example': round(avg_attempts, 2),
'rag_utilization_rate_percentage': round(rag_usage_rate * 100, 2),
'validation_failure_count': len(validation_failures),
'common_failure_patterns': self._analyze_failure_patterns(validation_failures)
}

# Efficiency metrics
results['efficiency_metrics'] = {
'total_evaluation_time_seconds': round(total_time, 2),
'average_generation_time_seconds': round(avg_generation_time, 3),
'throughput_examples_per_minute': round((len(test_examples) / total_time) * 60, 2),
'time_per_successful_generation_seconds': round(
total_generation_time / successful_generations, 3
) if successful_generations > 0 else None
}

# Store results for later analysis
self.results_history.append(results)

# Print summary
self._print_evaluation_summary(results)

return results

def _analyze_failure_patterns(self, failures: List[Dict]) -> List[Dict[str, Any]]:
"""Analyze common patterns in validation failures."""
if not failures:
return []

error_patterns = {}
for failure in failures:
error = failure.get('error', 'Unknown error')
# Extract key error patterns
if 'missing' in error.lower():
pattern = 'Missing required fields'
elif 'syntax' in error.lower() or 'invalid' in error.lower():
pattern = 'Syntax errors'
elif 'terraform init failed' in error.lower():
pattern = 'Terraform init failures'
elif 'empty' in error.lower():
pattern = 'Empty outputs'
else:
pattern = 'Other validation errors'

error_patterns[pattern] = error_patterns.get(pattern, 0) + 1

return [{'pattern': k, 'count': v, 'percentage': round((v/len(failures))*100, 1)} 
for k, v in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)]

def _print_evaluation_summary(self, results: Dict[str, Any]):
"""Print a comprehensive evaluation summary."""
print(f"\n{'='*60}")
print(f" EVALUATION SUMMARY")
print(f"{'='*60}")

perf = results['performance_metrics']
quality = results['quality_metrics']
efficiency = results['efficiency_metrics']

print(f" Performance Metrics:")
print(f" • Success Rate: {perf['success_rate_percentage']:.2f}% ({perf['successful_generations']}/{perf['total_examples_evaluated']})")
print(f" • Average Validation Score: {perf['average_validation_score']:.4f}")
print(f" • Failed Generations: {perf['failed_generations']}")

print(f"\n Quality Metrics:")
print(f" • Terraform CLI Validation Rate: {quality['terraform_cli_validation_rate']:.2f}%")
print(f" • Average Attempts per Example: {quality['average_attempts_per_example']:.2f}")
print(f" • RAG Utilization Rate: {quality['rag_utilization_rate_percentage']:.2f}%")
print(f" • Validation Failures: {quality['validation_failure_count']}")

print(f"\n⚡ Efficiency Metrics:")
print(f" • Total Evaluation Time: {efficiency['total_evaluation_time_seconds']:.2f}s")
print(f" • Average Generation Time: {efficiency['average_generation_time_seconds']:.3f}s")
print(f" • Throughput: {efficiency['throughput_examples_per_minute']:.2f} examples/min")

if quality['common_failure_patterns']:
print(f"\n Common Failure Patterns:")
for pattern in quality['common_failure_patterns'][:3]:
print(f" • {pattern['pattern']}: {pattern['count']} ({pattern['percentage']:.1f}%)")

def generate_metrics_report(self, output_file: str = "metrics_report.json"):
"""
Generate a comprehensive metrics report file.

Args:
output_file: Path to save the metrics report
"""
if not self.results_history:
print("No evaluation results available to generate report.")
return

latest_results = self.results_history[-1]

# Create sharable metrics summary
report = {
"project_info": {
"name": "IaC-Gen-DSPy",
"description": "Infrastructure as Code Generation with DSPy Framework",
"evaluation_date": latest_results['evaluation_metadata']['timestamp'],
"version": "0.2.0"
},
"key_metrics": {
"success_rate_percentage": latest_results['performance_metrics']['success_rate_percentage'],
"average_validation_score": latest_results['performance_metrics']['average_validation_score'],
"terraform_cli_validation_rate": latest_results['quality_metrics']['terraform_cli_validation_rate'],
"average_generation_time_seconds": latest_results['efficiency_metrics']['average_generation_time_seconds'],
"rag_utilization_rate": latest_results['quality_metrics']['rag_utilization_rate_percentage'],
"examples_evaluated": latest_results['evaluation_metadata']['total_examples']
},
"detailed_results": latest_results
}

with open(output_file, 'w') as f:
json.dump(report, f, indent=2)

print(f" Metrics report saved to: {output_file}")
return report
