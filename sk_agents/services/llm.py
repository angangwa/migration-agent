"""
LLM Service Configuration Module

Provides Azure-only service configuration for different models.
Supports both reasoning models (o1, o3, o4-mini) and standard models.

Environment Variable Pattern:
    AZURE_<DEPLOYMENT_NAME>_ENDPOINT
    AZURE_<DEPLOYMENT_NAME>_API_KEY
    
Where DEPLOYMENT_NAME is uppercase with hyphens/dots replaced by underscores.
Example: deployment "o4-mini" uses AZURE_O4_MINI_ENDPOINT and AZURE_O4_MINI_API_KEY
"""

import os
from typing import Optional, Literal
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings
)


def _deployment_to_env_prefix(deployment_name: str) -> str:
    """
    Convert deployment name to environment variable prefix.
    
    Examples:
        o4-mini -> O4_MINI
        gpt-4.1 -> GPT_4_1
        o4-mini-custom -> O4_MINI_CUSTOM
    """
    return deployment_name.upper().replace('-', '_').replace('.', '_')


def _is_reasoning_model(deployment_name: str) -> bool:
    """
    Check if a deployment name is for a reasoning model.
    Reasoning models start with 'o' followed by a digit (o1, o3, o4-mini, etc.)
    """
    name_lower = deployment_name.lower()
    return (
        name_lower.startswith('o') and 
        len(name_lower) > 1 and 
        name_lower[1].isdigit()
    )


def get_service(
    deployment_name: str,
    reasoning: Optional[Literal["low", "medium", "high"]] = None,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    service_id: Optional[str] = None,
    **settings_kwargs
):
    """
    Get Azure chat service for any model deployment.
    
    Args:
        deployment_name: Azure deployment name (e.g., "o4-mini", "gpt-4.1", "o4-mini-custom")
        reasoning: Reasoning effort level (only for reasoning models starting with 'o')
        endpoint: Azure endpoint (if not provided, uses env vars)
        api_key: Azure API key (if not provided, uses env vars)
        service_id: Optional service ID (defaults to deployment name)
        **settings_kwargs: Additional settings passed to execution settings
        
    Returns:
        Configured Azure chat service
        
    Raises:
        ValueError: If reasoning is specified for non-reasoning model or configuration is invalid
        
    Environment Variables:
        The function looks for environment variables in this pattern:
        - AZURE_<DEPLOYMENT_NAME>_ENDPOINT
        - AZURE_<DEPLOYMENT_NAME>_API_KEY
        
        If not found, falls back to:
        - AZURE_DEFAULT_ENDPOINT
        - AZURE_DEFAULT_API_KEY
    """
    # Check if this is a reasoning model
    is_reasoning = _is_reasoning_model(deployment_name)
    
    # Validate reasoning parameter
    if reasoning is not None and not is_reasoning:
        raise ValueError(
            f"Reasoning effort specified for non-reasoning model '{deployment_name}'. "
            f"Reasoning is only supported for models starting with 'o' followed by a digit "
            f"(e.g., o1, o3, o4-mini)"
        )
    
    # Set default reasoning effort for reasoning models
    if is_reasoning and reasoning is None:
        reasoning = "high"
    
    # Get credentials from environment if not provided
    if not endpoint or not api_key:
        env_prefix = _deployment_to_env_prefix(deployment_name)
        
        # Try model-specific environment variables
        model_endpoint = os.getenv(f"AZURE_{env_prefix}_ENDPOINT")
        model_api_key = os.getenv(f"AZURE_{env_prefix}_API_KEY")
        
        if model_endpoint and model_api_key:
            endpoint = endpoint or model_endpoint
            api_key = api_key or model_api_key
        else:
            # Fall back to default credentials
            default_endpoint = os.getenv("AZURE_DEFAULT_ENDPOINT")
            default_api_key = os.getenv("AZURE_DEFAULT_API_KEY")
            
            if default_endpoint and default_api_key:
                endpoint = endpoint or default_endpoint
                api_key = api_key or default_api_key
    
    # Validate we have required credentials
    if not endpoint:
        env_prefix = _deployment_to_env_prefix(deployment_name)
        raise ValueError(
            f"Azure endpoint not configured for deployment '{deployment_name}'. "
            f"Please provide endpoint parameter or set one of:\n"
            f"  - AZURE_{env_prefix}_ENDPOINT (model-specific)\n"
            f"  - AZURE_DEFAULT_ENDPOINT (fallback)\n"
            f"in your .env file."
        )
    
    if not api_key:
        env_prefix = _deployment_to_env_prefix(deployment_name)
        raise ValueError(
            f"Azure API key not configured for deployment '{deployment_name}'. "
            f"Please provide api_key parameter or set one of:\n"
            f"  - AZURE_{env_prefix}_API_KEY (model-specific)\n"
            f"  - AZURE_DEFAULT_API_KEY (fallback)\n"
            f"in your .env file."
        )
    
    # Build service configuration
    service_kwargs = {
        "api_key": api_key,
        "endpoint": endpoint,
        "deployment_name": deployment_name,
        "service_id": service_id or deployment_name
    }
    
    # Add instruction role for reasoning models
    if is_reasoning:
        service_kwargs["instruction_role"] = "developer"
    
    return AzureChatCompletion(**service_kwargs)


def get_execution_settings(
    deployment_name: str,
    reasoning: Optional[Literal["low", "medium", "high"]] = None,
    **kwargs
) -> AzureChatPromptExecutionSettings:
    """
    Get prompt execution settings for a deployment.
    
    Args:
        deployment_name: Azure deployment name
        reasoning: Reasoning effort level (only for reasoning models)
        **kwargs: Additional settings like max_completion_tokens
        
    Returns:
        Azure chat prompt execution settings
        
    Raises:
        ValueError: If reasoning is specified for non-reasoning model
    """
    # Check if this is a reasoning model
    is_reasoning = _is_reasoning_model(deployment_name)
    
    # Validate reasoning parameter
    if reasoning is not None and not is_reasoning:
        raise ValueError(
            f"Reasoning effort specified for non-reasoning model '{deployment_name}'. "
            f"Reasoning is only supported for models starting with 'o' followed by a digit "
            f"(e.g., o1, o3, o4-mini)"
        )
    
    # Build settings
    settings_dict = {}
    
    # Add reasoning effort if applicable
    if is_reasoning and reasoning:
        settings_dict["reasoning_effort"] = reasoning
    
    # Add any additional kwargs
    settings_dict.update(kwargs)
    
    return AzureChatPromptExecutionSettings(**settings_dict)


# Convenience functions for common configurations
def get_reasoning_service(
    deployment_name: str = "o4-mini",
    reasoning_effort: Literal["low", "medium", "high"] = "high",
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    **settings_kwargs
):
    """
    Get reasoning service with specified reasoning effort.
    
    Args:
        deployment_name: Deployment name for reasoning model (default: o4-mini)
        reasoning_effort: Reasoning effort level
        endpoint: Optional Azure endpoint
        api_key: Optional Azure API key
        **settings_kwargs: Additional settings
        
    Returns:
        Configured reasoning service
        
    Example:
        service = get_reasoning_service("o4-mini-custom", reasoning_effort="medium")
    """
    if not _is_reasoning_model(deployment_name):
        raise ValueError(
            f"'{deployment_name}' is not a reasoning model. "
            f"Reasoning models must start with 'o' followed by a digit."
        )
    
    return get_service(
        deployment_name=deployment_name,
        reasoning=reasoning_effort,
        endpoint=endpoint,
        api_key=api_key,
        service_id="reasoning",
        **settings_kwargs
    )


def get_chat_service(
    deployment_name: str = "gpt-4.1",
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    **settings_kwargs
):
    """
    Get standard chat service.
    
    Args:
        deployment_name: Deployment name (default: gpt-4.1)
        endpoint: Optional Azure endpoint
        api_key: Optional Azure API key
        **settings_kwargs: Additional settings
        
    Returns:
        Configured chat service
        
    Example:
        service = get_chat_service("gpt-4o-mini")
    """
    if _is_reasoning_model(deployment_name):
        raise ValueError(
            f"'{deployment_name}' appears to be a reasoning model. "
            f"Use get_reasoning_service() for reasoning models."
        )
    
    return get_service(
        deployment_name=deployment_name,
        endpoint=endpoint,
        api_key=api_key,
        service_id="chat",
        **settings_kwargs
    )