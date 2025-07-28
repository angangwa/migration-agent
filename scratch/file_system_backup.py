"""
FileSystemPlugin
Implements best practices for tool design with consistent responses, helpful errors, and semantic outputs.
"""

import re
import json
import fnmatch
from pathlib import Path
from typing import List, Dict, Optional, Any, Annotated

from semantic_kernel.functions import kernel_function
from pydantic import BaseModel, Field, ConfigDict


# Standardized response structure for all functions
class PluginResponse(BaseModel):
    """Standard response format for all plugin functions."""
    success: bool = Field(description="Whether the operation succeeded")
    data: Optional[Any] = Field(description="The actual result data")
    error: Optional[str] = Field(description="Error message if operation failed")
    suggestions: List[str] = Field(default_factory=list, description="Helpful suggestions for next steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context and statistics")


# Semantic data structures for better LLM comprehension
class FileInfo(BaseModel):
    """Structured file information."""
    path: str = Field(description="Relative path from base directory")
    name: str = Field(description="File name without path")
    extension: str = Field(description="File extension including dot (e.g., '.py')")
    type: str = Field(description="File type category (e.g., 'python', 'config', 'documentation')")


class DirectoryInfo(BaseModel):
    """Structured directory information."""
    path: str = Field(description="Relative path from base directory")
    name: str = Field(description="Directory name")
    file_count: int = Field(description="Number of direct files")
    dir_count: int = Field(description="Number of subdirectories")
    total_size: Optional[int] = Field(default=None, description="Total size in bytes (if calculated)")


class SearchMatch(BaseModel):
    """Structured search result."""
    file: FileInfo = Field(description="File containing the match")
    line_number: int = Field(description="Line number (1-indexed)")
    line_content: str = Field(description="Full line content")
    match_text: str = Field(description="The specific matched text")
    context_before: Optional[str] = Field(description="Line before the match")
    context_after: Optional[str] = Field(description="Line after the match")


class FileSystemPlugin():
    """
    FileSystemPlugin v2 - Optimized for AI agents with consistent responses and helpful errors.
    All functions return a standardized PluginResponse with success status, data, errors, and suggestions.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    _base_path: Optional[Path] = None
    
    # File type mappings for semantic categorization
    FILE_TYPE_MAPPINGS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.json': 'config',
        '.yaml': 'config',
        '.yml': 'config',
        '.toml': 'config',
        '.xml': 'config',
        '.ini': 'config',
        '.env': 'config',
        '.tf': 'infrastructure',
        '.tfvars': 'infrastructure',
        '.md': 'documentation',
        '.rst': 'documentation',
        '.txt': 'text',
        '.log': 'log',
        '.sh': 'script',
        '.bat': 'script',
        '.ps1': 'script',
        '.dockerfile': 'container',
        '.dockerignore': 'container',
    }
    
    def __init__(self, base_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._base_path = Path(base_path) if base_path else Path.cwd()
    
    @kernel_function(
        name="find_files",
        description="""Finds files matching patterns and returns a list of file paths.
        Returns an optimized response with minimal redundancy for LLM usage.
        
        Success response includes:
        - List of file paths (relative to base directory)
        - Total count and truncation status
        - Smart suggestions based on results
        
        Error response includes:
        - Clear error message explaining the issue
        - Suggestions for fixing the problem
        - Alternative functions to try
        
        Examples:
        - find_files("*.py") → Find all Python files in current directory
        - find_files("**/*.py") → Find all Python files recursively
        - find_files("**/test_*.py") → Find all test files
        - find_files("src/**/*.{js,ts}") → Find JS/TS files in src (use multiple calls)"""
    )
    async def find_files(
        self,
        pattern: Annotated[str, "Glob pattern to match files (e.g., '*.py', '**/*.js')"],
        search_path: Annotated[str, "Directory to search in (default: '.')"] = ".",
        max_results: Annotated[int, "Maximum files to return (default: 100, max: 1000)"] = 100,
        exclude_patterns: Annotated[Optional[List[str]], "Patterns to exclude (e.g., ['.venv/*', 'node_modules/*'])"] = None
    ) -> Dict[str, Any]:
        """Find files with enhanced metadata and error handling."""
        try:
            # Validate and cap max_results
            max_results = min(max_results, 1000)
            
            search_dir = self._resolve_path(search_path)
            
            # Validate search directory
            if not search_dir.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Directory '{search_path}' does not exist",
                    suggestions=[
                        "Use list_directory() to see available directories",
                        "Check if the path is relative to the base directory",
                        f"Current base directory: {self._base_path}"
                    ]
                ).model_dump()
            
            if not search_dir.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{search_path}' is not a directory, it's a file",
                    suggestions=[
                        f"Use read_file('{search_path}') to read this file",
                        f"Use get_file_info('{search_path}') to get file metadata",
                        "Use list_directory() on the parent directory"
                    ]
                ).model_dump()
            
            # Find matching files
            files = []
            total_found = 0
            exclude_set = set(exclude_patterns or [])
            
            for file_path in self._find_files(search_dir, pattern):
                # Check if file should be excluded
                rel_path = str(file_path.relative_to(self._base_path))
                if self._should_exclude_file(rel_path, exclude_set):
                    continue
                    
                total_found += 1
                if len(files) < max_results:
                    # Just append the relative path as a string
                    files.append(rel_path)
            
            # Prepare response with smart suggestions
            suggestions = self._get_smart_find_suggestions(
                total_found, len(files), max_results, pattern, search_path
            )
            
            # Detect common excluded directories and suggest exclusion
            if not exclude_patterns:
                venv_found = any('.venv' in f for f in files[:10])
                node_modules_found = any('node_modules' in f for f in files[:10])
                if venv_found or node_modules_found:
                    exclude_suggestion = "Consider using exclude_patterns=['.venv/*', 'node_modules/*'] to filter out dependency directories"
                    suggestions.append(exclude_suggestion)
            
            # Deduplicate suggestions
            suggestions = self._deduplicate_suggestions(suggestions)
            
            return PluginResponse(
                success=True,
                data={
                    "files": files,
                    "count": len(files)
                },
                error=None,
                suggestions=suggestions,
                metadata={
                    "total_found": total_found,
                    "truncated": total_found > max_results
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)}",
                suggestions=[
                    "Check if the pattern is valid glob syntax",
                    "Verify you have read permissions for the directory",
                    "Try a simpler pattern first"
                ]
            ).model_dump()
    
    @kernel_function(
        name="list_directory",
        description="""Lists directory contents in a tree format similar to the Unix 'tree' command.
        Returns an optimized text-based tree structure for minimal token usage.
        
        Success response includes:
        - Tree-formatted string showing directory structure
        - File counts shown inline: "dirname/ (X files, Y dirs)"
        - Files are shown when depth allows
        - Summary with total counts
        
        Error response includes:
        - Explanation of why listing failed
        - Suggestions for alternative directories or approaches
        
        Examples:
        - list_directory(".") → List current directory
        - list_directory("src", max_depth=3) → List src with 3 levels deep
        - list_directory(".", include_hidden=True) → Include hidden files"""
    )
    async def list_directory(
        self,
        path: Annotated[str, "Directory path to list"] = ".",
        max_depth: Annotated[int, "Maximum depth to traverse (default: 2)"] = 2,
        include_hidden: Annotated[bool, "Include hidden files/dirs (default: False)"] = False,
        max_entries: Annotated[int, "Maximum entries to return (default: 200, max: 1000)"] = 200
    ) -> Dict[str, Any]:
        """List directory with enhanced structure and metadata."""
        try:
            # Validate and cap max_entries
            max_entries = min(max_entries, 1000)
            
            dir_path = self._resolve_path(path)
            
            # Validate directory
            if not dir_path.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Path '{path}' does not exist",
                    suggestions=[
                        "Use list_directory('.') to see current directory",
                        "Use find_files('**/*', max_results=20) to see available files",
                        f"Current working directory: {self._base_path}"
                    ]
                ).model_dump()
            
            if not dir_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{path}' is a file, not a directory",
                    suggestions=[
                        f"Use read_file('{path}') to read this file",
                        f"Use get_file_info('{path}') for file metadata",
                        f"Use list_directory('{str(dir_path.parent.relative_to(self._base_path))}') for parent directory"
                    ]
                ).model_dump()
            
            # Common directories to exclude
            exclude_patterns = {
                '.git', '.vscode', '.idea', '__pycache__', 'node_modules',
                '.pytest_cache', '.mypy_cache', 'dist', 'build', '.next',
                'target', 'bin', 'obj', '.terraform', '.venv', 'venv',
                '.DS_Store', 'thumbs.db'
            } if not include_hidden else set()
            
            # Build directory tree as string
            tree_str, stats = self._build_tree_string(
                dir_path, max_depth, max_entries, 
                exclude_patterns, include_hidden
            )
            
            # Generate insights and suggestions
            suggestions = self._generate_directory_insights(stats, None)
            
            # Deduplicate suggestions
            suggestions = self._deduplicate_suggestions(suggestions)
            
            return PluginResponse(
                success=True,
                data={
                    "tree": tree_str,
                    "summary": {
                        "total_files": stats.get('total_files', 0),
                        "total_directories": stats.get('total_dirs', 0)
                    }
                },
                error=None,
                suggestions=suggestions,
                metadata={
                    "max_depth_reached": stats.get('max_depth_reached', 0),
                    "truncated": stats.get('truncated', False)
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Failed to list directory: {str(e)}",
                suggestions=[
                    "Check if you have read permissions",
                    "Try listing parent directory first",
                    "Use find_files() to search for specific files instead"
                ]
            ).model_dump()
    
    @kernel_function(
        name="read_file",
        description="""Reads file content with optimized response format.
        Returns either full content OR specific lines, with line range information.
        
        Success response includes:
        - For full reads: content string with line_range [1, 100] by default
        - For line reads: array of lines with exact line_range
        - Total lines count and encoding information
        - Truncation status when applicable
        
        Error response includes:
        - Specific reason for failure (not found, too large, binary, etc.)
        - Alternative approaches or related files
        
        Examples:
        - read_file("config.json") → Read first 100 lines as content
        - read_file("main.py", start_line=1, num_lines=50) → Read lines 1-50
        - read_file("logs/app.log", start_line=100, num_lines=20) → Read lines 100-119"""
    )
    async def read_file(
        self,
        file_path: Annotated[str, "Path to the file to read"],
        start_line: Annotated[Optional[int], "Starting line number (1-indexed)"] = None,
        num_lines: Annotated[Optional[int], "Number of lines to read"] = None,
        encoding: Annotated[str, "File encoding (default: 'utf-8')"] = "utf-8"
    ) -> Dict[str, Any]:
        """Read file with enhanced error handling and metadata."""
        try:
            full_path = self._resolve_path(file_path)
            
            # Validate file
            if not full_path.exists():
                similar_files = self._find_similar_files(full_path)
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File '{file_path}' not found",
                    suggestions=[
                        f"Did you mean: {similar}" for similar in similar_files[:3]
                    ] + [
                        "Use find_files() to search for files",
                        "Use list_directory() to explore the directory structure"
                    ]
                ).model_dump()
            
            if full_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{file_path}' is a directory, not a file",
                    suggestions=[
                        f"Use list_directory('{file_path}') to see directory contents",
                        f"Use find_files('*', '{file_path}') to list files in this directory",
                        "Specify a file path, not a directory path"
                    ]
                ).model_dump()
            
            # Check file size
            file_size = full_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File too large ({file_size:,} bytes)",
                    suggestions=[
                        f"Use read_file('{file_path}', start_line=1, num_lines=100) to read portions",
                        f"Use search_in_files() to find specific content",
                        f"Large files should be read in chunks"
                    ]
                ).model_dump()
            
            # Detect file type
            file_info = self._create_file_info(full_path)
            
            # Read file
            try:
                total_lines = self._count_file_lines(full_path)
                
                if start_line is not None or num_lines is not None:
                    # Line-based reading
                    lines = self._read_file_lines(full_path, start_line or 1, num_lines or 100, encoding)
                    
                    content_data = {
                        "lines": lines,
                        "line_range": [start_line or 1, (start_line or 1) + len(lines) - 1],
                        "total_lines": total_lines
                    }
                    
                    suggestions = []
                    if len(lines) < (num_lines or 100):
                        suggestions.append(f"Reached end of file at line {(start_line or 1) + len(lines) - 1}")
                    else:
                        next_start = (start_line or 1) + len(lines)
                        suggestions.append(f"Continue from line {next_start}")
                    
                else:
                    # Read entire file or first 100 lines
                    with open(full_path, 'r', encoding=encoding) as f:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= 100:
                                break
                            lines.append(line.rstrip('\n'))
                        
                        # Join lines back into content
                        content = '\n'.join(lines)
                    
                    content_data = {
                        "content": content,
                        "line_range": [1, len(lines)],
                        "total_lines": total_lines
                    }
                    
                    suggestions = []
                    if total_lines > 100:
                        suggestions.append(f"File has {total_lines} lines, showing first 100. Continue from line 101")
                    
                    # Add content-based suggestions
                    suggestions.extend(self._generate_content_suggestions(content, file_info))
                
                # Deduplicate suggestions
                suggestions = self._deduplicate_suggestions(suggestions)
                
                return PluginResponse(
                    success=True,
                    data=content_data,
                    error=None,
                    suggestions=suggestions,
                    metadata={
                        "encoding": encoding,
                        "truncated": total_lines > len(lines) if 'lines' in content_data else total_lines > 100
                    }
                ).model_dump()
                
            except UnicodeDecodeError:
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Cannot decode file with {encoding} encoding",
                    suggestions=[
                        "Try reading with encoding='latin-1' for legacy files",
                        "Try encoding='utf-16' for some Windows files",
                        "This might be a binary file - check the extension",
                        f"Use get_file_info('{file_path}') to check file type"
                    ]
                ).model_dump()
                
        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Error reading file: {str(e)}",
                suggestions=[
                    "Check file permissions",
                    "Verify the file is not locked by another process",
                    "Try reading a smaller portion of the file"
                ]
            ).model_dump()
    
    @kernel_function(
        name="search_in_files",
        description="""Searches for patterns in files and returns matches grouped by file.
        Optimized response format with minimal redundancy.
        
        Success response includes:
        - Matches grouped by file path
        - Each match contains: line number, content, and context
        - Context object has "before" (line above) and "after" (line below)
        - Summary with total matches and files matched
        
        Error response includes:
        - Clear explanation of search failures
        - Suggestions for improving search patterns
        
        Examples:
        - search_in_files("TODO", ["*.py"]) → Find TODO comments in Python files
        - search_in_files("class.*Controller", ["**/*.java"]) → Find controller classes
        - search_in_files("import.*boto3", ["**/*.py"]) → Find AWS SDK imports
        - search_in_files("password|secret|key", ["**/*.env", "**/*.config"]) → Security scan"""
    )
    async def search_in_files(
        self,
        pattern: Annotated[str, "Regex pattern to search for"],
        file_patterns: Annotated[List[str], "List of glob patterns for files to search"],
        search_path: Annotated[str, "Directory to search in"] = ".",
        case_sensitive: Annotated[bool, "Case sensitive search (default: True)"] = True,
        max_results: Annotated[int, "Maximum results to return (default: 50, max: 1000)"] = 50,
        include_context: Annotated[bool, "Include surrounding lines (default: True)"] = True
    ) -> Dict[str, Any]:
        """Search files with enhanced context and metadata."""
        try:
            # Validate and cap max_results
            max_results = min(max_results, 1000)
            
            search_dir = self._resolve_path(search_path)
            
            # Validate search directory
            if not search_dir.exists() or not search_dir.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Search directory '{search_path}' not found or not a directory",
                    suggestions=[
                        "Use list_directory() to find valid directories",
                        "Check if the path is relative to the base directory",
                        "Use '.' to search in current directory"
                    ]
                ).model_dump()
            
            # Compile regex pattern
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
            except re.error as e:
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Invalid regex pattern: {str(e)}",
                    suggestions=[
                        "Escape special characters: . * + ? [ ] { } ( ) | \\ ^ $",
                        f"For literal search, use: {re.escape(pattern)}",
                        "Common patterns: '^import' (line start), 'word\\b' (word boundary)",
                        "Use simpler patterns or literal strings for basic searches"
                    ]
                ).model_dump()
            
            # Search files
            matches_by_file = {}
            files_searched = 0
            total_matches = 0
            
            for file_pattern in file_patterns:
                for file_path in self._find_files(search_dir, file_pattern):
                    if total_matches >= max_results:
                        break
                    
                    files_searched += 1
                    file_matches = self._search_in_file(
                        file_path, regex, max_results - total_matches, include_context
                    )
                    
                    if file_matches:
                        rel_path = str(file_path.relative_to(self._base_path))
                        matches_by_file[rel_path] = file_matches
                        total_matches += len(file_matches)
            
            # Generate suggestions based on results
            suggestions = self._generate_search_suggestions(
                pattern, matches_by_file, files_searched, total_matches, max_results
            )
            
            # Deduplicate suggestions
            suggestions = self._deduplicate_suggestions(suggestions)
            
            return PluginResponse(
                success=True,
                data={
                    "matches_by_file": matches_by_file,
                    "summary": {
                        "total_matches": total_matches,
                        "files_matched": len(matches_by_file),
                        "files_searched": files_searched
                    }
                },
                error=None,
                suggestions=suggestions,
                metadata={
                    "truncated": total_matches > max_results
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Search error: {str(e)}",
                suggestions=[
                    "Try a simpler search pattern",
                    "Verify file patterns are valid globs",
                    "Check if you have read permissions"
                ]
            ).model_dump()
    
    @kernel_function(
        name="get_file_info",
        description="""Gets file information with optimized response.
        Returns essential file details with minimal redundancy.
        
        Success response includes:
        - File path and semantic type
        - Human-readable size
        - Content preview (if text file and requested)
        - Encoding information for text files
        
        Error response includes:
        - Reason why file info couldn't be retrieved
        - Suggestions for alternatives
        
        Examples:
        - get_file_info("package.json") → Get Node.js package details
        - get_file_info("src/main.py") → Get Python file information
        - get_file_info("data.csv") → Get CSV file stats"""
    )
    async def get_file_info(
        self,
        file_path: Annotated[str, "Path to the file"],
        include_preview: Annotated[bool, "Include content preview (default: True)"] = True,
        preview_lines: Annotated[int, "Number of preview lines (default: 10)"] = 10
    ) -> Dict[str, Any]:
        """Get comprehensive file information."""
        try:
            full_path = self._resolve_path(file_path)
            
            # Validate file
            if not full_path.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File '{file_path}' not found",
                    suggestions=[
                        "Use find_files() to search for the file",
                        "Check if the path is correct",
                        "Use list_directory() to explore available files"
                    ]
                ).model_dump()
            
            if full_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{file_path}' is a directory",
                    suggestions=[
                        f"Use list_directory('{file_path}') for directory information",
                        "This function is for files only"
                    ]
                ).model_dump()
            
            # Get file stats
            stat = full_path.stat()
            file_info = self._create_file_info(full_path)
            is_text = self._is_text_file(full_path)
            
            # Prepare simplified file data
            file_data = {
                "path": str(full_path.relative_to(self._base_path)),
                "type": file_info.type,  # Keep semantic type as it adds value
                "size": self._format_size(stat.st_size)
            }
            
            # Add content preview if requested
            if include_preview and is_text and stat.st_size < 1024 * 1024:  # 1MB limit
                preview_data = self._get_file_preview(full_path, preview_lines)
                file_data["preview"] = preview_data
            
            # Generate type-specific suggestions
            suggestions = self._generate_file_type_suggestions(file_info, stat.st_size)
            
            # Deduplicate suggestions
            suggestions = self._deduplicate_suggestions(suggestions)
            
            return PluginResponse(
                success=True,
                data=file_data,
                error=None,
                suggestions=suggestions,
                metadata={
                    "is_text_file": is_text,
                    "encoding": self._guess_encoding(full_path) if is_text else None
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Error getting file info: {str(e)}",
                suggestions=[
                    "Check if the file is accessible",
                    "Verify file permissions",
                    "Try using list_directory() on parent directory"
                ]
            ).model_dump()
    
    # Helper methods
    def _deduplicate_suggestions(self, suggestions: List[str]) -> List[str]:
        """Remove duplicate suggestions while preserving order."""
        seen = set()
        deduplicated = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                deduplicated.append(suggestion)
        return deduplicated
    
    def _should_suggest_increase_results(self, found: int, returned: int) -> bool:
        """Determine if suggesting to increase max_results is helpful."""
        if found <= returned:
            return False
        
        # Only suggest if the gap is reasonable (< 200% of current results)
        gap_ratio = found / returned
        return gap_ratio <= 3.0  # Don't suggest if found is > 3x returned
    
    def _should_exclude_file(self, rel_path: str, exclude_patterns: set) -> bool:
        """Check if a file should be excluded based on patterns."""
        if not exclude_patterns:
            return False
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # Also check if any parent directory matches
            parts = rel_path.split('/')
            for i in range(len(parts)):
                partial_path = '/'.join(parts[:i+1])
                if fnmatch.fnmatch(partial_path + '/*', pattern):
                    return True
        return False
    
    def _get_smart_find_suggestions(self, total_found: int, returned: int, 
                                   max_results: int, pattern: str, search_path: str) -> List[str]:
        """Generate smart suggestions for find_files based on results."""
        suggestions = []
        
        if total_found > returned:
            if self._should_suggest_increase_results(total_found, returned):
                suggestions.append(f"Found {total_found} files but returned only {returned}. Increase max_results to see more.")
            else:
                # For large gaps, focus on refinement instead
                suggestions.append(f"Found {total_found} files (showing first {returned}). Use more specific patterns to narrow results.")
            
            suggestions.append("Consider using more specific patterns to narrow results")
        
        if not returned:  # No files found
            suggestions.extend([
                f"No files found matching '{pattern}' in '{search_path}'",
                "Try a broader pattern like '**/*' to see all files",
                "Use list_directory() to explore the directory structure",
                "Check if files have different extensions than expected"
            ])
        else:
            # Add helpful next steps based on pattern
            if pattern.endswith('.py'):
                suggestions.append("Use search_in_files() to find specific code patterns or read_file() to examine specific files")
            elif pattern.endswith(('.json', '.yaml', '.yml', '.toml')):
                suggestions.append("Use read_file() to examine configuration files")
            
            if total_found > 20:
                suggestions.append("Consider using more specific patterns to narrow results")
        
        # Cap reached warning
        if max_results >= 1000:
            suggestions.append("Results capped at maximum limit of 1000 files")
        
        return suggestions
    
    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path relative to the base path."""
        path = Path(path_str)
        if path.is_absolute():
            return path
        return (self._base_path / path).resolve()
    
    def _find_files(self, directory: Path, pattern: str) -> List[Path]:
        """Find files matching a pattern in a directory."""
        if '**' in pattern:
            return list(directory.glob(pattern))
        else:
            matches = []
            try:
                for item in directory.iterdir():
                    if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                        matches.append(item)
            except PermissionError:
                pass
            return matches
    
    def _create_file_info(self, file_path: Path) -> FileInfo:
        """Create FileInfo object from path."""
        extension = file_path.suffix.lower()
        file_type = self.FILE_TYPE_MAPPINGS.get(extension, 'other')
        
        # Special case for files without extensions
        if not extension and file_path.name.lower() in ['dockerfile', 'makefile', 'jenkinsfile']:
            file_type = 'config'
        
        return FileInfo(
            path=str(file_path.relative_to(self._base_path)),
            name=file_path.name,
            extension=extension,
            type=file_type
        )
    
    def _build_tree_structure(self, path: Path, max_depth: int, max_entries: int, 
                            entry_count: int, exclude_patterns: set, include_hidden: bool) -> tuple:
        """Build directory tree structure with statistics."""
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'file_types': {},
            'max_depth_reached': 0,
            'truncated': False
        }
        
        def build_node(current_path: Path, current_depth: int) -> Optional[Dict[str, Any]]:
            nonlocal entry_count
            
            if entry_count >= max_entries:
                stats['truncated'] = True
                return None
            
            if current_depth > max_depth:
                return None
            
            stats['max_depth_reached'] = max(stats['max_depth_reached'], current_depth)
            entry_count += 1
            
            name = current_path.name
            if name in exclude_patterns:
                return None
            
            if not include_hidden and name.startswith('.'):
                return None
            
            if current_path.is_file():
                stats['total_files'] += 1
                file_info = self._create_file_info(current_path)
                stats['file_types'][file_info.type] = stats['file_types'].get(file_info.type, 0) + 1
                
                return {
                    "name": name,
                    "type": "file",
                    "path": str(current_path.relative_to(self._base_path)),
                    "extension": file_info.extension,
                    "file_type": file_info.type
                }
            else:
                stats['total_dirs'] += 1
                children = []
                
                try:
                    entries = sorted(current_path.iterdir(), 
                                   key=lambda x: (not x.is_dir(), x.name.lower()))
                    
                    for child_path in entries:
                        if entry_count >= max_entries:
                            break
                        
                        child_node = build_node(child_path, current_depth + 1)
                        if child_node:
                            children.append(child_node)
                except PermissionError:
                    pass
                
                dir_info = DirectoryInfo(
                    path=str(current_path.relative_to(self._base_path)),
                    name=name,
                    file_count=sum(1 for c in children if c['type'] == 'file'),
                    dir_count=sum(1 for c in children if c['type'] == 'directory'),
                    total_size=None  # Could be calculated if needed
                )
                
                return {
                    "name": name,
                    "type": "directory",
                    "path": dir_info.path,
                    "children": children,
                    "summary": {
                        "files": dir_info.file_count,
                        "directories": dir_info.dir_count
                    }
                }
        
        structure = build_node(path, 0)
        return structure, stats
    
    def _generate_directory_insights(self, stats: Dict[str, Any], structure: Optional[Dict[str, Any]]) -> List[str]:
        """Generate insights and suggestions based on directory analysis."""
        suggestions = []
        
        # Analyze project type based on file types
        file_types = stats.get('file_types', {})
        
        if file_types.get('python', 0) > 5:
            suggestions.append("Python project detected. Use search_in_files() to find imports and classes.")
        
        if file_types.get('javascript', 0) > 0 or file_types.get('typescript', 0) > 0:
            suggestions.append("JavaScript/TypeScript project. Check package.json for dependencies.")
        
        if file_types.get('infrastructure', 0) > 0:
            suggestions.append("Infrastructure as Code detected. Examine .tf files for cloud resources.")
        
        if file_types.get('config', 0) > 3:
            suggestions.append("Multiple config files found. Review for environment settings.")
        
        # Check for common project patterns (only if we have structure data)
        if structure and 'children' in structure:
            child_names = [c['name'] for c in structure['children'] if c['type'] == 'directory']
            
            if 'src' in child_names or 'lib' in child_names:
                suggestions.append("Standard source layout detected. Focus analysis on src/ or lib/ directories.")
            
            if 'test' in child_names or 'tests' in child_names:
                suggestions.append("Test directory found. Analyze test coverage and patterns.")
            
            if 'docs' in child_names or 'documentation' in child_names:
                suggestions.append("Documentation directory found. Check for API docs or guides.")
        
        if stats.get('truncated'):
            suggestions.append(f"Results truncated. Use more specific paths or increase max_entries.")
        
        return suggestions
    
    def _read_file_lines(self, file_path: Path, start_line: int, num_lines: int, encoding: str) -> List[str]:
        """Read specific lines from a file."""
        lines = []
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            # Skip to start line
            for _ in range(start_line - 1):
                if not f.readline():
                    return []
            
            # Read requested lines
            for _ in range(num_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip('\n'))
        
        return lines
    
    def _count_file_lines(self, file_path: Path) -> int:
        """Count total lines in a file."""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    
    def _search_in_file(self, file_path: Path, regex: re.Pattern, 
                       max_matches: int, include_context: bool) -> List[Dict[str, Any]]:
        """Search for pattern in a single file."""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                if len(matches) >= max_matches:
                    break
                
                match = regex.search(line)
                if match:
                    match_data = {
                        "line": i + 1,
                        "content": line.rstrip('\n')
                    }
                    
                    if include_context:
                        context = {}
                        if i > 0:
                            context["before"] = lines[i-1].rstrip('\n')
                        else:
                            context["before"] = ""
                        
                        if i < len(lines) - 1:
                            context["after"] = lines[i+1].rstrip('\n')
                        else:
                            context["after"] = ""
                        
                        match_data["context"] = context
                    
                    matches.append(match_data)
        
        except Exception:
            # Skip files that can't be read
            pass
        
        return matches
    
    def _generate_search_suggestions(self, pattern: str, matches_by_file: Dict[str, List], 
                                   files_searched: int, total_matches: int, max_results: int) -> List[str]:
        """Generate suggestions based on search results."""
        suggestions = []
        
        # Check if we actually have matches
        files_with_matches = len(matches_by_file) if matches_by_file else 0
        
        if not matches_by_file or total_matches == 0:
            suggestions.extend([
                f"No matches found for '{pattern}'",
                "Try a broader pattern or check the file patterns",
                "Use case_sensitive=False for case-insensitive search",
                "Verify files exist with find_files() first"
            ])
        else:
            if total_matches > max_results:
                suggestions.append(f"Found {total_matches} matches but showing only {max_results}. Increase max_results or refine pattern.")
            
            # Analyze match distribution
            if files_with_matches == 1:
                suggestions.append("All matches in single file. Consider searching more broadly.")
            elif files_with_matches > 10:
                suggestions.append("Matches spread across many files. Consider more specific patterns.")
            
            # Pattern-specific suggestions
            if 'TODO' in pattern.upper() or 'FIXME' in pattern.upper():
                suggestions.append("Found development markers. Review for pending tasks.")
            elif 'import' in pattern.lower():
                suggestions.append("Analyzing imports. Use results to understand dependencies.")
            elif any(word in pattern.lower() for word in ['class', 'function', 'def']):
                suggestions.append("Found code definitions. Map out architecture from results.")
        
        suggestions.append(f"Searched {files_searched} files in total")
        
        return suggestions
    
    def _find_similar_files(self, target_path: Path) -> List[str]:
        """Find files with similar names."""
        similar = []
        parent = target_path.parent
        target_name = target_path.name.lower()
        
        if parent.exists():
            for file in parent.iterdir():
                if file.is_file():
                    similarity = self._calculate_similarity(target_name, file.name.lower())
                    if similarity > 0.6:
                        similar.append(str(file.relative_to(self._base_path)))
        
        return sorted(similar)[:5]
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (simple approach)."""
        if s1 == s2:
            return 1.0
        
        # Simple character overlap ratio
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _generate_content_suggestions(self, content: str, file_info: FileInfo) -> List[str]:
        """Generate suggestions based on file content."""
        suggestions = []
        
        # Language-specific suggestions
        if file_info.type == 'python':
            if 'import boto3' in content or 'from boto3' in content:
                suggestions.append("AWS SDK detected. Search for specific AWS service usage.")
            if 'import flask' in content or 'from flask' in content:
                suggestions.append("Flask web framework detected. Look for route definitions.")
            if 'import django' in content or 'from django' in content:
                suggestions.append("Django framework detected. Check for models and views.")
        
        elif file_info.type == 'javascript' or file_info.type == 'typescript':
            if 'require(' in content or 'import ' in content:
                suggestions.append("Module imports found. Analyze dependencies.")
            if 'express' in content:
                suggestions.append("Express.js detected. Search for route handlers.")
            if 'react' in content.lower():
                suggestions.append("React framework detected. Look for components.")
        
        elif file_info.type == 'config':
            if file_info.name == 'package.json':
                suggestions.append("Node.js project file. Check dependencies and scripts sections.")
            elif file_info.name == 'requirements.txt':
                suggestions.append("Python dependencies file. Analyze required packages.")
            elif file_info.extension in ['.yaml', '.yml']:
                suggestions.append("YAML config file. May contain deployment or CI/CD settings.")
        
        elif file_info.type == 'infrastructure':
            suggestions.append("Infrastructure as Code file. Analyze cloud resources defined.")
            if 'aws_' in content:
                suggestions.append("AWS resources detected. Map to target cloud equivalents.")
            if 'azurerm_' in content:
                suggestions.append("Azure resources detected. Check for migration compatibility.")
        
        return suggestions
    
    def _generate_file_type_suggestions(self, file_info: FileInfo, size: int) -> List[str]:
        """Generate suggestions based on file type."""
        suggestions = []
        
        if file_info.type == 'python':
            suggestions.extend([
                "Use search_in_files() to find specific functions or classes",
                "Look for import statements to understand dependencies"
            ])
        elif file_info.type in ['javascript', 'typescript']:
            suggestions.extend([
                "Check for framework usage (React, Vue, Angular)",
                "Analyze import/require statements for dependencies"
            ])
        elif file_info.type == 'config':
            suggestions.extend([
                "Parse configuration for environment-specific settings",
                "Look for API keys, endpoints, or service configurations"
            ])
        elif file_info.type == 'infrastructure':
            suggestions.extend([
                "Analyze cloud resources and their configurations",
                "Map infrastructure to target cloud provider"
            ])
        
        if size > 1024 * 1024:  # 1MB
            suggestions.append("Large file. Consider reading in chunks using line ranges.")
        
        return suggestions
    
    def _get_file_preview(self, file_path: Path, preview_lines: int) -> Dict[str, Any]:
        """Get file content preview."""
        try:
            lines = self._read_file_lines(file_path, 1, preview_lines, 'utf-8')
            
            # Try to detect file structure
            content_type = "text"
            if file_path.suffix == '.json':
                try:
                    full_content = file_path.read_text()
                    json_data = json.loads(full_content)
                    content_type = "json"
                    lines = json.dumps(json_data, indent=2).splitlines()[:preview_lines]
                except:
                    pass
            
            return {
                "lines": lines,
                "content_type": content_type,
                "truncated": len(lines) == preview_lines
            }
        except:
            return {
                "lines": [],
                "content_type": "binary",
                "truncated": False,
                "error": "Cannot preview binary file"
            }
    
    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely text based."""
        text_extensions = {
            '.txt', '.md', '.rst', '.log', '.csv', '.json', '.xml', '.yaml', '.yml',
            '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.cs',
            '.rb', '.php', '.swift', '.kt', '.sh', '.bat', '.ps1', '.sql', '.html',
            '.css', '.scss', '.less', '.jsx', '.tsx', '.vue', '.tf', '.tfvars'
        }
        return file_path.suffix.lower() in text_extensions
    
    def _guess_encoding(self, file_path: Path) -> str:
        """Guess file encoding."""
        # Simple approach - could be enhanced with chardet
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
            
            # Try UTF-8 first
            try:
                sample.decode('utf-8')
                return 'utf-8'
            except:
                pass
            
            # Try other common encodings
            for encoding in ['latin-1', 'utf-16', 'cp1252']:
                try:
                    sample.decode(encoding)
                    return encoding
                except:
                    pass
            
            return 'unknown'
        except:
            return 'unknown'
    
    def _build_tree_string(self, path: Path, max_depth: int, max_entries: int, 
                          exclude_patterns: set, include_hidden: bool) -> tuple:
        """Build a tree-formatted string representation of directory structure."""
        tree_lines = []
        entry_count = 0
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'file_types': {},
            'max_depth_reached': 0,
            'truncated': False
        }
        
        def add_node(current_path: Path, prefix: str, is_last: bool, depth: int):
            nonlocal entry_count
            
            if entry_count >= max_entries:
                stats['truncated'] = True
                return
            
            if depth > max_depth:
                return
            
            stats['max_depth_reached'] = max(stats['max_depth_reached'], depth)
            
            name = current_path.name
            if name in exclude_patterns and not include_hidden:
                return
            
            if not include_hidden and name.startswith('.'):
                return
            
            # Prepare the tree branch characters
            if depth > 0:
                connector = "└── " if is_last else "├── "
                line_prefix = prefix + connector
            else:
                line_prefix = ""
            
            if current_path.is_file():
                stats['total_files'] += 1
                file_info = self._create_file_info(current_path)
                stats['file_types'][file_info.type] = stats['file_types'].get(file_info.type, 0) + 1
                
                # Show files only if we're not at max depth
                if depth < max_depth:
                    tree_lines.append(f"{line_prefix}{name}")
                    entry_count += 1
            
            elif current_path.is_dir():
                stats['total_dirs'] += 1
                
                # Count children for the directory annotation
                try:
                    children = list(current_path.iterdir())
                    # Filter based on hidden/exclude rules
                    if not include_hidden:
                        children = [c for c in children if not c.name.startswith('.') and c.name not in exclude_patterns]
                    
                    file_count = sum(1 for c in children if c.is_file())
                    dir_count = sum(1 for c in children if c.is_dir())
                    
                    # Add directory with counts
                    if file_count > 0 or dir_count > 0:
                        dir_line = f"{line_prefix}{name}/ ({file_count} files"
                        if dir_count > 0:
                            dir_line += f", {dir_count} dirs"
                        dir_line += ")"
                    else:
                        dir_line = f"{line_prefix}{name}/"
                    
                    tree_lines.append(dir_line)
                    entry_count += 1
                    
                    # Process children if not at max depth
                    if depth < max_depth:
                        # Sort: directories first, then files
                        children.sort(key=lambda x: (x.is_file(), x.name.lower()))
                        
                        for i, child in enumerate(children):
                            if entry_count >= max_entries:
                                break
                            
                            # Update prefix for children
                            if depth > 0:
                                child_prefix = prefix + ("    " if is_last else "│   ")
                            else:
                                child_prefix = ""
                            
                            is_last_child = (i == len(children) - 1)
                            add_node(child, child_prefix, is_last_child, depth + 1)
                
                except PermissionError:
                    pass
        
        # Start building from the root
        add_node(path, "", True, 0)
        
        tree_str = "\n".join(tree_lines)
        return tree_str, stats


# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_plugin_v2():
        plugin = FileSystemPlugin()
        
        print("Testing FileSystemPlugin v2 with LLM-optimized responses\n")
        
        # Test finding files
        print("1. Testing find_files:")
        result = await plugin.find_files("*.py", ".", max_results=5)
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Found {result['metadata']['total_found']} files, returned {result['metadata']['returned']}")
            print(f"File types: {result['metadata']['file_types']}")
        print(f"Suggestions: {result['suggestions'][:2]}")
        
        print("\n2. Testing error handling:")
        result = await plugin.read_file("nonexistent/directory/")
        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")
        print(f"Suggestions: {result['suggestions']}")
        
        print("\n3. Testing list_directory:")
        result = await plugin.list_directory(".", max_depth=1)
        if result['success']:
            summary = result['data']['summary']
            print(f"Files: {summary['total_files']}, Directories: {summary['total_directories']}")
            print(f"Suggestions: {result['suggestions'][:2]}")
    
    # Run test
    asyncio.run(test_plugin_v2())