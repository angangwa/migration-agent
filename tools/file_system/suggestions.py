"""
Suggestion generation logic for FileSystemPlugin.

This module contains all the logic for generating contextual suggestions
to help users navigate and use the FileSystemPlugin effectively.
"""

from typing import List, Dict, Any, Optional
from .models import FileInfo


class SuggestionGenerator:
    """Generates contextual suggestions for FileSystemPlugin operations."""

    @staticmethod
    def deduplicate_suggestions(suggestions: List[str]) -> List[str]:
        """Remove duplicate suggestions while preserving order."""
        seen = set()
        deduplicated = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                deduplicated.append(suggestion)
        return deduplicated

    @staticmethod
    def should_suggest_increase_results(found: int, returned: int) -> bool:
        """Determine if suggesting to increase max_results is helpful."""
        if found <= returned:
            return False

        # Only suggest if the gap is reasonable (< 3x current results)
        gap_ratio = found / returned
        return gap_ratio <= 3.0  # Don't suggest if found is > 3x returned

    @staticmethod
    def get_smart_find_suggestions(
        total_found: int,
        returned: int,
        max_results: int,
        pattern: str,
        search_path: str,
    ) -> List[str]:
        """Generate smart suggestions for find_files based on results."""
        suggestions = []

        if total_found > returned:
            if SuggestionGenerator.should_suggest_increase_results(
                total_found, returned
            ):
                suggestions.append(
                    f"Found {total_found} files but returned only {returned}. "
                    "Increase max_results to see more."
                )
            else:
                # For large gaps, focus on refinement instead
                suggestions.append(
                    f"Found {total_found} files (showing first {returned}). "
                    "Use more specific patterns to narrow results."
                )

            suggestions.append(
                "Consider using more specific patterns to narrow results"
            )

        if not returned:  # No files found
            suggestions.extend(
                [
                    f"No files found matching '{pattern}' in '{search_path}'",
                    "Try a broader pattern like '**/*' to see all files",
                    "Use list_directory() to explore the directory structure",
                    "Check if files have different extensions than expected",
                ]
            )
        else:
            # Add helpful next steps based on pattern
            if pattern.endswith(".py"):
                suggestions.append(
                    "Use search_in_files() to find specific code patterns "
                    "or read_file() to examine specific files"
                )
            elif pattern.endswith((".json", ".yaml", ".yml", ".toml")):
                suggestions.append("Use read_file() to examine configuration files")

            if total_found > 20:
                suggestions.append(
                    "Consider using more specific patterns to narrow results"
                )

        # Cap reached warning
        if max_results >= 1000:
            suggestions.append("Results capped at maximum limit of 1000 files")

        return suggestions

    @staticmethod
    def generate_directory_insights(
        stats: Dict[str, Any], structure: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights and suggestions based on directory analysis."""
        suggestions = []

        # Analyze project type based on file types
        file_types = stats.get("file_types", {})

        if file_types.get("python", 0) > 5:
            suggestions.append(
                "Python project detected. Use search_in_files() to find imports and classes."
            )

        if file_types.get("javascript", 0) > 0 or file_types.get("typescript", 0) > 0:
            suggestions.append(
                "JavaScript/TypeScript project. Check package.json for dependencies."
            )

        if file_types.get("infrastructure", 0) > 0:
            suggestions.append(
                "Infrastructure as Code detected. Examine .tf files for cloud resources."
            )

        if file_types.get("config", 0) > 3:
            suggestions.append(
                "Multiple config files found. Review for environment settings."
            )

        # Check for common project patterns (only if we have structure data)
        if structure and "children" in structure:
            child_names = [
                c["name"] for c in structure["children"] if c["type"] == "directory"
            ]

            if "src" in child_names or "lib" in child_names:
                suggestions.append(
                    "Standard source layout detected. "
                    "Focus analysis on src/ or lib/ directories."
                )

            if "test" in child_names or "tests" in child_names:
                suggestions.append(
                    "Test directory found. Analyze test coverage and patterns."
                )

            if "docs" in child_names or "documentation" in child_names:
                suggestions.append(
                    "Documentation directory found. Check for API docs or guides."
                )

        if stats.get("truncated"):
            suggestions.append(
                "Results truncated. Use more specific paths or increase max_entries."
            )

        return suggestions

    @staticmethod
    def generate_search_suggestions(
        pattern: str,
        matches_by_file: Dict[str, List],
        files_searched: int,
        total_matches: int,
        max_results: int,
    ) -> List[str]:
        """Generate suggestions based on search results."""
        suggestions = []

        # Check if we actually have matches
        files_with_matches = len(matches_by_file) if matches_by_file else 0

        if not matches_by_file or total_matches == 0:
            suggestions.extend(
                [
                    f"No matches found for '{pattern}'",
                    "Try a broader pattern or check the file patterns",
                    "Use case_sensitive=False for case-insensitive search",
                    "Verify files exist with find_files() first",
                ]
            )
        else:
            if total_matches > max_results:
                suggestions.append(
                    f"Found {total_matches} matches but showing only {max_results}. "
                    "Increase max_results or refine pattern."
                )

            # Analyze match distribution
            if files_with_matches == 1:
                suggestions.append(
                    "All matches in single file. Consider searching more broadly."
                )
            elif files_with_matches > 10:
                suggestions.append(
                    "Matches spread across many files. Consider more specific patterns."
                )

            # Pattern-specific suggestions
            if "TODO" in pattern.upper() or "FIXME" in pattern.upper():
                suggestions.append(
                    "Found development markers. Review for pending tasks."
                )
            elif "import" in pattern.lower():
                suggestions.append(
                    "Analyzing imports. Use results to understand dependencies."
                )
            elif any(word in pattern.lower() for word in ["class", "function", "def"]):
                suggestions.append(
                    "Found code definitions. Map out architecture from results."
                )

        suggestions.append(f"Searched {files_searched} files in total")

        return suggestions

    @staticmethod
    def generate_content_suggestions(content: str, file_info: FileInfo) -> List[str]:
        """Generate suggestions based on file content."""
        suggestions = []

        # Language-specific suggestions
        if file_info.type == "python":
            if "import boto3" in content or "from boto3" in content:
                suggestions.append(
                    "AWS SDK detected. Search for specific AWS service usage."
                )
            if "import flask" in content or "from flask" in content:
                suggestions.append(
                    "Flask web framework detected. Look for route definitions."
                )
            if "import django" in content or "from django" in content:
                suggestions.append(
                    "Django framework detected. Check for models and views."
                )

        elif file_info.type in ("javascript", "typescript"):
            if "require(" in content or "import " in content:
                suggestions.append("Module imports found. Analyze dependencies.")
            if "express" in content:
                suggestions.append("Express.js detected. Search for route handlers.")
            if "react" in content.lower():
                suggestions.append("React framework detected. Look for components.")

        elif file_info.type == "config":
            if file_info.name == "package.json":
                suggestions.append(
                    "Node.js project file. Check dependencies and scripts sections."
                )
            elif file_info.name == "requirements.txt":
                suggestions.append(
                    "Python dependencies file. Analyze required packages."
                )
            elif file_info.extension in [".yaml", ".yml"]:
                suggestions.append(
                    "YAML config file. May contain deployment or CI/CD settings."
                )

        elif file_info.type == "infrastructure":
            suggestions.append(
                "Infrastructure as Code file. Analyze cloud resources defined."
            )
            if "aws_" in content:
                suggestions.append(
                    "AWS resources detected. Map to target cloud equivalents."
                )
            if "azurerm_" in content:
                suggestions.append(
                    "Azure resources detected. Check for migration compatibility."
                )

        return suggestions

    @staticmethod
    def generate_file_type_suggestions(file_info: FileInfo, size: int) -> List[str]:
        """Generate suggestions based on file type."""
        suggestions = []

        if file_info.type == "python":
            suggestions.extend(
                [
                    "Use search_in_files() to find specific functions or classes",
                    "Look for import statements to understand dependencies",
                ]
            )
        elif file_info.type in ["javascript", "typescript"]:
            suggestions.extend(
                [
                    "Check for framework usage (React, Vue, Angular)",
                    "Analyze import/require statements for dependencies",
                ]
            )
        elif file_info.type == "config":
            suggestions.extend(
                [
                    "Parse configuration for environment-specific settings",
                    "Look for API keys, endpoints, or service configurations",
                ]
            )
        elif file_info.type == "infrastructure":
            suggestions.extend(
                [
                    "Analyze cloud resources and their configurations",
                    "Map infrastructure to target cloud provider",
                ]
            )

        if size > 1024 * 1024:  # 1MB
            suggestions.append(
                "Large file. Consider reading in chunks using line ranges."
            )

        return suggestions
