#!/usr/bin/env python3
"""
Comprehensive benchmark runner for IaC-Gen-DSPy project.

This script runs various benchmarks to evaluate and showcase the capabilities
of the IaC generation system, producing sharable metrics and reports.
"""
import os
import sys
import argparse
import json
from dotenv import load_dotenv

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from iac_gen_dspy.metrics.benchmarks import BenchmarkSuite

def print_quick_summary(results):
    """Print a quick summary of benchmark results."""
    print(f"\n📊 Quick Summary:")

    if 'standard' in results:
        std = results['standard'].get('performance_results', {})
        success_rate = std.get('success_rate', 0) * 100
        avg_time = std.get('average_attempts_per_example', 0)
        print(f" • Standard Benchmark Success Rate: {success_rate:.1f}%")
        print(f" • Average Generation Time: {avg_time:.2f}s")

    if 'specialized' in results:
        spec = results['specialized'].get('summary', {})
        print(f" • Resource Types Tested: {spec.get('total_resource_types', 0)}")
        print(f" • Specialized Success Rate: {spec.get('average_success_rate', 0):.1f}%")

    if 'efficiency' in results:
        eff = results['efficiency'].get('best_configuration', {})
        print(f" • Best Configuration: {eff.get('name', 'Unknown')}")
        print(f" • Best Efficiency Score: {eff.get('efficiency_score', 0)}")

def main():
    """Main benchmark runner function."""
    parser = argparse.ArgumentParser(description='Run IaC generation benchmarks')
    parser.add_argument('--benchmark', 
                        choices=['standard', 'specialized', 'efficiency', 'all'], 
                        default='standard',
                        help='Type of benchmark to run')
    parser.add_argument('--examples', type=int, default=50,
                        help='Number of examples to use for standard benchmark')
    parser.add_argument('--api-key', type=str,
                        help='OpenAI API key (can also use OPENAI_API_KEY env var)')
    parser.add_argument('--output', type=str, default='benchmark_results.json',
                        help='Output file for benchmark results')
    parser.add_argument('--showcase', action='store_true',
                        help='Generate showcase report after benchmarks')

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OpenAI API key not found!")
        print("   Set OPENAI_API_KEY environment variable or use --api-key argument")
        sys.exit(1)

    print("🚀 IaC-Gen-DSPy Benchmark Suite")
    print("=" * 50)

    # Initialize benchmark suite
    benchmark_suite = BenchmarkSuite()

    try:
        if args.benchmark == 'standard' or args.benchmark == 'all':
            print(f"\n📊 Running Standard Benchmark...")
            standard_results = benchmark_suite.run_standard_benchmark(
                api_key=api_key, 
                num_examples=args.examples
            )
            print(f"✅ Standard benchmark completed!")

        if args.benchmark == 'specialized' or args.benchmark == 'all':
            print(f"\n🎯 Running Specialized Resource Benchmarks...")
            specialized_results = benchmark_suite.run_specialized_benchmarks(api_key=api_key)
            print(f"✅ Specialized benchmarks completed!")

        if args.benchmark == 'efficiency' or args.benchmark == 'all':
            print(f"\n⚡ Running Efficiency Benchmarks...")
            efficiency_results = benchmark_suite.run_efficiency_benchmark(api_key=api_key)
            print(f"✅ Efficiency benchmarks completed!")

        # Save benchmark results
        with open(args.output, 'w') as f:
            json.dump(benchmark_suite.benchmark_results, f, indent=2)
        print(f"\n💾 Benchmark results saved to: {args.output}")

        # Generate showcase report if requested
        if args.showcase:
            print(f"\n📄 Generating showcase report...")
            showcase_file = args.output.replace('.json', '_showcase.json')
            showcase_report = benchmark_suite.generate_showcase_report(showcase_file)
            print(f"✅ Showcase report generated!")

        print(f"\n✅ Benchmarks completed successfully!")
        print_quick_summary(benchmark_suite.benchmark_results)

    except Exception as e:
        print(f"❌ Error running benchmarks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
