"""
Helper utilities for FileSystemPlugin.

This module contains core utility functions and classes that support
the main FileSystemPlugin operations.
"""

import re
import json
import fnmatch
from pathlib import Path
from typing import List, Dict, Any

from .models import FileInfo, FILE_TYPE_MAPPINGS


class FileSystemHelpers:
    """Core helper utilities for file system operations."""

    def __init__(self, base_path: Path):
        """Initialize helpers with base path."""
        self.base_path = base_path

    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path relative to the base path."""
        path = Path(path_str)
        if path.is_absolute():
            return path
        return (self.base_path / path).resolve()

    def should_exclude_file(self, rel_path: str, exclude_patterns: set) -> bool:
        """Check if a file should be excluded based on patterns."""
        if not exclude_patterns:
            return False

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # Also check if any parent directory matches
            parts = rel_path.split("/")
            for i in range(len(parts)):
                partial_path = "/".join(parts[: i + 1])
                if fnmatch.fnmatch(partial_path + "/*", pattern):
                    return True
        return False

    def find_files(self, directory: Path, pattern: str) -> List[Path]:
        """Find files matching a pattern in a directory."""
        if "**" in pattern:
            return list(directory.glob(pattern))

        matches = []
        try:
            for item in directory.iterdir():
                if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                    matches.append(item)
        except PermissionError:
            pass
        return matches

    def create_file_info(self, file_path: Path) -> FileInfo:
        """Create FileInfo object from path."""
        extension = file_path.suffix.lower()
        file_type = FILE_TYPE_MAPPINGS.get(extension, "other")

        # Special case for files without extensions
        if not extension and file_path.name.lower() in [
            "dockerfile",
            "makefile",
            "jenkinsfile",
        ]:
            file_type = "config"

        return FileInfo(
            path=str(file_path.relative_to(self.base_path)),
            name=file_path.name,
            extension=extension,
            type=file_type,
        )

    def read_file_lines(
        self, file_path: Path, start_line: int, num_lines: int, encoding: str
    ) -> List[str]:
        """Read specific lines from a file."""
        lines = []
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            # Skip to start line
            for _ in range(start_line - 1):
                if not f.readline():
                    return []

            # Read requested lines
            for _ in range(num_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))

        return lines

    def count_file_lines(self, file_path: Path) -> int:
        """Count total lines in a file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)

    def search_in_file(
        self,
        file_path: Path,
        regex: re.Pattern,
        max_matches: int,
        include_context: bool,
    ) -> List[Dict[str, Any]]:
        """Search for pattern in a single file."""
        matches = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if len(matches) >= max_matches:
                    break

                match = regex.search(line)
                if match:
                    match_data = {"line": i + 1, "content": line.rstrip("\n")}

                    if include_context:
                        context = {}
                        if i > 0:
                            context["before"] = lines[i - 1].rstrip("\n")
                        else:
                            context["before"] = ""

                        if i < len(lines) - 1:
                            context["after"] = lines[i + 1].rstrip("\n")
                        else:
                            context["after"] = ""

                        match_data["context"] = context

                    matches.append(match_data)

        except Exception:
            # Skip files that can't be read
            pass

        return matches

    def find_similar_files(self, target_path: Path) -> List[str]:
        """Find files with similar names."""
        similar = []
        parent = target_path.parent
        target_name = target_path.name.lower()

        if parent.exists():
            for file in parent.iterdir():
                if file.is_file():
                    similarity = self._calculate_similarity(
                        target_name, file.name.lower()
                    )
                    if similarity > 0.6:
                        similar.append(str(file.relative_to(self.base_path)))

        return sorted(similar)[:5]

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (simple approach)."""
        if s1 == s2:
            return 1.0

        # Simple character overlap ratio
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_file_preview(self, file_path: Path, preview_lines: int) -> Dict[str, Any]:
        """Get file content preview."""
        try:
            lines = self.read_file_lines(file_path, 1, preview_lines, "utf-8")

            # Try to detect file structure
            content_type = "text"
            if file_path.suffix == ".json":
                try:
                    full_content = file_path.read_text()
                    json_data = json.loads(full_content)
                    content_type = "json"
                    lines = json.dumps(json_data, indent=2).splitlines()[:preview_lines]
                except Exception:
                    pass

            return {
                "lines": lines,
                "content_type": content_type,
                "truncated": len(lines) == preview_lines,
            }
        except Exception:
            return {
                "lines": [],
                "content_type": "binary",
                "truncated": False,
                "error": "Cannot preview binary file",
            }

    def is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely text based."""
        text_extensions = {
            ".txt",
            ".md",
            ".rst",
            ".log",
            ".csv",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".sh",
            ".bat",
            ".ps1",
            ".sql",
            ".html",
            ".css",
            ".scss",
            ".less",
            ".jsx",
            ".tsx",
            ".vue",
            ".tf",
            ".tfvars",
        }
        return file_path.suffix.lower() in text_extensions

    def guess_encoding(self, file_path: Path) -> str:
        """Guess file encoding."""
        # Simple approach - could be enhanced with chardet
        try:
            with open(file_path, "rb") as f:
                sample = f.read(1024)

            # Try UTF-8 first
            try:
                sample.decode("utf-8")
                return "utf-8"
            except UnicodeDecodeError:
                pass

            # Try other common encodings
            for encoding in ["latin-1", "utf-16", "cp1252"]:
                try:
                    sample.decode(encoding)
                    return encoding
                except UnicodeDecodeError:
                    pass

            return "unknown"
        except Exception:
            return "unknown"


class TreeBuilder:
    """Builds directory tree structures for display."""

    def __init__(self, helpers: FileSystemHelpers):
        """Initialize with helpers instance."""
        self.helpers = helpers

    def build_tree_string(
        self,
        path: Path,
        max_depth: int,
        max_entries: int,
        exclude_patterns: set,
        include_hidden: bool,
    ) -> tuple:
        """Build a tree-formatted string representation of directory structure."""
        tree_lines = []
        entry_count = 0
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "file_types": {},
            "max_depth_reached": 0,
            "truncated": False,
        }

        def add_node(current_path: Path, prefix: str, is_last: bool, depth: int):
            nonlocal entry_count

            if entry_count >= max_entries:
                stats["truncated"] = True
                return

            if depth > max_depth:
                return

            stats["max_depth_reached"] = max(stats["max_depth_reached"], depth)

            name = current_path.name
            if name in exclude_patterns and not include_hidden:
                return

            if not include_hidden and name.startswith("."):
                return

            # Prepare the tree branch characters
            if depth > 0:
                connector = "└── " if is_last else "├── "
                line_prefix = prefix + connector
            else:
                line_prefix = ""

            if current_path.is_file():
                stats["total_files"] += 1
                file_info = self.helpers.create_file_info(current_path)
                stats["file_types"][file_info.type] = (
                    stats["file_types"].get(file_info.type, 0) + 1
                )

                # Show files only if we're not at max depth
                if depth < max_depth:
                    tree_lines.append(f"{line_prefix}{name}")
                    entry_count += 1

            elif current_path.is_dir():
                stats["total_dirs"] += 1

                # Count children for the directory annotation
                try:
                    children = list(current_path.iterdir())
                    # Filter based on hidden/exclude rules
                    if not include_hidden:
                        children = [
                            c
                            for c in children
                            if not c.name.startswith(".")
                            and c.name not in exclude_patterns
                        ]

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

                            is_last_child = i == len(children) - 1
                            add_node(child, child_prefix, is_last_child, depth + 1)

                except PermissionError:
                    pass

        # Start building from the root
        add_node(path, "", True, 0)

        tree_str = "\n".join(tree_lines)
        return tree_str, stats
