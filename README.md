# PyTofu

A simple Python package that prints "Hello tofu" via a console script.

## Installation

```bash
pip install pytofu
```

## Directory structure

```text
pytofu/
├── .gitignore
├── .vscode/
│   ├── launch.json
│   └── settings.json
├── LICENSE
├── README.md
├── pyproject.toml
├── src/
│   └── pytofu/
│       └── __init__.py
└── tests/
    └── test_hello.py
```


## Files

launch.json

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Python: PyTofu CLI",
            "type": "debugpy",
            "request": "launch",
            "module": "pytofu",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

settings.json

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true
    }
}
```

pyproject.toml

```toml
#### pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pytofu"
version = "0.1.0"
description = "A simple Python package that prints 'Hello tofu'."
readme = "README.md"
authors = [{ name = "Doe", email = "g41797l@gmail.com" }]
license = { file = "LICENSE" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
requires-python = ">=3.14"

[project.urls]
Homepage = "https://github.com/g41797l/pytofu"
Repository = "https://github.com/g41797l/pytofu.git"
Issues = "https://github.com/g41797l/pytofu/issues"

[project.scripts]
pytofu = "pytofu:main"
```

__init__.py

```python
def main() -> None:
    """Entry point for the pytofu console script."""
    print("Hello tofu")

if __name__ == "__main__":
    main()
```

test_hello.py

```python
from pytofu import main
from io import StringIO
import sys

def test_main(capsys):
    """Test that main prints 'Hello tofu'."""
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello tofu"
```

## Development

Open in VSCode for pre-configured settings (linting with mypy, formatting with black, testing with pytest).
Install dev deps: pip install -e .[dev] (add [dev] extras in pyproject.toml if needed).
Run tests: pytest

## Publishing to PyPI

Update version in pyproject.toml.
Build: python -m build
Upload: twine upload dist/*


## To test locally

```text
pip install -e 
pytofu
```
