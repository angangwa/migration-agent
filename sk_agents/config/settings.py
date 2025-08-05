"""
Settings Module

Environment variables and configuration constants for SK Agents.
"""

import os
from typing import Optional, Any


# Orchestration Settings
MAX_ROUNDS = 20  # Maximum rounds for group chat orchestration
DEFAULT_TIMEOUT = 600  # Default timeout in seconds (10 minutes)

# Model Settings
DEFAULT_REASONING_EFFORT = "high"  # Default reasoning effort for o-models
DEFAULT_CHAT_MODEL = "gpt-4.1"  # Default chat model deployment
DEFAULT_REASONING_MODEL = "o4-mini"  # Default reasoning model deployment

# Response Settings
MAX_RESPONSE_LENGTH = 10000  # Maximum response length to display
TRUNCATE_RESPONSES = True  # Whether to truncate long responses in callbacks

# Plugin Settings
DEFAULT_BASE_PATH = "."  # Default base path for FileSystemPlugin


def get_env_var(
    var_name: str,
    default: Optional[Any] = None,
    var_type: type = str
) -> Optional[Any]:
    """
    Get environment variable with optional type conversion.
    
    Args:
        var_name: Environment variable name
        default: Default value if not set
        var_type: Type to convert to (str, int, bool, float)
        
    Returns:
        Environment variable value or default
        
    Example:
        timeout = get_env_var("SK_TIMEOUT", 600, int)
        debug = get_env_var("SK_DEBUG", False, bool)
    """
    value = os.getenv(var_name)
    
    if value is None:
        return default
    
    if var_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    elif var_type == int:
        try:
            return int(value)
        except ValueError:
            return default
    elif var_type == float:
        try:
            return float(value)
        except ValueError:
            return default
    else:
        return value


def require_env_var(var_name: str) -> str:
    """
    Get required environment variable or raise error.
    
    Args:
        var_name: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable not set
    """
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(
            f"Required environment variable '{var_name}' is not set. "
            f"Please configure your .env file."
        )
    return value


# Load settings from environment with defaults
MAX_ROUNDS = get_env_var("SK_MAX_ROUNDS", MAX_ROUNDS, int)
DEFAULT_TIMEOUT = get_env_var("SK_TIMEOUT", DEFAULT_TIMEOUT, int)
DEFAULT_REASONING_EFFORT = get_env_var("SK_REASONING_EFFORT", DEFAULT_REASONING_EFFORT)
MAX_RESPONSE_LENGTH = get_env_var("SK_MAX_RESPONSE_LENGTH", MAX_RESPONSE_LENGTH, int)
TRUNCATE_RESPONSES = get_env_var("SK_TRUNCATE_RESPONSES", TRUNCATE_RESPONSES, bool)