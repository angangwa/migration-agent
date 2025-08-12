"""
Helper utilities for DiscoveryMemoryPlugin

Provides utility functions for parallel processing, validation,
and data manipulation to support the main plugin functionality.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

from .models import RepoMetadata, ComponentData, AnalysisState


class ParallelProcessor:
    """Handles parallel processing of repository analysis."""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
    
    def process_repositories(
        self, 
        repo_paths: List[Path],
        analyzer_func: Callable[[Path], RepoMetadata],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, RepoMetadata]:
        """
        Process multiple repositories in parallel.
        
        Args:
            repo_paths: List of repository paths to analyze
            analyzer_func: Function to analyze a single repository
            progress_callback: Optional callback for progress updates (current, total, repo_name)
            
        Returns:
            Dictionary mapping repo names to RepoMetadata
        """
        results = {}
        completed = 0
        total = len(repo_paths)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_path = {
                executor.submit(analyzer_func, repo_path): repo_path 
                for repo_path in repo_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                repo_path = future_to_path[future]
                repo_name = repo_path.name
                
                try:
                    metadata = future.result()
                    results[repo_name] = metadata
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total, repo_name)
                        
                except Exception as e:
                    # Create error metadata for failed analysis
                    error_metadata = RepoMetadata(
                        name=repo_name,
                        path=str(repo_path.relative_to(repo_path.parent.parent))
                    )
                    error_metadata.insights['analysis_error'] = str(e)
                    results[repo_name] = error_metadata
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total, f"{repo_name} (ERROR)")
        
        return results


class ValidationHelper:
    """Provides validation utilities for discovery data."""
    
    @staticmethod
    def validate_component_size(component_data: ComponentData, repo_count: int) -> Dict[str, Any]:
        """
        Validate component size according to discovery agent guidelines.
        
        Args:
            component_data: Component to validate
            repo_count: Number of repositories in component
            
        Returns:
            Validation result with warnings and suggestions
        """
        warnings = []
        suggestions = []
        
        if repo_count >= 30:
            warnings.append("Component is too large (30+ repositories)")
            suggestions.append("Consider splitting into smaller, focused components")
            
        elif repo_count == 1:
            warnings.append("Component contains only one repository")
            suggestions.append("Consider if this represents a major standalone system")
            
        elif repo_count < 3:
            warnings.append("Component is quite small (<3 repositories)")
            suggestions.append("Consider merging with related components if appropriate")
        
        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings,
            'suggestions': suggestions,
            'size_category': ValidationHelper._get_size_category(repo_count)
        }
    
    @staticmethod
    def _get_size_category(repo_count: int) -> str:
        """Get size category for component."""
        if repo_count >= 30:
            return "too_large"
        elif repo_count >= 3:
            return "appropriate"
        elif repo_count == 1:
            return "single_repo"
        else:
            return "too_small"
    
    @staticmethod
    def validate_repo_assignments(state: AnalysisState) -> Dict[str, Any]:
        """
        Validate repository component assignments.
        
        Args:
            state: Current analysis state
            
        Returns:
            Validation summary with issues and suggestions
        """
        unassigned_repos = []
        multi_assigned_repos = []
        orphaned_components = []
        
        # Check for unassigned repositories
        for repo_name, repo_data in state.repositories.items():
            if not repo_data.assigned_components:
                unassigned_repos.append(repo_name)
            elif len(repo_data.assigned_components) > 1:
                multi_assigned_repos.append({
                    'repo': repo_name,
                    'components': repo_data.assigned_components
                })
        
        # Check for empty components
        for comp_name, comp_data in state.components.items():
            if not comp_data.repositories:
                orphaned_components.append(comp_name)
        
        return {
            'unassigned_repos': unassigned_repos,
            'multi_assigned_repos': multi_assigned_repos,
            'orphaned_components': orphaned_components,
            'assignment_coverage': (
                (len(state.repositories) - len(unassigned_repos)) / len(state.repositories) * 100
                if state.repositories else 0
            )
        }


class ReportGenerator:
    """Generates comprehensive discovery reports."""
    
    @staticmethod
    def generate_discovery_report(state: AnalysisState) -> str:
        """
        Generate comprehensive discovery report in markdown format.
        
        Args:
            state: Analysis state to generate report from
            
        Returns:
            Markdown-formatted discovery report
        """
        report_lines = []
        
        # Header
        report_lines.extend([
            "# Legacy Application Discovery Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Base Path:** `{state.base_repos_path}`",
            ""
        ])
        
        # Executive Summary
        progress = state.get_progress_summary()
        report_lines.extend([
            "## Executive Summary",
            "",
            f"- **Total Repositories:** {progress['total_repositories']}",
            f"- **Investigation Progress:** {progress['investigation_progress']:.1f}%",
            f"- **Repositories with Insights:** {progress['repositories_with_insights']}",
            f"- **Logical Components:** {progress['components_created']}",
            f"- **Unassigned Repositories:** {progress['unassigned_repos']}",
            ""
        ])
        
        # Repository Inventory
        report_lines.extend([
            "## Repository Inventory",
            ""
        ])
        
        # Group repositories by discovery phase status
        by_status = {
            'complete': [],  # Has insights and assigned to components
            'needs_assignment': [],  # Has insights but not assigned
            'needs_investigation': []  # No insights
        }
        
        for repo_name, repo_data in state.repositories.items():
            if repo_data.insights and repo_data.assigned_components:
                by_status['complete'].append((repo_name, repo_data))
            elif repo_data.insights and not repo_data.assigned_components:
                by_status['needs_assignment'].append((repo_name, repo_data))
            else:
                by_status['needs_investigation'].append((repo_name, repo_data))
        
        status_titles = {
            'complete': 'Complete (Has Insights & Assigned)',
            'needs_assignment': 'Needs Component Assignment',
            'needs_investigation': 'Needs Investigation'
        }
        
        for status, repos in by_status.items():
            if repos:
                report_lines.extend([
                    f"### {status_titles[status]} ({len(repos)})",
                    ""
                ])
                
                for repo_name, repo_data in sorted(repos):
                    # Build technical details only if we have actual data
                    tech_details = []
                    
                    # Show frameworks if detected
                    if repo_data.technology_stack.frameworks:
                        frameworks = ", ".join(repo_data.technology_stack.frameworks[:5])  # Show more frameworks
                        tech_details.append(f"- Frameworks: {frameworks}")
                    
                    # Show file type breakdown (top file types)
                    if repo_data.file_counts:
                        # Get top 5 file types
                        sorted_files = sorted(repo_data.file_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                        file_types = ", ".join([f"{ext}: {count}" for ext, count in sorted_files])
                        tech_details.append(f"- File types: {file_types}")
                    
                    # Always show basic stats
                    tech_details.extend([
                        f"- Files: {repo_data.total_files:,}",
                        f"- Lines: {repo_data.total_lines:,}"
                    ])
                    
                    # Show discovery status and components
                    tech_details.extend([
                        f"- Status: {repo_data.discovery_phase_status}",
                        f"- Components: {', '.join(repo_data.assigned_components) or 'Unassigned'}"
                    ])
                    
                    report_lines.extend([
                        f"**{repo_name}**",
                        *tech_details
                    ])
                    
                    # Add insights if available
                    if repo_data.insights:
                        report_lines.append("- **Insights:**")
                        for key, value in repo_data.insights.items():
                            if key != 'analysis_error':  # Skip error entries
                                report_lines.append(f"  - {key}: {value}")
                    
                    report_lines.append("")  # Empty line between repos
        
        # Logical Components Analysis
        if state.components:
            report_lines.extend([
                "## Logical Components Analysis",
                ""
            ])
            
            for comp_name, comp_data in sorted(state.components.items()):
                validation = ValidationHelper.validate_component_size(comp_data, len(comp_data.repositories))
                
                report_lines.extend([
                    f"### {comp_name}",
                    "",
                    f"**Purpose:** {comp_data.purpose}",
                    "",
                    f"**Rationale:** {comp_data.rationale}",
                    "",
                    f"**Repositories ({len(comp_data.repositories)}):** {', '.join(comp_data.repositories)}",
                    "",
                    f"**Size Assessment:** {validation['size_category'].replace('_', ' ').title()}",
                    ""
                ])
                
                if validation['warnings']:
                    report_lines.extend([
                        "**Warnings:**",
                        *[f"- {warning}" for warning in validation['warnings']],
                        ""
                    ])
        
        # Technology Stack Summary
        tech_summary = ReportGenerator._generate_tech_summary(state)
        if tech_summary:
            report_lines.extend([
                "## Technology Stack Summary",
                "",
                tech_summary,
                ""
            ])
        
        # Validation Results
        validation_results = ValidationHelper.validate_repo_assignments(state)
        report_lines.extend([
            "## Assignment Validation",
            "",
            f"**Coverage:** {validation_results['assignment_coverage']:.1f}% of repositories assigned",
            ""
        ])
        
        if validation_results['unassigned_repos']:
            report_lines.extend([
                f"**Unassigned Repositories ({len(validation_results['unassigned_repos'])}):**",
                *[f"- {repo}" for repo in validation_results['unassigned_repos']],
                ""
            ])
        
        if validation_results['multi_assigned_repos']:
            report_lines.extend([
                "**Multi-assigned Repositories:**",
                *[f"- {item['repo']}: {', '.join(item['components'])}" for item in validation_results['multi_assigned_repos']],
                ""
            ])
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            "### Immediate Actions",
        ])
        
        recommendations = ReportGenerator._generate_recommendations(state, validation_results)
        report_lines.extend(recommendations)
        
        return "\n".join(report_lines)
    
    @staticmethod
    def _generate_tech_summary(state: AnalysisState) -> str:
        """Generate technology stack summary."""
        if not state.repositories:
            return ""
        
        framework_counts = {}
        
        for repo_data in state.repositories.values():
            # Count frameworks
            for framework in repo_data.technology_stack.frameworks:
                framework_counts[framework] = framework_counts.get(framework, 0) + 1
        
        lines = []
        
        if framework_counts:
            lines.append("**Frameworks:**")
            for framework, count in sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"- {framework}: {count} repositories")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _generate_recommendations(state: AnalysisState, validation_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if validation_results['unassigned_repos']:
            recommendations.extend([
                f"1. **Assign {len(validation_results['unassigned_repos'])} unassigned repositories** to appropriate components",
                "   - Review repository purposes and group by business function or technology stack",
                ""
            ])
        
        # Check for components that might need splitting
        large_components = []
        for comp_name, comp_data in state.components.items():
            if len(comp_data.repositories) >= 20:
                large_components.append(comp_name)
        
        if large_components:
            recommendations.extend([
                f"2. **Review large components** for potential splitting:",
                *[f"   - {comp}: {len(state.components[comp].repositories)} repositories" for comp in large_components],
                ""
            ])
        
        # Check investigation progress
        progress = state.get_progress_summary()
        if progress['investigation_progress'] < 100:
            remaining = progress['total_repositories'] - progress['repositories_with_insights']
            recommendations.extend([
                f"3. **Complete investigation** of {remaining} remaining repositories",
                "   - Use filesystem tools to understand repository purposes",
                "   - Store detailed insights using store_repo_insights()",
                ""
            ])
        
        if not recommendations:
            recommendations.extend([
                "1. **Discovery appears complete** - all repositories have insights and are assigned",
                "2. **Ready for next phase** - detailed migration planning can begin",
                ""
            ])
        
        return recommendations


def find_repositories(base_path: Path) -> List[Path]:
    """
    Find all repository directories in the base path.
    
    Args:
        base_path: Base path to search for repositories
        
    Returns:
        List of repository paths
    """
    repo_paths = []
    
    if not base_path.exists():
        return repo_paths
    
    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if it's a git repository or just a directory with files
            if (item / '.git').exists() or any(item.iterdir()):
                repo_paths.append(item)
    
    return sorted(repo_paths)


def format_progress_message(current: int, total: int, repo_name: str) -> str:
    """Format progress message for console output."""
    percentage = (current / total * 100) if total > 0 else 0
    return f"[{current}/{total}] ({percentage:.1f}%) Analyzing: {repo_name}"