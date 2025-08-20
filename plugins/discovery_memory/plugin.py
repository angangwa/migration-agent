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
    PluginResponse, RepoMetadata, ComponentData, AnalysisState, 
    DependencyRecord, DeepAnalysis
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
        
        # Initialize runtime dependency cache (not persisted)
        self._dependency_cache = {}

    @kernel_function(
        name="get_all_repos",
        description="""Get comprehensive inventory of all repositories with basic metadata.
        
        On first call, automatically performs lightweight analysis of all repositories 
        including framework detection, file statistics, and line counting.
        Subsequent calls return cached results instantly.
        
        Returns structured data with:
        - Repository names and paths
        - File extension breakdown (top 10 + others)
        - Detected frameworks and technologies
        - Total files and exact line counts
        - README presence and component assignments
        
        Provides essential metadata for repository categorization and component planning.
        
        Example usage:
        - get_all_repos() → Analyzes all repositories and returns metadata
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
                    'assigned_components': repo_metadata.assigned_components,
                    'discovery_status': repo_metadata.discovery_phase_status
                }
            
            progress = self.state.get_progress_summary()
            
            return PluginResponse(
                success=True,
                data=repos_data,
                suggestions=[
                    "Use get_unanalyzed_repos() to find repositories needing investigation or assignment",
                    "Investigate repositories using filesystem tools to understand their purpose",
                    "Store insights with store_repo_insights() after investigating each repository",
                    "Create logical components with add_component() and assign repositories to them"
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
        description="""Get repositories that need investigation or component assignment.
        
        Returns repositories that either:
        1. Need investigation: No insights have been added by agents yet
        2. Need assignment: Have insights but are not assigned to any components
        
        Use this to systematically work through repositories to complete
        the discovery process. Investigation involves using filesystem tools
        to understand repository purpose, then storing insights.
        
        Returns:
        - Repository names and basic metadata  
        - Current discovery phase status
        - Suggestions for next steps
        
        Essential for ensuring all repositories are fully analyzed and assigned.""",
    )
    async def get_unanalyzed_repos(self) -> Dict[str, Any]:
        """Get repositories that need investigation or component assignment."""
        
        try:
            unanalyzed = {}
            
            for repo_name, repo_metadata in self.state.repositories.items():
                # Consider repos that need investigation or assignment
                needs_analysis = (
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
                        'discovery_status': repo_metadata.discovery_phase_status,
                        'suggested_investigation': self._get_investigation_suggestions(repo_metadata)
                    }
            
            suggestions = []
            if unanalyzed:
                needs_insights = [repo for repo in unanalyzed.values() if "No insights" in repo['discovery_status']]
                needs_assignment = [repo for repo in unanalyzed.values() if "Insights added. Assigned to no components" in repo['discovery_status']]
                
                suggestions.extend([
                    f"{len(unanalyzed)} repositories need attention",
                    f"{len(needs_insights)} repositories need investigation (use filesystem tools)",
                    f"{len(needs_assignment)} repositories need component assignment",
                    "Store findings with store_repo_insights() after investigating each repository",
                    "Assign repositories to components with assign_repo_to_component()"
                ])
            else:
                suggestions.extend([
                    "All repositories have insights and are assigned to components",
                    "Discovery phase complete - ready to generate final report",
                    "Use generate_discovery_report() to create comprehensive report"
                ])
            
            return PluginResponse(
                success=True,
                data=unanalyzed,
                suggestions=suggestions,
                metadata={
                    'repositories_needing_attention': len(unanalyzed),
                    'total_repos': len(self.state.repositories),
                    'discovery_completion': (len(self.state.repositories) - len(unanalyzed)) / len(self.state.repositories) * 100 if self.state.repositories else 0
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to get unanalyzed repositories: {str(e)}",
                suggestions=[
                    "Check if repositories have been loaded with get_all_repos()",
                    "Ensure repository discovery has been initiated"
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
            repo_metadata.update_discovery_status()
            
            # Update progress counters
            self.state.repositories_with_insights = len([
                repo for repo in self.state.repositories.values() 
                if repo.insights
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
                    'discovery_status': repo_metadata.discovery_phase_status
                },
                suggestions=[
                    f"Successfully stored insights for {repo_name}",
                    "Repository discovery status updated automatically",
                    "Continue with other repositories using get_unanalyzed_repos()",
                    "Assign repository to components when ready with assign_repo_to_component()"
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
            if progress['investigation_progress'] < 90:
                readiness_issues.append(f"Only {progress['investigation_progress']:.1f}% of repositories have insights")
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
                    "Discovery phase complete! Report generated successfully.",
                    "Ready for handoff to migration planning teams.",
                    "All repositories have insights and are assigned to logical components."
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
                    "Ensure repositories have been loaded with get_all_repos()",
                    "Add insights to repositories with store_repo_insights()",
                    "Create components with add_component() before generating report",
                    "Assign repositories to components with assign_repo_to_component()"
                ]
            ).model_dump()

    # === Phase 2 Kernel Functions ===

    @kernel_function(
        name="store_repository_deep_analysis",
        description="""Store comprehensive Phase 2 deep analysis for a repository.
        
        Stores your detailed findings from deep dive analysis:
        - markdown_summary (required): Well-formatted markdown report
        - deep_insights (optional): Custom key-value insights
        
        For dependencies, use the dedicated add_repository_dependency() function.
        Validates that repo_name exists in the system.
        
        Parameters:
        - repo_name: Name of the repository (must exist)
        - markdown_summary: Comprehensive markdown report
        - deep_insights: Custom key-value pairs for additional insights
        
        Example:
        store_repository_deep_analysis(
            repo_name="customer-api",
            markdown_summary="# Customer API Analysis\\n## Overview\\n...",
            deep_insights={
                "api_style": "RESTful with OpenAPI 3.0",
                "database": "PostgreSQL with Prisma ORM",
                "deployment": "Kubernetes with Helm charts",
                "test_coverage": "85%",
                "migration_effort_days": 15
            }
        )""",
    )
    async def store_repository_deep_analysis(
        self,
        repo_name: Annotated[str, "Repository name"],
        markdown_summary: Annotated[str, "Comprehensive markdown analysis report"],
        deep_insights: Annotated[Dict[str, Any], "Custom key-value insights"] = None
    ) -> Dict[str, Any]:
        """Store comprehensive Phase 2 analysis with validation."""
        
        try:
            # Validate repo exists
            if repo_name not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Repository '{repo_name}' not found. Use get_all_repos() to see valid repositories.",
                    suggestions=[
                        "Check repository name spelling",
                        "Run get_all_repos() to see available repositories",
                        "Ensure repository has been discovered in Phase 1"
                    ]
                ).model_dump()
            
            # Create deep analysis object
            if deep_insights is None:
                deep_insights = {}
            
            deep_analysis = DeepAnalysis(
                markdown_summary=markdown_summary,
                deep_insights=deep_insights,
                analysis_timestamp=datetime.now()
            )
            
            # Store in repository metadata
            repo = self.state.repositories[repo_name]
            repo.deep_analysis = deep_analysis
            
            # Save state
            self.storage.save_state(self.state)
            
            return PluginResponse(
                success=True,
                data={
                    "repository": repo_name,
                    "markdown_length": len(markdown_summary),
                    "insights_count": len(deep_insights),
                    "analysis_timestamp": deep_analysis.analysis_timestamp.isoformat()
                },
                suggestions=[
                    "Deep analysis stored successfully",
                    "Use add_repository_dependency() to track dependencies to other repositories",
                    "Use get_repository_details() to see complete repository information"
                ],
                metadata={
                    "phase": "2",
                    "operation": "store_deep_analysis",
                    "has_previous_analysis": repo.deep_analysis is not None
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to store deep analysis: {str(e)}",
                suggestions=[
                    "Ensure markdown_summary is a valid string",
                    "Check deep_insights is a valid dictionary",
                    "Verify repository name exists"
                ]
            ).model_dump()

    @kernel_function(
        name="add_repository_dependency",
        description="""Add a specific dependency between repositories.
        
        Documents a discovered dependency with validation that both repos exist.
        Updates both source (outgoing) and target (incoming) dependency lists.
        
        Parameters:
        - source_repo: Repository that has the dependency (must exist)
        - target_repo: Repository being depended upon (must exist)  
        - dependency_type: Descriptive type (e.g. code/api/database/config/build/runtime or custom)
        - description: Clear description of the dependency
        - evidence: List of file paths or code snippets as proof
        
        Example:
        add_repository_dependency(
            source_repo="frontend-app",
            target_repo="customer-api",
            dependency_type="api",
            description="Calls customer endpoints for user profile data",
            evidence=["src/services/customer.js:45-67"]
        )""",
    )
    async def add_repository_dependency(
        self,
        source_repo: Annotated[str, "Repository with the dependency"],
        target_repo: Annotated[str, "Repository being depended upon"],
        dependency_type: Annotated[str, "Descriptive dependency type (flexible, e.g. api, database, shared-library)"],
        description: Annotated[str, "Clear description of the dependency"],
        evidence: Annotated[List[str], "File paths or code snippets as evidence"] = None
    ) -> Dict[str, Any]:
        """Add dependency with bidirectional updates and validation."""
        
        try:
            # Validate both repos exist
            if source_repo not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Source repository '{source_repo}' not found.",
                    suggestions=[
                        "Check source repository name spelling",
                        "Run get_all_repos() to see available repositories"
                    ]
                ).model_dump()
            
            if target_repo not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Target repository '{target_repo}' not found.",
                    suggestions=[
                        "Check target repository name spelling", 
                        "Run get_all_repos() to see available repositories"
                    ]
                ).model_dump()
            
            # Validate dependency type (flexible validation - allow any non-empty string)
            if not dependency_type or not isinstance(dependency_type, str):
                return PluginResponse(
                    success=False,
                    error="Dependency type must be a non-empty string",
                    suggestions=[
                        "Common dependency types: code, api, database, config, build, runtime",
                        "Use descriptive types that help understand the relationship",
                        "Examples: 'shared-library', 'message-queue', 'authentication-service'"
                    ]
                ).model_dump()
            
            # Clean up the dependency type
            dependency_type = dependency_type.strip().lower()
            
            if evidence is None:
                evidence = []
            
            # Check for duplicate dependency
            for existing in self.state.dependency_records:
                if (existing.source_repo == source_repo and 
                    existing.target_repo == target_repo and 
                    existing.dependency_type == dependency_type):
                    return PluginResponse(
                        success=False,
                        error=f"Dependency already exists: {source_repo} -> {target_repo} ({dependency_type})",
                        suggestions=[
                            "Dependency is already recorded",
                            "Use get_dependency_graph() to see all dependencies",
                            "Consider updating the existing dependency if needed"
                        ]
                    ).model_dump()
            
            # Create dependency record
            dependency = DependencyRecord(
                source_repo=source_repo,
                target_repo=target_repo,
                dependency_type=dependency_type,
                description=description,
                evidence=evidence,
                created_at=datetime.now()
            )
            
            # Add to dependency records
            self.state.dependency_records.append(dependency)
            
            # Clear cache to force rebuild
            self._clear_dependency_cache()
            
            # Save state
            self.storage.save_state(self.state)
            
            return PluginResponse(
                success=True,
                data={
                    "source_repo": source_repo,
                    "target_repo": target_repo,
                    "dependency_type": dependency_type,
                    "evidence_count": len(evidence),
                    "created_at": dependency.created_at.isoformat()
                },
                suggestions=[
                    f"Dependency recorded: {source_repo} -> {target_repo}",
                    "Use get_dependency_graph() to visualize all dependencies",
                    "Use get_repository_details() to see repository dependencies"
                ],
                metadata={
                    "phase": "2",
                    "operation": "add_dependency",
                    "total_dependencies": len(self.state.dependency_records)
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to add dependency: {str(e)}",
                suggestions=[
                    "Verify both repository names exist",
                    "Check dependency type is valid",
                    "Ensure description is provided"
                ]
            ).model_dump()

    @kernel_function(
        name="get_repository_details",
        description="""Get complete repository details from both Phase 1 and Phase 2.
        
        Unified function that returns:
        - Basic metadata (Phase 1): file counts, frameworks, lines of code
        - Insights (Phase 1): Purpose, business function, architecture notes
        - Deep analysis (Phase 2): Markdown summary, dependencies, deep insights
        - Component assignments
        
        Works for repositories at any stage of analysis.
        
        Parameters:
        - repo_name: Repository to retrieve details for
        - include_dependencies: Include dependency analysis (default: True)
        
        Returns all available data for the repository.""",
    )
    async def get_repository_details(
        self,
        repo_name: Annotated[str, "Repository name"],
        include_dependencies: Annotated[bool, "Include dependency analysis"] = True
    ) -> Dict[str, Any]:
        """Get unified repository details from all phases."""
        
        try:
            if repo_name not in self.state.repositories:
                return PluginResponse(
                    success=False,
                    error=f"Repository '{repo_name}' not found.",
                    suggestions=[
                        "Check repository name spelling",
                        "Run get_all_repos() to see available repositories"
                    ]
                ).model_dump()
            
            repo = self.state.repositories[repo_name]
            
            # Build comprehensive details
            details = {
                # Phase 1 basic metadata
                "name": repo.name,
                "path": repo.path,
                "file_extensions": self._format_file_extensions(repo.file_counts),
                "frameworks": repo.technology_stack.frameworks,
                "total_files": repo.total_files,
                "total_lines": repo.total_lines,
                "has_readme": repo.has_readme,
                "config_files": repo.config_files,
                
                # Phase 1 insights
                "insights": repo.insights,
                "assigned_components": repo.assigned_components,
                "discovery_status": repo.discovery_phase_status,
                
                # Phase 2 deep analysis (if available)
                "has_deep_analysis": repo.deep_analysis is not None,
                "markdown_summary": repo.deep_analysis.markdown_summary if repo.deep_analysis else None,
                "deep_insights": repo.deep_analysis.deep_insights if repo.deep_analysis else {},
                "analysis_timestamp": (
                    repo.deep_analysis.analysis_timestamp.isoformat() 
                    if repo.deep_analysis else None
                ),
                
                # Dependencies (computed from centralized records)
                "dependencies": None
            }
            
            if include_dependencies:
                outgoing = self._get_outgoing_dependencies(repo_name)
                incoming = self._get_incoming_dependencies(repo_name)
                
                details["dependencies"] = {
                    "outgoing": outgoing,
                    "incoming": incoming,
                    "outgoing_count": len(outgoing),
                    "incoming_count": len(incoming)
                }
            
            return PluginResponse(
                success=True,
                data=details,
                suggestions=[
                    "Repository details retrieved successfully",
                    "Use store_repository_deep_analysis() to add Phase 2 analysis" if not repo.deep_analysis else "Deep analysis available",
                    "Use add_repository_dependency() to add dependency relationships"
                ],
                metadata={
                    "phase_1_complete": bool(repo.insights),
                    "phase_2_complete": repo.deep_analysis is not None,
                    "has_components": bool(repo.assigned_components),
                    "dependency_relationships": (
                        len(outgoing) + len(incoming) 
                        if include_dependencies else "not_requested"
                    )
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to get repository details: {str(e)}",
                suggestions=[
                    "Verify repository name exists",
                    "Check if repository has been analyzed"
                ]
            ).model_dump()

    @kernel_function(
        name="get_dependency_graph",
        description="""Generate dependency graph for all repositories.
        
        Returns structured dependency data optimized for both AI agents and humans:
        
        For AI Agents:
        - Structured dict with source->target mappings
        - Dependency types and descriptions
        - Easy to traverse programmatically
        
        For Humans:
        - Summary statistics (total dependencies, most connected repos)
        - Circular dependency detection
        - Orphaned repositories (no dependencies)
        - Optional Mermaid diagram for visualization
        
        Parameters:
        - format: "structured" (default), "mermaid", or "both"
        - include_evidence: Include evidence file paths (default: False)
        
        Returns dependency graph in requested format.""",
    )
    async def get_dependency_graph(
        self,
        format: Annotated[str, "Output format: structured/mermaid/both"] = "structured",
        include_evidence: Annotated[bool, "Include evidence paths"] = False
    ) -> Dict[str, Any]:
        """Generate dependency graph for analysis and visualization."""
        
        try:
            # Validate format
            valid_formats = ["structured", "mermaid", "both"]
            if format not in valid_formats:
                return PluginResponse(
                    success=False,
                    error=f"Invalid format '{format}'. Must be one of: {valid_formats}",
                    suggestions=[
                        "Use 'structured' for programmatic access",
                        "Use 'mermaid' for visualization",
                        "Use 'both' for complete output"
                    ]
                ).model_dump()
            
            # Build dependency graph
            graph = {
                "nodes": [],  # List of all repos with dependencies
                "edges": [],  # List of all dependencies
                "statistics": {},
                "issues": {}
            }
            
            # Collect all dependencies from centralized records
            repos_with_deps = set()
            for dep_record in self.state.dependency_records:
                repos_with_deps.add(dep_record.source_repo)
                repos_with_deps.add(dep_record.target_repo)
                
                edge = {
                    "source": dep_record.source_repo,
                    "target": dep_record.target_repo,
                    "type": dep_record.dependency_type,
                    "description": dep_record.description
                }
                
                # Add evidence if requested
                if include_evidence and dep_record.evidence:
                    edge["evidence"] = dep_record.evidence
                
                graph["edges"].append(edge)
            
            graph["nodes"] = list(repos_with_deps)
            
            # Calculate statistics
            graph["statistics"] = {
                "total_repositories": len(self.state.repositories),
                "repositories_with_dependencies": len(repos_with_deps),
                "total_dependencies": len(graph["edges"]),
                "most_depended_upon": self._find_most_depended_upon(),
                "most_dependent": self._find_most_dependent(),
                "average_dependencies": (
                    len(graph["edges"]) / len(repos_with_deps) 
                    if repos_with_deps else 0
                )
            }
            
            # Detect issues
            graph["issues"] = {
                "circular_dependencies": self._detect_circular_dependencies(),
                "orphaned_repositories": self._find_orphaned_repos()
            }
            
            # Generate Mermaid if requested
            if format in ["mermaid", "both"]:
                mermaid = self._generate_mermaid_diagram(graph)
                if format == "mermaid":
                    return PluginResponse(
                        success=True,
                        data={
                            "mermaid": mermaid, 
                            "statistics": graph["statistics"],
                            "issues": graph["issues"]
                        },
                        suggestions=[
                            "Use Mermaid diagram for visualization",
                            "Copy diagram to markdown files or documentation"
                        ]
                    ).model_dump()
                else:
                    graph["mermaid"] = mermaid
            
            return PluginResponse(
                success=True,
                data=graph,
                suggestions=[
                    "Use 'edges' for programmatic dependency traversal",
                    "Review 'issues' section for potential problems",
                    "Check 'statistics' for dependency insights",
                    "Use format='mermaid' for visualization diagrams"
                ],
                metadata={
                    "format": format,
                    "includes_evidence": include_evidence,
                    "dependency_count": len(graph["edges"]),
                    "repo_coverage": len(repos_with_deps) / len(self.state.repositories) if self.state.repositories else 0
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to generate dependency graph: {str(e)}",
                suggestions=[
                    "Ensure dependencies have been added with add_repository_dependency()",
                    "Check format parameter is valid"
                ]
            ).model_dump()

    @kernel_function(
        name="generate_deep_analysis_report",
        description="""Generate formatted markdown report from Phase 2 analysis data.
        
        Creates a comprehensive human-readable report from structured memory data.
        Designed for stakeholders and migration teams, not for AI consumption.
        
        Report includes:
        - Executive summary with key metrics
        - Repository-by-repository deep analysis
        - Dependency visualization and analysis
        - Technology stack breakdown
        - Component organization
        - Migration considerations from AI insights
        
        Parameters:
        - include_phase1: Include Phase 1 basic analysis (default: True)
        - include_dependencies: Include dependency section (default: True)
        - repo_filter: List of specific repos to include (None for all)
        
        Returns markdown-formatted report ready for documentation.""",
    )
    async def generate_deep_analysis_report(
        self,
        include_phase1: Annotated[bool, "Include Phase 1 analysis"] = True,
        include_dependencies: Annotated[bool, "Include dependency analysis"] = True,
        repo_filter: Annotated[List[str], "Filter to specific repositories"] = None
    ) -> Dict[str, Any]:
        """Generate human-readable markdown report from memory."""
        
        try:
            # Validate repo filter
            if repo_filter:
                invalid = [r for r in repo_filter if r not in self.state.repositories]
                if invalid:
                    return PluginResponse(
                        success=False,
                        error=f"Invalid repositories in filter: {invalid}",
                        suggestions=[
                            "Check repository names in filter",
                            "Run get_all_repos() to see available repositories"
                        ]
                    ).model_dump()
            
            # Build report sections
            report_lines = []
            
            # Header
            report_lines.append("# Deep Repository Analysis Report")
            report_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"**Total Repositories:** {len(self.state.repositories)}")
            
            # Executive Summary
            phase2_count = sum(1 for r in self.state.repositories.values() if r.deep_analysis)
            dep_count = len(self.state.dependency_records)
            
            report_lines.append("\n## Executive Summary")
            report_lines.append(f"- Repositories with deep analysis: {phase2_count}/{len(self.state.repositories)}")
            report_lines.append(f"- Total dependency relationships: {dep_count}")
            report_lines.append(f"- Analysis completion: {(phase2_count / len(self.state.repositories) * 100):.1f}%")
            
            # Repository Deep Dives
            report_lines.append("\n## Repository Analysis")
            
            repos_to_include = repo_filter if repo_filter else sorted(self.state.repositories.keys())
            
            for repo_name in repos_to_include:
                repo = self.state.repositories[repo_name]
                
                report_lines.append(f"\n### {repo_name}")
                
                if include_phase1:
                    report_lines.append("\n**Basic Information:**")
                    report_lines.append(f"- Path: `{repo.path}`")
                    report_lines.append(f"- Files: {repo.total_files} ({repo.total_lines:,} lines)")
                    if repo.file_counts:
                        top_langs = list(repo.file_counts.keys())[:3]
                        report_lines.append(f"- Primary languages: {', '.join(top_langs)}")
                    if repo.technology_stack.frameworks:
                        report_lines.append(f"- Frameworks: {', '.join(repo.technology_stack.frameworks)}")
                
                if repo.deep_analysis:
                    report_lines.append("\n**Deep Analysis:**")
                    report_lines.append(repo.deep_analysis.markdown_summary)
                    
                    if repo.deep_analysis.deep_insights:
                        report_lines.append("\n**Key Insights:**")
                        for key, value in repo.deep_analysis.deep_insights.items():
                            report_lines.append(f"- **{key}**: {value}")
                else:
                    report_lines.append("\n*No deep analysis available*")
                
                if include_dependencies:
                    outgoing = self._get_outgoing_dependencies(repo_name)
                    incoming = self._get_incoming_dependencies(repo_name)
                    
                    if outgoing or incoming:
                        report_lines.append("\n**Dependencies:**")
                        
                        if outgoing:
                            report_lines.append("\n*Depends on:*")
                            for dep in outgoing:
                                report_lines.append(f"- → `{dep['target_repo']}` ({dep['dependency_type']}): {dep['description']}")
                        
                        if incoming:
                            report_lines.append("\n*Depended upon by:*")
                            for dep in incoming:
                                report_lines.append(f"- ← `{dep['source_repo']}` ({dep['dependency_type']}): {dep['description']}")
            
            # Dependency Graph Section
            if include_dependencies and self.state.dependency_records:
                report_lines.append("\n## Dependency Analysis")
                
                # Get dependency statistics
                dep_graph_result = await self.get_dependency_graph(format="both")
                if dep_graph_result["success"]:
                    dep_data = dep_graph_result["data"]
                    stats = dep_data["statistics"]
                    
                    report_lines.append(f"- Total dependencies: {stats['total_dependencies']}")
                    report_lines.append(f"- Repositories with dependencies: {stats['repositories_with_dependencies']}")
                    
                    if stats.get('most_depended_upon'):
                        report_lines.append(f"- Most depended upon: `{stats['most_depended_upon']}`")
                    if stats.get('most_dependent'):
                        report_lines.append(f"- Most dependent: `{stats['most_dependent']}`")
                    
                    # Issues
                    if dep_data["issues"]["circular_dependencies"]:
                        report_lines.append(f"\n**⚠️ Circular Dependencies Detected:**")
                        for cycle in dep_data["issues"]["circular_dependencies"]:
                            report_lines.append(f"- {' ↔ '.join(cycle)}")
                    
                    if dep_data["issues"]["orphaned_repositories"]:
                        report_lines.append(f"\n**Isolated Repositories:**")
                        for orphan in dep_data["issues"]["orphaned_repositories"]:
                            report_lines.append(f"- `{orphan}` (no dependencies)")
                    
                    # Mermaid diagram
                    if dep_data.get("mermaid"):
                        report_lines.append("\n### Dependency Diagram")
                        report_lines.append("\n```mermaid")
                        report_lines.append(dep_data["mermaid"])
                        report_lines.append("```")
            
            # Join and return
            report_content = "\n".join(report_lines)
            
            return PluginResponse(
                success=True,
                data={
                    "report": report_content,
                    "statistics": {
                        "repositories_included": len(repos_to_include),
                        "deep_analyses_included": phase2_count,
                        "dependencies_included": dep_count,
                        "report_length": len(report_content),
                        "word_count": len(report_content.split())
                    }
                },
                suggestions=[
                    "Report generated successfully",
                    "Save report to markdown file for documentation",
                    "Share with migration planning teams"
                ],
                metadata={
                    "includes_phase1": include_phase1,
                    "includes_dependencies": include_dependencies,
                    "filtered_repos": repo_filter is not None,
                    "completion_percentage": (phase2_count / len(self.state.repositories) * 100) if self.state.repositories else 0
                }
            ).model_dump()
            
        except Exception as e:
            return PluginResponse(
                success=False,
                error=f"Failed to generate deep analysis report: {str(e)}",
                suggestions=[
                    "Ensure repositories have deep analysis data",
                    "Check repo_filter contains valid repository names",
                    "Verify dependencies have been added"
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
            
            # Update progress counters
            self.state.repositories_with_insights = len([
                repo for repo in self.state.repositories.values() 
                if repo.insights
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
                    'assigned_components': repo_metadata.assigned_components,
                    'discovery_status': repo_metadata.discovery_phase_status
                }
            
            progress = self.state.get_progress_summary()
            
            return PluginResponse(
                success=True,
                data=repos_data,
                suggestions=[
                    "Repository discovery initiated - proceed to investigation phase",
                    "Use get_unanalyzed_repos() to find repositories needing investigation or assignment",
                    "Investigate repositories using filesystem tools to understand their purpose",
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
        
        # Suggest investigation based on file types
        if '.py' in repo_metadata.file_counts:
            suggestions.append("Look for main.py, app.py, or manage.py entry points")
        elif '.js' in repo_metadata.file_counts:
            suggestions.append("Check package.json and look for index.js or server.js")
        elif '.java' in repo_metadata.file_counts:
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
        file_types = {}
        frameworks = set()
        
        for repo_name in repo_names:
            if repo_name in self.state.repositories:
                repo = self.state.repositories[repo_name]
                
                # Count file types
                for file_type, count in repo.file_counts.items():
                    file_types[file_type] = file_types.get(file_type, 0) + count
                
                # Collect frameworks
                frameworks.update(repo.technology_stack.frameworks)
        
        return {
            'primary_file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
            'frameworks': sorted(list(frameworks)),
            'file_type_diversity': len(file_types),
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
    
    # === Phase 2 Helper Methods ===
    
    def _get_outgoing_dependencies(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get outgoing dependencies for a repository with caching."""
        if '_outgoing_cache' not in self._dependency_cache:
            self._build_dependency_cache()
        
        return self._dependency_cache['_outgoing_cache'].get(repo_name, [])

    def _get_incoming_dependencies(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get incoming dependencies for a repository with caching."""
        if '_incoming_cache' not in self._dependency_cache:
            self._build_dependency_cache()
        
        return self._dependency_cache['_incoming_cache'].get(repo_name, [])

    def _build_dependency_cache(self):
        """Build outgoing and incoming dependency caches."""
        outgoing = {}
        incoming = {}
        
        for dep in self.state.dependency_records:
            # Build outgoing cache
            if dep.source_repo not in outgoing:
                outgoing[dep.source_repo] = []
            outgoing[dep.source_repo].append({
                'target_repo': dep.target_repo,
                'dependency_type': dep.dependency_type,
                'description': dep.description,
                'evidence': dep.evidence,
                'created_at': dep.created_at.isoformat()
            })
            
            # Build incoming cache
            if dep.target_repo not in incoming:
                incoming[dep.target_repo] = []
            incoming[dep.target_repo].append({
                'source_repo': dep.source_repo,
                'dependency_type': dep.dependency_type,
                'description': dep.description,
                'evidence': dep.evidence,
                'created_at': dep.created_at.isoformat()
            })
        
        self._dependency_cache['_outgoing_cache'] = outgoing
        self._dependency_cache['_incoming_cache'] = incoming

    def _clear_dependency_cache(self):
        """Clear dependency cache after updates."""
        self._dependency_cache = {}

    def _find_most_depended_upon(self) -> Optional[str]:
        """Find repository with most incoming dependencies."""
        if not self.state.dependency_records:
            return None
        
        incoming_counts = {}
        for dep in self.state.dependency_records:
            incoming_counts[dep.target_repo] = incoming_counts.get(dep.target_repo, 0) + 1
        
        return max(incoming_counts.items(), key=lambda x: x[1])[0] if incoming_counts else None

    def _find_most_dependent(self) -> Optional[str]:
        """Find repository with most outgoing dependencies."""
        if not self.state.dependency_records:
            return None
        
        outgoing_counts = {}
        for dep in self.state.dependency_records:
            outgoing_counts[dep.source_repo] = outgoing_counts.get(dep.source_repo, 0) + 1
        
        return max(outgoing_counts.items(), key=lambda x: x[1])[0] if outgoing_counts else None

    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the dependency graph."""
        # Build adjacency list
        graph = {}
        for dep in self.state.dependency_records:
            if dep.source_repo not in graph:
                graph[dep.source_repo] = []
            graph[dep.source_repo].append(dep.target_repo)
        
        # Simple cycle detection (could be enhanced for complex cycles)
        cycles = []
        
        def has_path(start, end, path):
            if start == end and len(path) > 1:
                return True
            if start in path:
                return False
            
            path = path + [start]
            for neighbor in graph.get(start, []):
                if has_path(neighbor, end, path):
                    return True
            return False
        
        # Check for cycles
        visited_pairs = set()
        for source_repo in graph:
            for target_repo in graph[source_repo]:
                pair = (source_repo, target_repo)
                reverse_pair = (target_repo, source_repo)
                
                if pair not in visited_pairs and reverse_pair not in visited_pairs:
                    visited_pairs.add(pair)
                    if has_path(target_repo, source_repo, []):
                        cycles.append([source_repo, target_repo])
        
        return cycles

    def _find_orphaned_repos(self) -> List[str]:
        """Find repositories with no dependencies (incoming or outgoing)."""
        repos_with_deps = set()
        
        for dep in self.state.dependency_records:
            repos_with_deps.add(dep.source_repo)
            repos_with_deps.add(dep.target_repo)
        
        all_repos = set(self.state.repositories.keys())
        return list(all_repos - repos_with_deps)

    def _generate_mermaid_diagram(self, graph: Dict[str, Any]) -> str:
        """Generate Mermaid diagram for dependency visualization."""
        lines = ["graph TD"]
        
        # Add nodes and edges
        for edge in graph.get("edges", []):
            source = edge["source"].replace("-", "_")
            target = edge["target"].replace("-", "_")
            dep_type = edge["type"]
            lines.append(f'    {source} -->|{dep_type}| {target}')
        
        return "\n".join(lines)