"""
Data models for FileSystemPlugin.

This module contains all the Pydantic models used for structured data
representation in the FileSystemPlugin.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class PluginResponse(BaseModel):
    """Standard response format for all plugin functions."""

    success: bool = Field(description="Whether the operation succeeded")
    data: Optional[Any] = Field(description="The actual result data")
    error: Optional[str] = Field(description="Error message if operation failed")
    suggestions: List[str] = Field(
        default_factory=list, description="Helpful suggestions for next steps"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context and statistics"
    )


class FileInfo(BaseModel):
    """Structured file information."""

    path: str = Field(description="Relative path from base directory")
    name: str = Field(description="File name without path")
    extension: str = Field(description="File extension including dot (e.g., '.py')")
    type: str = Field(
        description="File type category (e.g., 'python', 'config', 'documentation')"
    )


class DirectoryInfo(BaseModel):
    """Structured directory information."""

    path: str = Field(description="Relative path from base directory")
    name: str = Field(description="Directory name")
    file_count: int = Field(description="Number of direct files")
    dir_count: int = Field(description="Number of subdirectories")
    total_size: Optional[int] = Field(
        default=None, description="Total size in bytes (if calculated)"
    )


class SearchMatch(BaseModel):
    """Structured search result."""

    file: FileInfo = Field(description="File containing the match")
    line_number: int = Field(description="Line number (1-indexed)")
    line_content: str = Field(description="Full line content")
    match_text: str = Field(description="The specific matched text")
    context_before: Optional[str] = Field(description="Line before the match")
    context_after: Optional[str] = Field(description="Line after the match")


# File type mappings for semantic categorization
FILE_TYPE_MAPPINGS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".json": "config",
    ".yaml": "config",
    ".yml": "config",
    ".toml": "config",
    ".xml": "config",
    ".ini": "config",
    ".env": "config",
    ".tf": "infrastructure",
    ".tfvars": "infrastructure",
    ".md": "documentation",
    ".rst": "documentation",
    ".txt": "text",
    ".log": "log",
    ".sh": "script",
    ".bat": "script",
    ".ps1": "script",
    ".dockerfile": "container",
    ".dockerignore": "container",
}
