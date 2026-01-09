# envyeet - Agent Guidelines

This file contains guidelines for agentic coding assistants working on the envyeet project, a dependency-free Python script for merging environment variable files.

## Contract and Specification

**IMPORTANT**: `spec.md` is the authoritative specification for the CLI interface and behavior. All implementation details should align with the requirements outlined in `spec.md`.

- Use `spec.md` as the single source of truth for CLI behavior, flags, subcommands, and edge cases
- Any ambiguity in implementation should be resolved by referencing `spec.md`
- Test cases should be derived from examples in `spec.md`
- When making changes, ensure they don't violate the contract defined in `spec.md`

## Build/Lint/Test Commands

### Running Tests
```bash
# Run all tests
python3 -m unittest discover tests/

# Run a single test file
python3 -m unittest tests.test_envyeet

# Run a specific test class
python3 -m unittest tests.test_envyeet.TestEnvLine

# Run tests with verbose output
python3 -m unittest discover tests/ -v
```

### Linting and Formatting
```bash
# Run static type checking
python3 -m mypy .

# Run linting (if ruff/flake8 is added)
ruff check .
flake8 .

# Format code (if black/autopep8 is added)
black .
ruff format .
```

### Running the Script
```bash
# Run the main script
python3 envyeet.py

# With arguments
python3 envyeet.py file1.env file2.env --output merged.env
```

## Code Style Guidelines

### Python Version
- Target Python 3.8+ for broad compatibility
- Maintain dependency-free philosophy unless absolutely necessary

### Imports and Formatting
- Follow PEP 8 style guidelines
- Use absolute imports over relative imports
- Keep imports at the top of files, grouped in order: stdlib, third-party, local
- Use `isort` if added: `isort .`

### Type Annotations
- Use type hints for all function signatures
- Type variables and complex types should be imported from `typing`
- Prefer `from typing import Dict, List, Optional` over inline syntax for clarity
- Example:
  ```python
  def merge_env_files(files: List[str], output: Optional[str] = None) -> Dict[str, str]:
      pass
  ```

### Naming Conventions
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Error Handling
- Use specific exception types (ValueError, FileNotFoundError, etc.)
- Always wrap I/O operations with try/except blocks
- Provide clear, actionable error messages
- Example:
  ```python
  try:
      with open(filepath, 'r') as f:
          content = f.read()
  except FileNotFoundError:
      raise ValueError(f"Environment file not found: {filepath}")
  ```

### Documentation
- Use docstrings for all public functions and classes (Google or NumPy style)
- Keep docstrings concise but informative
- Include type information in docstrings even if type hints are present

### Environment File Handling
- Parse environment files line by line to handle large files
- Support both `KEY=VALUE` and `export KEY=VALUE` formats
- Skip comments (lines starting with `#`) and empty lines
- Handle quoted values correctly
- Later values should override earlier values (last-wins semantics)
- Preserve original order for determinism

### Testing
- Use `unittest` framework (built-in, no dependencies)
- Write unit tests for all public functions
- Test edge cases: empty files, malformed lines, duplicate keys
- Use `tempfile.TemporaryDirectory` for test file operations
- Aim for high test coverage (>80%)

### Command Line Interface
- Use `argparse` for CLI (built-in, no dependencies)
- Provide clear help text and examples
- Support `-h/--help` for usage information
- Use sensible defaults where appropriate
- Exit with appropriate exit codes (0 for success, 1 for errors)

### Performance
- Avoid unnecessary file reads or string operations
- Use generators/yield for large file processing
- Consider memory efficiency for large environment files
- Profile before optimizing

### Security
- Never log or print sensitive environment values
- Sanitize file paths to prevent path traversal
- Validate inputs before processing
- Warn about overwriting existing files

## Project Philosophy

- **Keep it simple**: Avoid unnecessary complexity
- **No dependencies**: Prefer stdlib solutions
- **Explicit is better than implicit**: Write clear, readable code
- **Backward compatible**: Don't break existing behavior
- **Well tested**: Maintain high test coverage
