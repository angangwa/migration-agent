"""
FileSystemPlugin v2 - Backward compatibility import.

This file maintains backward compatibility by importing the FileSystemPlugin
from the new modular structure.
"""

# Import from the modular structure
from tools.file_system import FileSystemPlugin  # pylint: disable=import-self

__all__ = ['FileSystemPlugin']