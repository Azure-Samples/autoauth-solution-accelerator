"""Adapters that plug new agent runs into the existing evaluators and YAML cases."""

from src.evals.adapters.runners import get_runner, runner_mode

__all__ = ["get_runner", "runner_mode"]
