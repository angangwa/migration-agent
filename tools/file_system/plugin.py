"""
FileSystemPlugin

A comprehensive file system interface that provides clean, token-efficient
responses optimized for AI agents. This is the main plugin class that
orchestrates all file system operations.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Annotated

from semantic_kernel.functions import kernel_function

from .models import PluginResponse
from .helpers import FileSystemHelpers, TreeBuilder
from .suggestions import SuggestionGenerator


class FileSystemPlugin:
    """
    FileSystemPlugin

    All functions return standardized PluginResponse with success status,
    data, errors, and contextual suggestions.
    """

    def __init__(self, base_path: Optional[str] = None, **kwargs):
        """Initialize the plugin with a base path."""
        super().__init__(**kwargs)
        self._base_path = Path(base_path).resolve() if base_path else Path.cwd()
        self.helpers = FileSystemHelpers(self._base_path)
        self.tree_builder = TreeBuilder(self.helpers)
        self.suggestions = SuggestionGenerator()

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
        - find_files("src/**/*.{js,ts}") → Find JS/TS files in src (use multiple calls)""",
    )
    async def find_files(
        self,
        pattern: Annotated[
            str, "Glob pattern to match files (e.g., '*.py', '**/*.js')"
        ],
        search_path: Annotated[str, "Directory to search in (default: '.')"] = ".",
        max_results: Annotated[
            int, "Maximum files to return (default: 100, max: 1000)"
        ] = 100,
        exclude_patterns: Annotated[
            List[str],
            "Patterns to exclude (e.g., ['.venv/*', 'node_modules/*'])",
        ] = [],
    ) -> Dict[str, Any]:
        """Find files with enhanced metadata and error handling."""
        try:
            # Validate and cap max_results
            max_results = min(max_results, 1000)

            search_dir = self.helpers.resolve_path(search_path)

            # Validate search directory
            if not search_dir.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Directory '{search_path}' does not exist",
                    suggestions=[
                        "Use list_directory() to see available directories",
                        "Check if the path is relative to the base directory",
                        f"Current base directory: {self._base_path}",
                    ],
                ).model_dump()

            if not search_dir.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{search_path}' is not a directory, it's a file",
                    suggestions=[
                        f"Use read_file('{search_path}') to read this file",
                        f"Use get_file_info('{search_path}') to get file metadata",
                        "Use list_directory() on the parent directory",
                    ],
                ).model_dump()

            # Find matching files
            files = []
            total_found = 0
            exclude_set = set(exclude_patterns)

            for file_path in self.helpers.find_files(search_dir, pattern):
                # Check if file should be excluded
                rel_path = str(file_path.relative_to(self._base_path))
                if self.helpers.should_exclude_file(rel_path, exclude_set):
                    continue

                total_found += 1
                if len(files) < max_results:
                    # Just append the relative path as a string
                    files.append(rel_path)

            # Prepare response with smart suggestions
            suggestions = self.suggestions.get_smart_find_suggestions(
                total_found, len(files), max_results, pattern, search_path
            )

            # Detect common excluded directories and suggest exclusion
            if len(exclude_patterns) == 0:
                venv_found = any(".venv" in f for f in files[:10])
                node_modules_found = any("node_modules" in f for f in files[:10])
                if venv_found or node_modules_found:
                    exclude_suggestion = (
                        "Consider using exclude_patterns=['.venv/*', 'node_modules/*'] "
                        "to filter out dependency directories"
                    )
                    suggestions.append(exclude_suggestion)

            # Deduplicate suggestions
            suggestions = self.suggestions.deduplicate_suggestions(suggestions)

            return PluginResponse(
                success=True,
                data={"files": files, "count": len(files)},
                error=None,
                suggestions=suggestions,
                metadata={
                    "total_found": total_found,
                    "truncated": total_found > max_results,
                },
            ).model_dump()

        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)}",
                suggestions=[
                    "Check if the pattern is valid glob syntax",
                    "Verify you have read permissions for the directory",
                    "Try a simpler pattern first",
                ],
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
        - list_directory(".", include_hidden=True) → Include hidden files""",
    )
    async def list_directory(
        self,
        path: Annotated[str, "Directory path to list"] = ".",
        max_depth: Annotated[str, "Maximum depth to traverse (default: 2)"] = "2",
        include_hidden: Annotated[
            bool, "Include hidden files/dirs (default: False)"
        ] = False,
        max_entries: Annotated[
            str, "Maximum entries to return (default: 200, max: 1000)"
        ] = "200",
    ) -> Dict[str, Any]:
        """List directory with enhanced structure and metadata."""
        try:
            # Convert string parameters to integers
            try:
                max_depth_int = int(max_depth)
            except (ValueError, TypeError):
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Invalid max_depth value: '{max_depth}'. Must be a number.",
                    suggestions=["Provide max_depth as a number, e.g., '1', '2', '3'"]
                ).model_dump()
            
            try:
                max_entries_int = int(max_entries)
            except (ValueError, TypeError):
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Invalid max_entries value: '{max_entries}'. Must be a number.",
                    suggestions=["Provide max_entries as a number, e.g., '100', '200', '500'"]
                ).model_dump()
            
            # Validate and cap max_entries
            max_entries_int = min(max_entries_int, 1000)

            dir_path = self.helpers.resolve_path(path)

            # Validate directory
            if not dir_path.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Path '{path}' does not exist",
                    suggestions=[
                        "Use list_directory('.') to see current directory",
                        "Use find_files('**/*', max_results=20) to see available files",
                        f"Current working directory: {self._base_path}",
                    ],
                ).model_dump()

            if not dir_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{path}' is a file, not a directory",
                    suggestions=[
                        f"Use read_file('{path}') to read this file",
                        f"Use get_file_info('{path}') for file metadata",
                        (
                            "Use list_directory('"
                            f"{str(dir_path.parent.relative_to(self._base_path))}')"
                            " for parent directory"
                        ),
                    ],
                ).model_dump()

            # Common directories to exclude
            exclude_patterns = (
                {
                    ".git",
                    ".vscode",
                    ".idea",
                    "__pycache__",
                    "node_modules",
                    ".pytest_cache",
                    ".mypy_cache",
                    "dist",
                    "build",
                    ".next",
                    "target",
                    "bin",
                    "obj",
                    ".terraform",
                    ".venv",
                    "venv",
                    ".DS_Store",
                    "thumbs.db",
                }
                if not include_hidden
                else set()
            )

            # Build directory tree as string
            tree_str, stats = self.tree_builder.build_tree_string(
                dir_path, max_depth_int, max_entries_int, exclude_patterns, include_hidden
            )

            # Generate insights and suggestions
            suggestions = self.suggestions.generate_directory_insights(stats, None)

            # Deduplicate suggestions
            suggestions = self.suggestions.deduplicate_suggestions(suggestions)

            return PluginResponse(
                success=True,
                data={
                    "tree": tree_str,
                    "summary": {
                        "total_files": stats.get("total_files", 0),
                        "total_directories": stats.get("total_dirs", 0),
                    },
                },
                error=None,
                suggestions=suggestions,
                metadata={
                    "max_depth_reached": stats.get("max_depth_reached", 0),
                    "truncated": stats.get("truncated", False),
                },
            ).model_dump()

        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Failed to list directory: {str(e)}",
                suggestions=[
                    "Check if you have read permissions",
                    "Try listing parent directory first",
                    "Use find_files() to search for specific files instead",
                ],
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
        - read_file("logs/app.log", start_line=100, num_lines=20) → Read lines 100-119""",
    )
    async def read_file(
        self,
        file_path: Annotated[str, "Path to the file to read"],
        start_line: Annotated[int, "Starting line number (1-indexed, 0 means read from beginning)"] = 0,
        num_lines: Annotated[int, "Number of lines to read (0 means read all)"] = 0,
        encoding: Annotated[str, "File encoding (default: 'utf-8')"] = "utf-8",
    ) -> Dict[str, Any]:
        """Read file with enhanced error handling and metadata."""
        try:
            # Handle 0 as None equivalent for optional parameters
            start_line_int = start_line if start_line > 0 else None
            num_lines_int = num_lines if num_lines > 0 else None
            full_path = self.helpers.resolve_path(file_path)

            # Validate file
            if not full_path.exists():
                similar_files = self.helpers.find_similar_files(full_path)
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File '{file_path}' not found",
                    suggestions=[
                        f"Did you mean: {similar}" for similar in similar_files[:3]
                    ]
                    + [
                        "Use find_files() to search for files",
                        "Use list_directory() to explore the directory structure",
                    ],
                ).model_dump()

            if full_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{file_path}' is a directory, not a file",
                    suggestions=[
                        f"Use list_directory('{file_path}') to see directory contents",
                        f"Use find_files('*', '{file_path}') to list files in this directory",
                        "Specify a file path, not a directory path",
                    ],
                ).model_dump()

            # Check file size
            file_size = full_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File too large ({file_size:,} bytes)",
                    suggestions=[
                        f"Use read_file('{file_path}', start_line=1, num_lines=100) "
                        "to read portions",
                        f"Use search_in_files() to find specific content",
                        "Large files should be read in chunks",
                    ],
                ).model_dump()

            # Detect file type
            file_info = self.helpers.create_file_info(full_path)

            # Read file
            try:
                total_lines = self.helpers.count_file_lines(full_path)

                if start_line_int is not None or num_lines_int is not None:
                    # Line-based reading
                    lines = self.helpers.read_file_lines(
                        full_path, start_line_int or 1, num_lines_int or 100, encoding
                    )

                    content_data = {
                        "lines": lines,
                        "line_range": [
                            start_line_int or 1,
                            (start_line_int or 1) + len(lines) - 1,
                        ],
                        "total_lines": total_lines,
                    }

                    suggestions = []
                    if len(lines) < (num_lines_int or 100):
                        suggestions.append(
                            "Reached end of file at line "
                            f"{(start_line_int or 1) + len(lines) - 1}"
                        )
                    else:
                        next_start = (start_line_int or 1) + len(lines)
                        suggestions.append(f"Continue from line {next_start}")

                else:
                    # Read entire file or first 100 lines
                    with open(full_path, "r", encoding=encoding) as f:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= 100:
                                break
                            lines.append(line.rstrip("\n"))

                        # Join lines back into content
                        content = "\n".join(lines)

                    content_data = {
                        "content": content,
                        "line_range": [1, len(lines)],
                        "total_lines": total_lines,
                    }

                    suggestions = []
                    if total_lines > 100:
                        suggestions.append(
                            f"File has {total_lines} lines, showing first 100. "
                            "Continue from line 101"
                        )

                    # Add content-based suggestions
                    suggestions.extend(
                        self.suggestions.generate_content_suggestions(
                            content, file_info
                        )
                    )

                # Deduplicate suggestions
                suggestions = self.suggestions.deduplicate_suggestions(suggestions)

                return PluginResponse(
                    success=True,
                    data=content_data,
                    error=None,
                    suggestions=suggestions,
                    metadata={
                        "encoding": encoding,
                        "truncated": (
                            total_lines > len(lines)
                            if "lines" in content_data
                            else total_lines > 100
                        ),
                    },
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
                        f"Use get_file_info('{file_path}') to check file type",
                    ],
                ).model_dump()

        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Error reading file: {str(e)}",
                suggestions=[
                    "Check file permissions",
                    "Verify the file is not locked by another process",
                    "Try reading a smaller portion of the file",
                ],
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
        - search_in_files("password|secret|key", ["**/*.env", "**/*.config"]) → Security scan""",
    )
    async def search_in_files(
        self,
        pattern: Annotated[str, "Regex pattern to search for"],
        file_patterns: Annotated[
            List[str], "List of glob patterns for files to search"
        ],
        search_path: Annotated[str, "Directory to search in"] = ".",
        case_sensitive: Annotated[bool, "Case sensitive search (default: True)"] = True,
        max_results: Annotated[
            int, "Maximum results to return (default: 50, max: 1000)"
        ] = 50,
        include_context: Annotated[
            bool, "Include surrounding lines (default: True)"
        ] = True,
    ) -> Dict[str, Any]:
        """Search files with enhanced context and metadata."""
        try:
            # Validate and cap max_results
            max_results = min(max_results, 1000)

            search_dir = self.helpers.resolve_path(search_path)

            # Validate search directory
            if not search_dir.exists() or not search_dir.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Search directory '{search_path}' not found or not a directory",
                    suggestions=[
                        "Use list_directory() to find valid directories",
                        "Check if the path is relative to the base directory",
                        "Use '.' to search in current directory",
                    ],
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
                        "Use simpler patterns or literal strings for basic searches",
                    ],
                ).model_dump()

            # Search files
            matches_by_file = {}
            files_searched = 0
            total_matches = 0

            for file_pattern in file_patterns:
                for file_path in self.helpers.find_files(search_dir, file_pattern):
                    files_searched += 1
                    
                    # Calculate how many more matches we can accept
                    remaining_matches = max_results - total_matches
                    if remaining_matches <= 0:
                        # Continue counting files but don't search for more matches
                        continue
                    
                    file_matches = self.helpers.search_in_file(
                        file_path, regex, remaining_matches, include_context
                    )

                    if file_matches:
                        rel_path = str(file_path.relative_to(self._base_path))
                        matches_by_file[rel_path] = file_matches
                        total_matches += len(file_matches)

            # Generate suggestions based on results
            suggestions = self.suggestions.generate_search_suggestions(
                pattern, matches_by_file, files_searched, total_matches, max_results
            )

            # Deduplicate suggestions
            suggestions = self.suggestions.deduplicate_suggestions(suggestions)

            return PluginResponse(
                success=True,
                data={
                    "matches_by_file": matches_by_file,
                    "summary": {
                        "total_matches": total_matches,
                        "files_matched": len(matches_by_file),
                        "files_searched": files_searched,
                    },
                },
                error=None,
                suggestions=suggestions,
                metadata={"truncated": total_matches > max_results},
            ).model_dump()

        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Search error: {str(e)}",
                suggestions=[
                    "Try a simpler search pattern",
                    "Verify file patterns are valid globs",
                    "Check if you have read permissions",
                ],
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
        - get_file_info("data.csv") → Get CSV file stats""",
    )
    async def get_file_info(
        self,
        file_path: Annotated[str, "Path to the file"],
        include_preview: Annotated[
            bool, "Include content preview (default: True)"
        ] = True,
        preview_lines: Annotated[str, "Number of preview lines (default: 10)"] = "10",
    ) -> Dict[str, Any]:
        """Get comprehensive file information."""
        try:
            # Convert string parameter to integer
            try:
                preview_lines_int = int(preview_lines)
            except (ValueError, TypeError):
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"Invalid preview_lines value: '{preview_lines}'. Must be a number.",
                    suggestions=["Provide preview_lines as a number, e.g., '5', '10', '20'"]
                ).model_dump()
            
            full_path = self.helpers.resolve_path(file_path)

            # Validate file
            if not full_path.exists():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"File '{file_path}' not found",
                    suggestions=[
                        "Use find_files() to search for the file",
                        "Check if the path is correct",
                        "Use list_directory() to explore available files",
                    ],
                ).model_dump()

            if full_path.is_dir():
                return PluginResponse(
                    success=False,
                    data=None,
                    error=f"'{file_path}' is a directory",
                    suggestions=[
                        f"Use list_directory('{file_path}') for directory information",
                        "This function is for files only",
                    ],
                ).model_dump()

            # Get file stats
            stat = full_path.stat()
            file_info = self.helpers.create_file_info(full_path)
            is_text = self.helpers.is_text_file(full_path)

            # Prepare simplified file data
            file_data = {
                "path": str(full_path.relative_to(self._base_path)),
                "type": file_info.type,  # Keep semantic type as it adds value
                "size": self.helpers.format_size(stat.st_size),
            }

            # Add content preview if requested
            if include_preview and is_text and stat.st_size < 1024 * 1024:  # 1MB limit
                preview_data = self.helpers.get_file_preview(full_path, preview_lines_int)
                file_data["preview"] = preview_data

            # Generate type-specific suggestions
            suggestions = self.suggestions.generate_file_type_suggestions(
                file_info, stat.st_size
            )

            # Deduplicate suggestions
            suggestions = self.suggestions.deduplicate_suggestions(suggestions)

            return PluginResponse(
                success=True,
                data=file_data,
                error=None,
                suggestions=suggestions,
                metadata={
                    "is_text_file": is_text,
                    "encoding": (
                        self.helpers.guess_encoding(full_path) if is_text else None
                    ),
                },
            ).model_dump()

        except Exception as e:
            return PluginResponse(
                success=False,
                data=None,
                error=f"Error getting file info: {str(e)}",
                suggestions=[
                    "Check if the file is accessible",
                    "Verify file permissions",
                    "Try using list_directory() on parent directory",
                ],
            ).model_dump()
