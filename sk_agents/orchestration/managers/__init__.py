"""
Custom Group Chat Managers for SK Agents

This module contains custom group chat managers that extend
the base Semantic Kernel GroupChatManager functionality.
"""

from .single_agent import SingleAgentGroupChatManager
from .discovery_agent_manager import DiscoveryAgentGroupChatManager

__all__ = [
    "SingleAgentGroupChatManager",
    "DiscoveryAgentGroupChatManager"
]