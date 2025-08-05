"""
Custom Group Chat Managers for SK Agents

This module contains custom group chat managers that extend
the base Semantic Kernel GroupChatManager functionality.
"""

from .single_agent import SingleAgentGroupChatManager

__all__ = [
    "SingleAgentGroupChatManager"
]