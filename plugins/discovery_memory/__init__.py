"""
Discovery Memory Plugin

A comprehensive plugin for repository analysis and working memory management
designed for the Discovery Agent to analyze multiple code repositories and
categorize them into logical components.

This plugin combines repository analysis with persistent memory management
to provide efficient discovery and categorization of large enterprise codebases.
"""

from .plugin import DiscoveryMemoryPlugin

__all__ = ["DiscoveryMemoryPlugin"]