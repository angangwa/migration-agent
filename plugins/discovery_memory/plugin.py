"""
DiscoveryMemoryPlugin

Main plugin class providing repository analysis and working memory management
for the Discovery Agent. Combines automated repository analysis with persistent
memory storage to support efficient discovery of large enterprise codebases.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Annotated
from datetime import datetime

from semantic_kernel.functions import kernel_function

from .models import (
    PluginResponse, RepoMetadata, ComponentData, AnalysisState, AnalysisStatus
)
from .analyzer import RepositoryAnalyzer
from .storage import DiscoveryStorage
from .helpers import ParallelProcessor, ValidationHelper, ReportGenerator, find_repositories


class DiscoveryMemoryPlugin:
    """
    Discovery Memory Plugin for repository analysis and working memory management.
    
    Provides all functions required by the Discovery Agent to analyze multiple
    repositories and categorize them into logical components with persistent storage.
    """
    
    def __init__(self, repos_path: Optional[str] = None, storage_dir: Optional[str] = None, **kwargs):
        """
        Initialize the Discovery Memory Plugin.
        
        Args:
            repos_path: Path to directory containing repositories (default: './repos')
            storage_dir: Directory for cache storage (default: './.discovery_cache')
            **kwargs: Additional arguments
        """
        super().__init__(**kwargs)
        
        # Initialize paths
        self.repos_path = Path(repos_path) if repos_path else Path('./repos')
        storage_path = Path(storage_dir) if storage_dir else Path('./.discovery_cache')
        
        # Initialize components
        self.analyzer = RepositoryAnalyzer(self.repos_path)
        self.storage = DiscoveryStorage(storage_path)
        self.parallel_processor = ParallelProcessor(max_workers=4)
        
        # Load or initialize state
        self.state = self.storage.load_state(str(self.repos_path))
        
        # Track if initial analysis has been performed
        self._initial_analysis_done = self.state.analysis_completed is not None

    @kernel_function(
        name="get_all_repos",
        description="""Get comprehensive inventory of all repositories with basic metadata.
        
        On first call, automatically performs lightweight analysis of all repositories 
        including language detection, framework identification, and file statistics.
        Subsequent calls return cached results instantly.
        
        Returns structured data with:
        - Repository names and paths
        - Primary programming languages with confidence scores
        - Detected frameworks and technologies
        - File counts and estimated lines of code
        - Repository type classification
        - Analysis status and component assignments
        
        This provides the essential metadata the discovery agent needs to get started
        with repository categorization and component planning.
        
        Example usage:
        - get_all_repos() → Analyzes all 92 repos and returns metadata
        - Subsequent calls return cached data for fast access""",
    )
    async def get_all_repos(self) -> Dict[str, Any]:
        """Get all repositories with basic metadata, performing analysis if needed."""
        
        try:
            # Check if we need to perform initial analysis
            if not self._initial_analysis_done:
                return await self._perform_initial_analysis()
            
            # Return cached results
            repos_data = {}
            for repo_name, repo_metadata in self.state.repositories.items():
                # Format file extensions (top 10 + others)
                file_extensions = self._format_file_extensions(repo_metadata.file_counts)
                
                repos_data[repo_name] = {
                    'name': repo_name,
                    'path': repo_metadata.path,
                    'file_extensions': file_extensions,
                    'frameworks': repo_metadata.technology_stack.frameworks,
                    'total_files': repo_metadata.total_files,
                    'total_lines': repo_metadata.total_lines,
                    'has_readme': repo_metadata.has_readme,
                    'assigned_components': repo_metadata.assigned_components
                }
            
            progress = self.state.get_progress_summary()
            
            return PluginResponse(
                success=True,
                data=repos_data,
                suggestions=[
                    "Use get_unanalyzed_repos() to find repositories needing detailed analysis",
                    "Explore high-value repositories first (large codebases, core frameworks)",
                    "Store insights with store_repo_insights() after investigating each repository",
                    "Group related repositories into logical components with add_component()"
                ],
                metadata=progress
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to get repository inventory: {str(e)}",
                suggestions=[
                    f"Check that repos path exists: {self.repos_path}",
                    "Ensure repositories directory is accessible",
                    "Try clearing cache and running again"
                ]
            ).model_dump()

    @kernel_function(
        name="get_unanalyzed_repos",
        description="""Get repositories that need deeper exploration and analysis.
        
        Returns repositories that have only basic automated analysis but lack
        detailed insights from agent exploration. These are candidates for 
        deeper investigation using filesystem tools.
        
        Focuses agent attention on repos that need manual exploration to
        understand their true purpose, architecture, and component assignment.
        
        Returns:
        - Repository names and basic metadata
        - Analysis status and confidence scores
        - Suggestions for investigation approaches
        
        Use this to systematically work through repositories that need
        detailed analysis before component assignment.""",
    )
    async def get_unanalyzed_repos(self) -> Dict[str, Any]:
        """Get repositories that need deeper analysis."""
        
        try:
            unanalyzed = {}
            
            for repo_name, repo_metadata in self.state.repositories.items():
                # Consider repos that are only auto-analyzed or have low confidence
                needs_analysis = (
                    repo_metadata.analysis_status == AnalysisStatus.ANALYZED or
                    repo_metadata.analysis_confidence < 0.8 or
                    not repo_metadata.insights or
                    not repo_metadata.assigned_components
                )
                
                if needs_analysis:
                    # Format file extensions (top 10 + others)
                    file_extensions = self._format_file_extensions(repo_metadata.file_counts)
                    
                    unanalyzed[repo_name] = {
                        'name': repo_name,
                        'path': repo_metadata.path,
                        'file_extensions': file_extensions,
                        'frameworks': repo_metadata.technology_stack.frameworks,
                        'total_files': repo_metadata.total_files,
                        'total_lines': repo_metadata.total_lines,
                        'has_readme': repo_metadata.has_readme,
                        'has_insights': bool(repo_metadata.insights),
                        'assigned_components': repo_metadata.assigned_components,
                        'suggested_investigation': self._get_investigation_suggestions(repo_metadata)
                    }
            
            suggestions = []
            if unanalyzed:
                # Prioritize suggestions based on repository characteristics
                high_priority = [repo for repo in unanalyzed.values() if repo['total_lines'] > 5000 or repo['frameworks']]
                suggestions.extend([
                    f"{len(unanalyzed)} repositories need investigation",
                    f"Start with {len(high_priority)} high-priority repositories (large or with frameworks)",
                    "Examine README, main entry points, and configuration files",
                    "Store findings with store_repo_insights() for each repository investigated"
                ])
            else:
                suggestions.extend([
                    "All repositories investigated - ready for component creation",
                    "Create logical components with add_component()",
                    "Review component assignments with get_components_summary()"
                ])
            
            return PluginResponse(
                success=True,
                data=unanalyzed,
                suggestions=suggestions,
                metadata={
                    'unanalyzed_count': len(unanalyzed),
                    'total_repos': len(self.state.repositories),
                    'analysis_progress': (len(self.state.repositories) - len(unanalyzed)) / len(self.state.repositories) * 100 if self.state.repositories else 0
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to get unanalyzed repositories: {str(e)}",
                suggestions=[
                    "Check if initial repository analysis has been completed",
                    "Try running get_all_repos() first to ensure repositories are loaded"
                ]
            ).model_dump()

    @kernel_function(
        name="store_repo_insights",
        description="""Store detailed insights about a repository from agent exploration.
        
        Use this function to store your detailed findings after exploring a repository
        with filesystem tools. This enhances the basic automated analysis with your
        understanding of what the repository actually does.
        
        Store insights about:
        - Repository purpose and business function
        - Architecture patterns and design
        - Key technologies and dependencies  
        - Integration points with other systems
        - Migration complexity assessment
        - Component assignment rationale
        
        Parameters:
        - repo_name: Name of the repository
        - insights: Dictionary with your detailed findings
        
        Example insights structure:
        {
            "purpose": "Customer order processing microservice",
            "business_function": "E-commerce order management", 
            "architecture": "REST API with PostgreSQL database",
            "key_dependencies": ["payment-service", "inventory-service"],
            "migration_complexity": "medium",
            "notes": "Well-documented, standard Spring Boot structure"
        }""",
    )
    async def store_repo_insights(
        self,
        repo_name: Annotated[str, "Name of the repository to store insights for"],
        insights: Annotated[Dict[str, Any], "Dictionary containing detailed insights about the repository"]
    ) -> Dict[str, Any]:
        """Store detailed insights about a repository."""
        
        try:
            if repo_name not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Repository '{repo_name}' not found in analysis state",
                    suggestions=[
                        "Use get_all_repos() to see available repositories",
                        "Check repository name spelling",
                        "Ensure initial analysis has been completed"
                    ]
                ).model_dump()
            
            # Update repository with insights
            repo_metadata = self.state.repositories[repo_name]
            repo_metadata.insights.update(insights)
            repo_metadata.analysis_status = AnalysisStatus.DETAILED
            
            # Update progress counters
            self.state.detailed_repositories = len([
                repo for repo in self.state.repositories.values() 
                if repo.analysis_status == AnalysisStatus.DETAILED
            ])
            
            # Store updated metadata
            self.storage.update_repository(repo_name, repo_metadata)
            self.storage.save_state(self.state)
            
            return PluginResponse(
                success=True,
                data={
                    'repo_name': repo_name,
                    'insights_stored': len(insights),
                    'total_insights': len(repo_metadata.insights),
                    'analysis_status': repo_metadata.analysis_status.value
                },
                suggestions=[
                    f"Successfully stored insights for {repo_name}",
                    "Continue analyzing other repositories with get_unanalyzed_repos()",
                    "Consider component assignment once you understand repository patterns",
                    "Use add_component() to create logical groupings"
                ],
                metadata={
                    'insights_keys': list(insights.keys()),
                    'repository_path': repo_metadata.path
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to store insights for {repo_name}: {str(e)}",
                suggestions=[
                    "Ensure insights is a valid dictionary",
                    "Check that repository name exists",
                    "Try again with simpler insights structure"
                ]
            ).model_dump()

    @kernel_function(
        name="add_component",
        description="""Create a new logical component for grouping repositories.
        
        Creates a logical component that represents a cohesive part of the system
        for migration planning. Components should group repositories based on:
        - Business function (e.g., "Customer Management", "Order Processing")
        - Technology stack (e.g., "Java Microservices", "Python Analytics")
        - Architectural layer (e.g., "API Gateway", "Data Layer")
        
        Component sizing guidelines:
        - Appropriate: 3-15 repositories with related functionality
        - Too large: 30+ repositories or mixed technology stacks
        - Too small: Single repository (unless major standalone system)
        
        Parameters:
        - name: Descriptive component name
        - purpose: Clear description of component purpose  
        - rationale: Explanation of why these repos belong together
        
        Example:
        add_component(
            "customer-services",
            "Customer management and profile services",
            "Groups all microservices handling customer data and operations"
        )""",
    )
    async def add_component(
        self,
        name: Annotated[str, "Component name (use kebab-case, e.g., 'customer-services')"],
        purpose: Annotated[str, "Clear description of what this component does"],
        rationale: Annotated[str, "Explanation of why repositories belong in this component"]
    ) -> Dict[str, Any]:
        """Create a new logical component."""
        
        try:
            # Validate component name
            if not name or not name.replace('-', '').replace('_', '').isalnum():
                return PluginResponse(
                    success=False,
                    error="Component name must be alphanumeric with hyphens/underscores only",
                    suggestions=[
                        "Use kebab-case naming (e.g., 'customer-services')",
                        "Example names: 'api-gateway', 'data-processing', 'user-management'"
                    ]
                ).model_dump()
            
            # Check if component already exists
            if name in self.state.components:
                return PluginResponse(
                    success=False,
                    error=f"Component '{name}' already exists",
                    suggestions=[
                        "Use a different component name",
                        "Or assign repositories to existing component with assign_repo_to_component()",
                        "Use get_components_summary() to see existing components"
                    ]
                ).model_dump()
            
            # Create component
            component_data = ComponentData(
                name=name,
                purpose=purpose,
                rationale=rationale,
                created_at=datetime.now()
            )
            
            # Store component
            self.storage.add_component(name, component_data)
            self.storage.save_state(self.state)
            
            return PluginResponse(
                success=True,
                data={
                    'component_name': name,
                    'purpose': purpose,
                    'rationale': rationale,
                    'created_at': component_data.created_at.isoformat(),
                    'repositories': []
                },
                suggestions=[
                    f"Successfully created component '{name}'",
                    "Now assign repositories with assign_repo_to_component()",
                    "Use get_all_repos() to see available repositories for assignment",
                    "Aim for 3-15 repositories per component for optimal migration planning"
                ],
                metadata={
                    'total_components': len(self.state.components) + 1
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to create component: {str(e)}",
                suggestions=[
                    "Check that name, purpose, and rationale are provided",
                    "Use descriptive but concise component names",
                    "Try again with simpler parameters"
                ]
            ).model_dump()

    @kernel_function(
        name="assign_repo_to_component",
        description="""Assign a repository to a logical component.
        
        Links a repository to a component for migration planning. Each repository
        should be assigned to at least one component. Some repositories may belong
        to multiple components if they serve multiple purposes.
        
        Before assignment, ensure you understand:
        - Repository's true purpose (use filesystem tools to investigate)
        - How it fits with other repositories in the component
        - Technology compatibility with component's other repos
        
        Parameters:
        - repo_name: Name of repository to assign
        - component_name: Name of target component
        
        The assignment is bidirectional - updates both the repository's
        component list and the component's repository list.""",
    )
    async def assign_repo_to_component(
        self,
        repo_name: Annotated[str, "Name of the repository to assign"],
        component_name: Annotated[str, "Name of the component to assign to"]
    ) -> Dict[str, Any]:
        """Assign a repository to a component."""
        
        try:
            # Validate repository exists
            if repo_name not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Repository '{repo_name}' not found",
                    suggestions=[
                        "Use get_all_repos() to see available repositories",
                        "Check repository name spelling",
                        "Ensure repository has been analyzed"
                    ]
                ).model_dump()
            
            # Validate component exists
            if component_name not in self.state.components:
                return PluginResponse(
                    success=False,
                    error=f"Component '{component_name}' not found",
                    suggestions=[
                        "Create component first with add_component()",
                        "Use get_components_summary() to see existing components",
                        "Check component name spelling"
                    ]
                ).model_dump()
            
            # Check if already assigned
            repo_metadata = self.state.repositories[repo_name]
            if component_name in repo_metadata.assigned_components:
                return PluginResponse(
                    success=False,
                    error=f"Repository '{repo_name}' is already assigned to component '{component_name}'",
                    suggestions=[
                        "Repository is already assigned to this component",
                        "Use get_components_summary() to see current assignments",
                        "Assign to a different component if needed"
                    ]
                ).model_dump()
            
            # Perform assignment
            self.storage.assign_repo_to_component(repo_name, component_name)
            self.storage.save_state(self.state)
            
            # Get updated data
            component_data = self.state.components[component_name]
            repo_count = len(component_data.repositories)
            
            # Validate component size
            validation = ValidationHelper.validate_component_size(component_data, repo_count)
            
            suggestions = [f"Successfully assigned '{repo_name}' to component '{component_name}'"]
            if validation['warnings']:
                suggestions.extend([f"Warning: {warning}" for warning in validation['warnings']])
            if validation['suggestions']:
                suggestions.extend(validation['suggestions'])
            
            return PluginResponse(
                success=True,
                data={
                    'repo_name': repo_name,
                    'component_name': component_name,
                    'component_repository_count': repo_count,
                    'repository_components': self.state.repositories[repo_name].assigned_components
                },
                suggestions=suggestions,
                metadata={
                    'validation': validation,
                    'assignment_coverage': self._calculate_assignment_coverage()
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to assign repository: {str(e)}",
                suggestions=[
                    f"Check that both '{repo_name}' and '{component_name}' exist",
                    "Use get_all_repos() and get_components_summary() to verify names",
                    "Try again with correct names"
                ]
            ).model_dump()

    @kernel_function(
        name="get_components_summary",
        description="""Get comprehensive summary of all logical components and assignments.
        
        Returns complete overview of component structure including:
        - All created components with purposes and rationale
        - Repository assignments for each component
        - Component size validation and warnings
        - Assignment coverage statistics
        - Unassigned repositories that need component assignment
        
        Use this to:
        - Validate that all repositories are assigned to components
        - Review component sizes for migration planning
        - Identify components that may need restructuring
        - Get progress toward complete component assignment
        
        Essential for ensuring comprehensive coverage before generating
        the final discovery report.""",
    )
    async def get_components_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all components and assignments."""
        
        try:
            components_data = {}
            
            for comp_name, comp_data in self.state.components.items():
                repo_count = len(comp_data.repositories)
                validation = ValidationHelper.validate_component_size(comp_data, repo_count)
                
                # Get technology summary for component
                tech_summary = self._get_component_tech_summary(comp_data.repositories)
                
                components_data[comp_name] = {
                    'name': comp_name,
                    'purpose': comp_data.purpose,
                    'rationale': comp_data.rationale,
                    'repository_count': repo_count,
                    'repositories': comp_data.repositories,
                    'created_at': comp_data.created_at.isoformat(),
                    'size_category': validation['size_category'],
                    'validation': validation,
                    'technology_summary': tech_summary
                }
            
            # Get assignment validation
            validation_results = ValidationHelper.validate_repo_assignments(self.state)
            
            return PluginResponse(
                success=True,
                data={
                    'components': components_data,
                    'validation_results': validation_results
                },
                suggestions=self._get_component_suggestions(components_data, validation_results),
                metadata={
                    'total_components': len(components_data),
                    'total_repositories': len(self.state.repositories),
                    'assignment_coverage': validation_results['assignment_coverage'],
                    'unassigned_count': len(validation_results['unassigned_repos'])
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to get components summary: {str(e)}",
                suggestions=[
                    "Ensure components have been created with add_component()",
                    "Check that repositories have been assigned to components",
                    "Try running get_all_repos() first to load repository data"
                ]
            ).model_dump()

    @kernel_function(
        name="generate_discovery_report",
        description="""Generate comprehensive discovery report in markdown format.
        
        Creates a complete discovery report suitable for stakeholders and next-phase
        migration planning teams. The report includes:
        
        - Executive summary with key metrics and progress
        - Repository inventory organized by analysis status
        - Logical component analysis with validation
        - Technology stack summary across all repositories
        - Assignment validation and coverage statistics  
        - Actionable recommendations for next steps
        
        This report represents the final deliverable of the discovery phase,
        providing structured handoff to detailed migration planning teams.
        
        Should only be run after:
        1. All repositories have been analyzed
        2. Logical components have been created
        3. Repository assignments are complete
        4. Component validation passes
        
        Returns markdown-formatted report ready for documentation.""",
    )
    async def generate_discovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive discovery report."""
        
        try:
            # Generate the report
            report_content = ReportGenerator.generate_discovery_report(self.state)
            
            # Get summary statistics
            progress = self.state.get_progress_summary()
            validation_results = ValidationHelper.validate_repo_assignments(self.state)
            
            # Check if ready for report generation
            readiness_issues = []
            if progress['analysis_progress'] < 90:
                readiness_issues.append(f"Only {progress['analysis_progress']:.1f}% of repositories analyzed")
            if validation_results['assignment_coverage'] < 90:
                readiness_issues.append(f"Only {validation_results['assignment_coverage']:.1f}% of repositories assigned to components")
            if not self.state.components:
                readiness_issues.append("No logical components have been created")
            
            suggestions = []
            if readiness_issues:
                suggestions.extend([
                    "Report generated but discovery may be incomplete:",
                    *[f"- {issue}" for issue in readiness_issues],
                    "",
                    "Consider completing analysis before final report generation"
                ])
            else:
                suggestions.extend([
                    "Discovery analysis complete! Report generated successfully.",
                    "Ready for handoff to detailed migration planning teams.",
                    "All repositories analyzed and assigned to logical components."
                ])
            
            return PluginResponse(
                success=True,
                data={
                    'report': report_content,
                    'word_count': len(report_content.split()),
                    'line_count': len(report_content.split('\n')),
                    'generated_at': datetime.now().isoformat()
                },
                suggestions=suggestions,
                metadata={
                    'progress_summary': progress,
                    'validation_results': validation_results,
                    'readiness_issues': readiness_issues,
                    'report_sections': [
                        'Executive Summary',
                        'Repository Inventory', 
                        'Logical Components Analysis',
                        'Technology Stack Summary',
                        'Assignment Validation',
                        'Recommendations'
                    ]
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to generate discovery report: {str(e)}",
                suggestions=[
                    "Ensure repositories have been analyzed with get_all_repos()",
                    "Create components with add_component() before generating report",
                    "Assign repositories to components with assign_repo_to_component()",
                    "Check that analysis state is valid and complete"
                ]
            ).model_dump()

    async def _perform_initial_analysis(self) -> Dict[str, Any]:
        """Perform initial automated analysis of all repositories."""
        
        # Find all repositories
        repo_paths = find_repositories(self.repos_path)
        
        if not repo_paths:
            return PluginResponse(
                success=False,
                error=f"No repositories found in {self.repos_path}",
                suggestions=[
                    f"Ensure repositories exist in {self.repos_path}",
                    "Check that repos_path is correct",
                    "Repositories should be subdirectories with code files"
                ]
            ).model_dump()
        
        self.state.analysis_started = datetime.now()
        self.state.total_repositories = len(repo_paths)
        
        # Progress tracking
        analysis_results = {}
        
        def progress_callback(current: int, total: int, repo_name: str):
            print(f"[{current}/{total}] ({current/total*100:.1f}%) Analyzing: {repo_name}")
        
        try:
            # Perform parallel analysis
            analysis_results = self.parallel_processor.process_repositories(
                repo_paths,
                self.analyzer.analyze_repository,
                progress_callback
            )
            
            # Store results in state
            with self.storage.batch_update():
                for repo_name, metadata in analysis_results.items():
                    self.state.repositories[repo_name] = metadata
                    self.storage.update_repository(repo_name, metadata)
            
            # Update analysis progress counters
            self.state.analyzed_repositories = len([
                repo for repo in self.state.repositories.values() 
                if repo.analysis_status in [AnalysisStatus.ANALYZED, AnalysisStatus.DETAILED]
            ])
            self.state.detailed_repositories = len([
                repo for repo in self.state.repositories.values() 
                if repo.analysis_status == AnalysisStatus.DETAILED
            ])
            
            # Mark analysis as complete
            self.state.analysis_completed = datetime.now()
            self._initial_analysis_done = True
            
            # Save state
            self.storage.save_state(self.state)
            
            # Return results
            repos_data = {}
            for repo_name, repo_metadata in analysis_results.items():
                # Format file extensions (top 10 + others)
                file_extensions = self._format_file_extensions(repo_metadata.file_counts)
                
                repos_data[repo_name] = {
                    'name': repo_name,
                    'path': repo_metadata.path,
                    'file_extensions': file_extensions,
                    'frameworks': repo_metadata.technology_stack.frameworks,
                    'total_files': repo_metadata.total_files,
                    'total_lines': repo_metadata.total_lines,
                    'has_readme': repo_metadata.has_readme,
                    'assigned_components': repo_metadata.assigned_components
                }
            
            progress = self.state.get_progress_summary()
            
            return PluginResponse(
                success=True,
                data=repos_data,
                suggestions=[
                    "Repository analysis complete - proceed to detailed investigation",
                    "Use get_unanalyzed_repos() to find repositories needing investigation",
                    "Prioritize repositories with complex frameworks or large codebases",
                    "Store findings with store_repo_insights() after exploring each repository"
                ],
                metadata=progress
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed during initial analysis: {str(e)}",
                suggestions=[
                    "Check repository permissions and accessibility",
                    "Ensure sufficient disk space for analysis cache",
                    "Try reducing parallel processing if system resources are limited"
                ]
            ).model_dump()

    def _get_investigation_suggestions(self, repo_metadata: RepoMetadata) -> List[str]:
        """Get investigation suggestions for a repository."""
        suggestions = []
        
        if not repo_metadata.has_readme:
            suggestions.append("Read any documentation files to understand purpose")
        else:
            suggestions.append("Read README.md to understand stated purpose")
        
        if repo_metadata.config_files:
            suggestions.append(f"Examine config files: {', '.join(repo_metadata.config_files[:3])}")
        
        if repo_metadata.technology_stack.primary_languages:
            primary_lang = repo_metadata.technology_stack.primary_languages[0][0]
            if primary_lang == "Python":
                suggestions.append("Look for main.py, app.py, or manage.py entry points")
            elif primary_lang == "JavaScript":
                suggestions.append("Check package.json and look for index.js or server.js")
            elif primary_lang == "Java":
                suggestions.append("Find Main.java or Application.java entry points")
        
        if repo_metadata.repository_type.value == "unknown":
            suggestions.append("Explore directory structure to understand architecture")
        
        return suggestions
    
    def _calculate_assignment_coverage(self) -> float:
        """Calculate percentage of repositories assigned to components."""
        if not self.state.repositories:
            return 0.0
        
        assigned_count = sum(1 for repo in self.state.repositories.values() 
                           if repo.assigned_components)
        return assigned_count / len(self.state.repositories) * 100
    
    def _get_component_tech_summary(self, repo_names: List[str]) -> Dict[str, Any]:
        """Get technology summary for component repositories."""
        languages = {}
        frameworks = set()
        
        for repo_name in repo_names:
            if repo_name in self.state.repositories:
                repo = self.state.repositories[repo_name]
                
                # Count languages
                for lang, _ in repo.technology_stack.primary_languages:
                    languages[lang] = languages.get(lang, 0) + 1
                
                # Collect frameworks
                frameworks.update(repo.technology_stack.frameworks)
        
        return {
            'primary_languages': dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)),
            'frameworks': sorted(list(frameworks)),
            'language_diversity': len(languages),
            'framework_count': len(frameworks)
        }
    
    def _get_component_suggestions(self, components_data: Dict, validation_results: Dict) -> List[str]:
        """Get suggestions based on component analysis."""
        suggestions = []
        
        if not components_data:
            suggestions.extend([
                "No components created yet",
                "Use add_component() to create logical groupings for repositories",
                "Start with clear business functions or technology stacks"
            ])
            return suggestions
        
        if validation_results['unassigned_repos']:
            suggestions.append(f"Assign {len(validation_results['unassigned_repos'])} unassigned repositories to components")
        
        # Check for problematic component sizes
        large_components = [name for name, data in components_data.items() 
                          if data['validation']['size_category'] == 'too_large']
        small_components = [name for name, data in components_data.items() 
                          if data['validation']['size_category'] == 'too_small']
        
        if large_components:
            suggestions.append(f"Consider splitting large components: {', '.join(large_components)}")
        
        if small_components:
            suggestions.append(f"Review small components for potential merging: {', '.join(small_components)}")
        
        if validation_results['assignment_coverage'] >= 95:
            suggestions.extend([
                "Excellent! Nearly all repositories assigned to components",
                "Ready to generate final discovery report with generate_discovery_report()"
            ])
        
        return suggestions
    
    def _format_file_extensions(self, file_counts: Dict[str, int]) -> Dict[str, int]:
        """Format file extensions showing top 10 + others."""
        if not file_counts:
            return {}
        
        # Sort by count descending
        sorted_extensions = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 10
        top_10 = dict(sorted_extensions[:10])
        
        # Sum the rest as 'others'
        others_count = sum(count for _, count in sorted_extensions[10:])
        if others_count > 0:
            top_10['others'] = others_count
        
        return top_10