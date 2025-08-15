# Contributing to IaC-Gen-DSPy

We love your input! We want to make contributing to IaC-Gen-DSPy as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, track issues and feature requests, and accept pull requests.

### Quick Start for Contributors

1. **Fork the repository**
```bash
# Fork via GitHub UI, then clone your fork
git clone https://github.com/your-username/IaC-Gen-DSPy.git
cd IaC-Gen-DSPy
```

2. **Set up development environment**
```bash
# Create virtual environment
python -m venv dev-env
source dev-env/bin/activate # On Windows: dev-env\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

3. **Create a feature branch**
```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
```

4. **Make your changes and test**
```bash
# Run tests
python -m pytest

# Run code quality checks
black src/ examples/ tests/
flake8 src/ examples/ tests/
mypy src/
```

5. **Commit and push**
```bash
git add .
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

6. **Create Pull Request**
- Go to GitHub and create a pull request
- Fill out the PR template
- Wait for review and feedback

## Code Style

### Python Style Guide

- We use [Black](https://black.readthedocs.io/) for code formatting
- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](https://mypy.readthedocs.io/) for type checking

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```bash
feat(core): add support for Azure resources
fix(validation): handle terraform init timeout
docs: update installation instructions
test(metrics): add benchmarking tests
```

## Testing

### Test Structure

```
tests/
├── unit/ # Unit tests for individual modules
├── integration/ # Integration tests
├── benchmarks/ # Performance benchmarks
└── fixtures/ # Test data and fixtures
```

### Running Tests

```bash
# All tests
python -m pytest

# With coverage
python -m pytest --cov=src/iac_gen_dspy

# Specific test files
python -m pytest tests/unit/test_generator.py

# Specific test functions
python -m pytest tests/unit/test_generator.py::test_basic_generation
```

### Writing Tests

```python
# Example unit test
import pytest
from iac_gen_dspy.core.generator import IaCGenerator

def test_generator_initialization():
generator = IaCGenerator(max_retries=2, use_rag=True)
assert generator.max_retries == 2
assert generator.use_rag is True

def test_generator_basic_functionality():
generator = IaCGenerator(max_retries=1, use_rag=False)
# Mock the actual generation for unit tests
# ... test implementation
```

## Documentation

### Docstring Style

We use Google-style docstrings:

```python
def generate_infrastructure(prompt: str, config: dict) -> str:
"""
Generate infrastructure code from natural language prompt.

Args:
prompt (str): Natural language description of infrastructure
config (dict): Configuration parameters for generation

Returns:
str: Generated Terraform HCL code

Raises:
ValidationError: If the generated code fails validation

Example:
>>> generator = IaCGenerator()
>>> code = generator.generate_infrastructure(
... "Create an S3 bucket", 
... {"use_rag": True}
... )
>>> print(code)
resource "aws_s3_bucket" "main" { ... }
"""
```

### Documentation Updates

- Update docstrings when changing function signatures
- Add examples in docstrings for public APIs
- Update README.md for significant features
- Update configuration documentation for new settings

## Issue Guidelines

### Bug Reports

Use the bug report template and include:

- **Environment information** (OS, Python version, dependencies)
- **Reproduction steps** (minimal example that reproduces the issue)
- **Expected behavior** vs **actual behavior**
- **Error messages and stack traces**
- **Configuration files** (if relevant)

### Feature Requests

Use the feature request template and include:

- **Clear description** of the feature
- **Use case** and motivation
- **Proposed implementation** (if you have ideas)
- **Potential breaking changes**

### Questions and Discussions

For questions and discussions, use [GitHub Discussions](https://github.com/your-org/IaC-Gen-DSPy/discussions) instead of issues.

## Code Contribution Areas

### High Impact Areas

1. **Core Generation Logic** (`src/iac_gen_dspy/core/`)
- DSPy optimization improvements
- Better error handling and retry logic
- Support for new cloud providers

2. **RAG System** (`src/iac_gen_dspy/rag/`)
- Better keyword extraction
- Semantic similarity matching
- Knowledge base optimization

3. **Validation System** (`src/iac_gen_dspy/validation/`)
- Additional validation rules
- Policy-as-code integration
- Multi-provider validation

4. **Metrics and Benchmarking** (`src/iac_gen_dspy/metrics/`)
- New evaluation metrics
- Performance optimizations
- Comparative analysis tools

### Beginner-Friendly Areas

1. **Documentation improvements**
2. **Example scripts and tutorials**
3. **Test coverage improvements**
4. **Configuration options**
5. **Error message improvements**

## Performance Guidelines

### Code Performance

- Profile code changes that might affect performance
- Include benchmarks for performance-critical features
- Use appropriate data structures and algorithms
- Consider memory usage for large datasets

### Benchmark Testing

```bash
# Run performance benchmarks
python scripts/run_benchmarks.py --benchmark efficiency

# Profile specific functions
python -m cProfile -o profile.stats your_script.py
```

## Security Guidelines

### API Keys and Secrets

- Never commit API keys or secrets
- Use environment variables or config files
- Add sensitive files to `.gitignore`
- Use placeholder values in examples

### Input Validation

- Validate all user inputs
- Sanitize data before processing
- Handle edge cases gracefully
- Consider security implications of generated code

## Release Process

### Version Management

We use [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Release Checklist

- [ ] Update version in `src/iac_gen_dspy/__init__.py`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community discussions
- **Discord**: Real-time chat and community support
- **Email**: maintainers@iac-gen-dspy.org

### Maintainer Response Times

- **Bug fixes**: 1-3 business days
- **Feature requests**: 1-2 weeks
- **Pull reviews**: 2-5 business days
- **Questions**: 1-2 business days

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned with this Code of Conduct.

## Recognition

Contributors will be recognized in:
- **AUTHORS.md** file
- **GitHub contributors** section
- **Release notes** for significant contributions
- **Community highlights** in our newsletter

Thank you for contributing to IaC-Gen-DSPy! 
