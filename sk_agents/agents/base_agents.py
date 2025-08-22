"""
Base Agent Creation Module

Provides helper functions for creating and configuring Semantic Kernel agents.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Any, Dict
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase


def create_agent(
    name: str,
    service: ChatCompletionClientBase,
    description: Optional[str] = None,
    instructions: Optional[str] = None,
    plugins: Optional[List[Any]] = None,
    **kwargs
) -> ChatCompletionAgent:
    """
    Create a ChatCompletionAgent with the specified configuration.
    
    This is a simple wrapper around ChatCompletionAgent that provides
    consistent defaults and parameter handling.
    
    Args:
        name: Agent name
        service: Chat completion service (from services.llm)
        description: Agent description for orchestration
        instructions: Agent system instructions
        plugins: List of plugins to add to the agent
        **kwargs: Additional arguments passed to ChatCompletionAgent
        
    Returns:
        Configured ChatCompletionAgent
        
    Example:
        from sk_agents.services import get_reasoning_service
        from sk_agents.agents import create_agent
        
        service = get_reasoning_service()
        agent = create_agent(
            name="Analyzer",
            service=service,
            description="Code analysis agent",
            instructions="Analyze code thoroughly",
            plugins=[FileSystemPlugin()]
        )
    """
    agent_kwargs = {
        "name": name,
        "service": service
    }
    
    if description:
        agent_kwargs["description"] = description
    
    if instructions:
        agent_kwargs["instructions"] = instructions
        
    if plugins:
        agent_kwargs["plugins"] = plugins
    
    # Add any additional kwargs
    agent_kwargs.update(kwargs)
    
    return ChatCompletionAgent(**agent_kwargs)


def get_agent_config(config_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load agent configuration from YAML file.
    
    Args:
        config_name: Name of the agent configuration to load
        config_path: Optional path to config file (defaults to configs/agents.yaml)
        
    Returns:
        Dictionary containing agent configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If config_name not found in file
    """
    if config_path is None:
        # Default to configs/agents.yaml in the same directory
        config_path = Path(__file__).parent / "configs" / "agents.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        configs = yaml.safe_load(f)
    
    if config_name not in configs:
        available = ", ".join(configs.keys())
        raise KeyError(
            f"Configuration '{config_name}' not found. "
            f"Available configurations: {available}"
        )
    
    return configs[config_name]


def load_agent_from_config(
    config_name: str,
    service: ChatCompletionClientBase,
    plugins: Optional[List[Any]] = None,
    config_path: Optional[str] = None,
    
    **override_kwargs
) -> ChatCompletionAgent:
    """
    Create an agent from a YAML configuration.
    
    Args:
        config_name: Name of the agent configuration to load
        service: Chat completion service to use
        plugins: Optional list of plugins (overrides config)
        config_path: Optional path to config file
        **override_kwargs: Additional kwargs to override config values
        
    Returns:
        Configured ChatCompletionAgent
        
    Example:
        from sk_agents.services import get_reasoning_service
        from sk_agents.agents import load_agent_from_config
        
        service = get_reasoning_service()
        agent = load_agent_from_config(
            "codebase_analysis",
            service=service,
            plugins=[FileSystemPlugin()]
        )
    """
    # Load configuration
    config = get_agent_config(config_name, config_path)
    
    # Extract agent parameters
    agent_params = {
        "name": config.get("name", config_name),
        "service": service,
        "description": config.get("description"),
        "instructions": config.get("instructions")
    }
    
    # Handle plugins
    if plugins is not None:
        agent_params["plugins"] = plugins
    elif "plugins" in config:
        # Note: Plugin instantiation from config would need to be implemented
        # For now, plugins must be passed explicitly
        pass
    
    # Apply any overrides
    agent_params.update(override_kwargs)
    
    return create_agent(**agent_params)


def create_agent_team(
    team_config: Dict[str, Dict],
    services: Dict[str, ChatCompletionClientBase],
    default_service: Optional[ChatCompletionClientBase] = None
) -> List[ChatCompletionAgent]:
    """
    Create a team of agents from a configuration dictionary.
    
    Args:
        team_config: Dictionary of agent configurations
        services: Dictionary mapping service names to service instances
        default_service: Default service if not specified in config
        
    Returns:
        List of configured agents
        
    Example:
        team_config = {
            "analyzer": {
                "name": "CodeAnalyzer",
                "service": "reasoning",
                "description": "Analyzes code",
                "instructions": "..."
            },
            "reviewer": {
                "name": "CodeReviewer",
                "service": "chat",
                "description": "Reviews code",
                "instructions": "..."
            }
        }
        
        services = {
            "reasoning": get_reasoning_service(),
            "chat": get_chat_service()
        }
        
        team = create_agent_team(team_config, services)
    """
    agents = []
    
    for agent_id, config in team_config.items():
        # Determine which service to use
        service_name = config.get("service")
        if service_name and service_name in services:
            service = services[service_name]
        elif default_service:
            service = default_service
        else:
            raise ValueError(
                f"No service specified for agent '{agent_id}' "
                f"and no default service provided"
            )
        
        # Create agent
        agent = create_agent(
            name=config.get("name", agent_id),
            service=service,
            description=config.get("description"),
            instructions=config.get("instructions"),
            plugins=config.get("plugins", [])
        )
        
        agents.append(agent)
    
    return agents