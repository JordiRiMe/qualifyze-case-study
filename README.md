# Qualifyze Challenge
This repository contains the development behind the interview of Jordi Ripoll Melis. More details about the challenge in this [document](docs/2025_Case_Study__AI_Data_Scientist.docx.pdf).

# Repository

## Installation

For this use-case we are working with Python 3.13. Install it before running other commands and verify its version with `python --version`, checking it returns `Python 3.13.x`.

Install environment with the following sequence of commands:
```{bash}
uv sync
uv run pytest
uv run qualifyze-case-study
```

## Management

The repository libraries are managed with [uv](https://docs.astral.sh/uv/).

Tests are handled using [pytest](https://docs.pytest.org/en/stable/).

Linting is ran with [ruff](https://docs.astral.sh/ruff/).