"""
Lightweight Repository Analyzer

Fast repository analysis for extracting basic metadata including
languages, frameworks, file statistics, and configuration detection.
Optimized for bulk analysis of multiple repositories.
"""

import json
import re
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, Counter

from .models import (
    RepoMetadata, TechnologyStack, RepositoryType,
    LANGUAGE_MAPPINGS, CONFIG_PATTERNS, FRAMEWORK_PATTERNS
)


class RepositoryAnalyzer:
    """Fast, lightweight repository analyzer."""
    
    def __init__(self, base_path: Path):
        """Initialize analyzer with base repository path."""
        self.base_path = base_path
        
        # Directories to ignore during analysis
        self.ignore_dirs = {
            '.git', '.svn', '.hg',
            'node_modules', '__pycache__', '.pytest_cache',
            'target', 'build', 'dist', '.gradle',
            'venv', '.venv', 'env', '.env',
            '.idea', '.vscode', '.vs',
            'logs', 'log', 'tmp', 'temp'
        }
        
        # Files to ignore
        self.ignore_files = {
            '.gitignore', '.gitkeep', '.DS_Store',
            'Thumbs.db', '.env.example'
        }
        
        # Maximum files to scan for performance (prevent huge repos from slowing down)
        self.max_files_scan = 5000
    
    def analyze_repository(self, repo_path: Path) -> RepoMetadata:
        """
        Perform fast analysis of a single repository.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            RepoMetadata with analysis results
        """
        repo_name = repo_path.name
        relative_path = str(repo_path.relative_to(self.base_path))
        
        # Initialize metadata
        metadata = RepoMetadata(
            name=repo_name,
            path=relative_path
        )
        
        try:
            # Basic file statistics
            file_stats = self._analyze_file_structure(repo_path)
            metadata.total_files = file_stats['total_files']
            metadata.file_counts = file_stats['file_counts']
            metadata.total_lines = file_stats['total_lines']
            
            # Language detection
            metadata.technology_stack.primary_languages = self._detect_languages(
                file_stats['file_counts']
            )
            
            # Configuration file detection
            config_files = self._find_config_files(repo_path)
            metadata.config_files = config_files
            
            # Framework detection
            frameworks = self._detect_frameworks(repo_path, config_files)
            metadata.technology_stack.frameworks = frameworks
            
            # Repository type classification
            metadata.repository_type = self._classify_repository_type(
                repo_path, file_stats, config_files, frameworks
            )
            
            # Documentation detection
            doc_info = self._analyze_documentation(repo_path)
            metadata.has_readme = doc_info['has_readme']
            
            # Skip unused technology detection that is not exposed to LLM
            
            # Set analysis confidence based on data completeness
            metadata.analysis_confidence = self._calculate_confidence(metadata)
            
            # Update discovery status
            metadata.update_discovery_status()
            
        except Exception as e:
            # On error, return partial metadata with error info
            metadata.insights['analysis_error'] = str(e)
            metadata.analysis_confidence = 0.0
            
        return metadata
    
    def _analyze_file_structure(self, repo_path: Path) -> Dict:
        """Analyze file structure and get basic statistics."""
        file_counts = defaultdict(int)
        total_files = 0
        total_size = 0
        total_lines = 0
        files_scanned = 0
        
        for root, dirs, files in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                if files_scanned >= self.max_files_scan:
                    break
                    
                if file in self.ignore_files:
                    continue
                    
                file_path = Path(root) / file
                try:
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    # Count by extension
                    extension = file_path.suffix.lower()
                    file_counts[extension] += 1
                    total_files += 1
                    
                    # Count exact lines for all text files (not just code files)
                    if file_size < 1024 * 1024:  # < 1MB to avoid huge files
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_lines = sum(1 for line in f)
                                total_lines += file_lines
                        except (UnicodeDecodeError, OSError, PermissionError):
                            # For binary files or read errors, skip line counting
                            pass
                    
                    files_scanned += 1
                    
                except (OSError, PermissionError):
                    continue
            
            if files_scanned >= self.max_files_scan:
                break
        
        return {
            'total_files': total_files,
            'file_counts': dict(file_counts),
            'repository_size': total_size,
            'total_lines': total_lines,
            'files_scanned': files_scanned
        }
    
    def _detect_languages(self, file_counts: Dict[str, int]) -> List[Tuple[str, float]]:
        """Detect programming languages based on file extensions."""
        language_counts = defaultdict(int)
        total_code_files = 0
        
        for ext, count in file_counts.items():
            if ext in LANGUAGE_MAPPINGS:
                language = LANGUAGE_MAPPINGS[ext]
                language_counts[language] += count
                total_code_files += count
        
        if total_code_files == 0:
            return []
        
        # Calculate confidence scores
        languages = []
        for language, count in language_counts.items():
            confidence = count / total_code_files
            languages.append((language, confidence))
        
        # Sort by confidence descending
        languages.sort(key=lambda x: x[1], reverse=True)
        
        return languages[:5]  # Return top 5 languages
    
    def _find_config_files(self, repo_path: Path) -> List[str]:
        """Find configuration files in the repository."""
        config_files = []
        
        for config_file in CONFIG_PATTERNS.keys():
            config_path = repo_path / config_file
            if config_path.exists():
                config_files.append(config_file)
        
        # Also check for other common config files
        other_configs = [
            'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
            '.dockerignore', 'Jenkinsfile', '.gitlab-ci.yml',
            'azure-pipelines.yml', 'bitbucket-pipelines.yml',
            '.github/workflows', '.circleci/config.yml',
            'terraform', 'k8s', 'kubernetes', 'helm'
        ]
        
        # Check for .NET project files
        dotnet_patterns = ['*.csproj', '*.vbproj', '*.fsproj', '*.sln']
        for pattern in dotnet_patterns:
            if list(repo_path.glob(pattern)):
                config_files.append(pattern.replace('*', ''))  # Add without wildcard for reporting
        
        for config in other_configs:
            config_path = repo_path / config
            if config_path.exists():
                config_files.append(config)
        
        return config_files
    
    def _detect_frameworks(self, repo_path: Path, config_files: List[str]) -> List[str]:
        """Detect frameworks by parsing configuration files."""
        frameworks = set()
        
        # Parse package.json for JavaScript/TypeScript frameworks
        if 'package.json' in config_files:
            frameworks.update(self._parse_package_json(repo_path / 'package.json'))
        
        # Parse requirements.txt for Python frameworks
        if 'requirements.txt' in config_files:
            frameworks.update(self._parse_requirements_txt(repo_path / 'requirements.txt'))
        
        # Parse pom.xml for Java frameworks
        if 'pom.xml' in config_files:
            frameworks.update(self._parse_pom_xml(repo_path / 'pom.xml'))
        
        # Parse pyproject.toml for Python
        if 'pyproject.toml' in config_files:
            frameworks.update(self._parse_pyproject_toml(repo_path / 'pyproject.toml'))
        
        # Parse .csproj files for .NET
        csproj_files = list(repo_path.glob('**/*.csproj'))
        for csproj_file in csproj_files[:5]:  # Limit to 5 files for performance
            frameworks.update(self._parse_csproj_file(csproj_file))
        
        # Parse packages.config for .NET Framework
        if 'packages.config' in config_files:
            frameworks.update(self._parse_packages_config(repo_path / 'packages.config'))
        
        return list(frameworks)
    
    def _parse_package_json(self, package_path: Path) -> Set[str]:
        """Parse package.json for framework detection."""
        frameworks = set()
        
        try:
            with open(package_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check dependencies and devDependencies
            all_deps = {}
            all_deps.update(data.get('dependencies', {}))
            all_deps.update(data.get('devDependencies', {}))
            
            for dep_name in all_deps.keys():
                for framework, patterns in FRAMEWORK_PATTERNS.items():
                    if any(pattern.lower() in dep_name.lower() for pattern in patterns):
                        frameworks.add(framework)
                        
                # Specific framework detection
                if 'express' in dep_name.lower():
                    frameworks.add('Express.js')
                elif 'react' in dep_name.lower():
                    frameworks.add('React')
                elif 'vue' in dep_name.lower():
                    frameworks.add('Vue.js')
                elif 'angular' in dep_name.lower():
                    frameworks.add('Angular')
                elif 'nest' in dep_name.lower():
                    frameworks.add('NestJS')
                elif 'next' in dep_name.lower():
                    frameworks.add('Next.js')
                    
        except (json.JSONDecodeError, OSError):
            pass
            
        return frameworks
    
    def _parse_requirements_txt(self, req_path: Path) -> Set[str]:
        """Parse requirements.txt for Python framework detection."""
        frameworks = set()
        
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip().lower()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Extract package name (before ==, >=, etc.)
                    package = re.split(r'[=<>!]', line)[0].strip()
                    
                    if 'django' in package:
                        frameworks.add('Django')
                    elif 'flask' in package:
                        frameworks.add('Flask')
                    elif 'fastapi' in package:
                        frameworks.add('FastAPI')
                    elif 'tornado' in package:
                        frameworks.add('Tornado')
                    elif 'pyramid' in package:
                        frameworks.add('Pyramid')
                        
        except OSError:
            pass
            
        return frameworks
    
    def _parse_pom_xml(self, pom_path: Path) -> Set[str]:
        """Parse pom.xml for Java framework detection."""
        frameworks = set()
        
        try:
            with open(pom_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            if 'spring-boot' in content:
                frameworks.add('Spring Boot')
            elif 'springframework' in content:
                frameworks.add('Spring Framework')
            
            if 'hibernate' in content:
                frameworks.add('Hibernate')
                
        except OSError:
            pass
            
        return frameworks
    
    def _parse_pyproject_toml(self, toml_path: Path) -> Set[str]:
        """Parse pyproject.toml for Python framework detection."""
        frameworks = set()
        
        try:
            with open(toml_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            # Simple text-based detection
            if 'django' in content:
                frameworks.add('Django')
            if 'flask' in content:
                frameworks.add('Flask')
            if 'fastapi' in content:
                frameworks.add('FastAPI')
                
        except OSError:
            pass
            
        return frameworks
    
    def _parse_csproj_file(self, csproj_path: Path) -> Set[str]:
        """Parse .csproj files for .NET framework detection."""
        frameworks = set()
        
        try:
            with open(csproj_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for .NET Core/5+
            if '<TargetFramework>' in content or '<TargetFrameworks>' in content:
                if 'net5' in content or 'net6' in content or 'net7' in content or 'net8' in content:
                    frameworks.add('.NET 5+')
                elif 'netcoreapp' in content:
                    frameworks.add('.NET Core')
                elif 'netstandard' in content:
                    frameworks.add('.NET Standard')
                elif 'net4' in content:
                    frameworks.add('.NET Framework')
            
            # Check for specific packages
            content_lower = content.lower()
            if 'microsoft.aspnetcore' in content_lower:
                frameworks.add('ASP.NET Core')
            if 'microsoft.entityframeworkcore' in content_lower:
                frameworks.add('Entity Framework Core')
            if 'entityframework' in content_lower:
                frameworks.add('Entity Framework')
            if 'microsoft.windowsdesktop' in content_lower:
                frameworks.add('WPF')
            if 'system.windows.forms' in content_lower:
                frameworks.add('WinForms')
            if 'blazor' in content_lower:
                frameworks.add('Blazor')
            if 'signalr' in content_lower:
                frameworks.add('SignalR')
            if 'xamarin' in content_lower:
                frameworks.add('Xamarin')
            if 'microsoft.maui' in content_lower:
                frameworks.add('MAUI')
                
        except (OSError, UnicodeDecodeError):
            pass
            
        return frameworks
    
    def _parse_packages_config(self, config_path: Path) -> Set[str]:
        """Parse packages.config for .NET Framework packages."""
        frameworks = set()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            if 'entityframework' in content:
                frameworks.add('Entity Framework')
            if 'microsoft.aspnet' in content:
                frameworks.add('ASP.NET Framework')
            if 'signalr' in content:
                frameworks.add('SignalR')
            if 'microsoft.owin' in content:
                frameworks.add('OWIN')
                
        except (OSError, UnicodeDecodeError):
            pass
            
        return frameworks
    
    def _classify_repository_type(
        self, 
        repo_path: Path, 
        file_stats: Dict, 
        config_files: List[str],
        frameworks: List[str]
    ) -> RepositoryType:
        """Classify repository type based on analysis."""
        
        # Check for documentation-only repos
        if (file_stats['total_files'] < 10 and 
            any(ext in ['.md', '.rst', '.txt'] for ext in file_stats['file_counts'].keys())):
            return RepositoryType.DOCUMENTATION
        
        # Check for configuration-only repos
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.conf'}
        if (file_stats['total_files'] < 50 and 
            sum(file_stats['file_counts'].get(ext, 0) for ext in config_extensions) > 
            file_stats['total_files'] * 0.7):
            return RepositoryType.CONFIG
        
        # Check for library indicators
        library_indicators = ['setup.py', 'package.json', 'pom.xml', 'Cargo.toml']
        has_library_config = any(config in config_files for config in library_indicators)
        
        # Check for application entry points
        entry_points = ['main.py', 'app.py', 'server.js', 'index.js', 'Main.java', 'main.go']
        has_entry_point = any((repo_path / entry).exists() for entry in entry_points)
        
        # Check for microservice indicators
        microservice_indicators = ['Dockerfile', 'kubernetes', 'k8s', 'helm']
        has_microservice_config = any(config in config_files for config in microservice_indicators)
        
        if has_entry_point and has_microservice_config:
            return RepositoryType.MICROSERVICE
        elif has_entry_point and file_stats['total_lines'] > 10000:
            return RepositoryType.MONOLITH
        elif has_library_config and not has_entry_point:
            return RepositoryType.LIBRARY
        elif has_entry_point:
            return RepositoryType.MICROSERVICE
        else:
            return RepositoryType.UNKNOWN
    
    def _analyze_documentation(self, repo_path: Path) -> Dict:
        """Analyze documentation files in the repository."""
        doc_files = []
        has_readme = False
        
        doc_patterns = ['README*', 'CHANGELOG*', 'CONTRIBUTING*', 'LICENSE*', 'INSTALL*', 'docs/*']
        
        for pattern in doc_patterns:
            for doc_file in repo_path.glob(pattern):
                if doc_file.is_file():
                    relative_path = str(doc_file.relative_to(repo_path))
                    doc_files.append(relative_path)
                    
                    if doc_file.name.upper().startswith('README'):
                        has_readme = True
        
        return {
            'has_readme': has_readme
        }
    
    
    
    
    
    def _calculate_confidence(self, metadata: RepoMetadata) -> float:
        """Calculate analysis confidence score."""
        confidence_factors = []
        
        # Language detection confidence
        if metadata.technology_stack.primary_languages:
            confidence_factors.append(0.3)
        
        # Framework detection confidence
        if metadata.technology_stack.frameworks:
            confidence_factors.append(0.2)
        
        # Configuration files found
        if metadata.config_files:
            confidence_factors.append(0.2)
        
        # Repository type classified
        if metadata.repository_type != RepositoryType.UNKNOWN:
            confidence_factors.append(0.2)
        
        # Documentation present
        if metadata.has_readme:
            confidence_factors.append(0.1)
        
        return sum(confidence_factors)