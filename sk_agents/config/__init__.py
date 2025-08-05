"""
Configuration module for SK Agents

Provides settings and constants for the framework.
"""

from .settings import (
    MAX_ROUNDS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TIMEOUT,
    get_env_var,
    require_env_var
)

__all__ = [
    "MAX_ROUNDS",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_TIMEOUT",
    "get_env_var",
    "require_env_var"
]