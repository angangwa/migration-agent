"""
Data models for DiscoveryMemoryPlugin.

This module contains all the Pydantic models used for structured data
representation in the DiscoveryMemoryPlugin.
"""

from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum




class PluginResponse(BaseModel):
    """Standard response format for all plugin functions."""
    success: bool = Field(description="Whether the operation succeeded")
    data: Optional[Any] = Field(default=None, description="The actual result data")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    suggestions: List[str] = Field(
        default_factory=list, description="Helpful suggestions for next steps"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context and statistics"
    )


class TechnologyStack(BaseModel):
    """Technology stack information for a repository."""
    frameworks: List[str] = Field(
        default_factory=list,
        description="Detected frameworks (Spring Boot, Django, Express, etc.)"
    )


class DeepAnalysis(BaseModel):
    """Phase 2 comprehensive analysis data."""
    markdown_summary: str = Field(description="Comprehensive markdown analysis report")
    deep_insights: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom key-value insights for additional findings"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When deep analysis was performed"
    )


class RepoMetadata(BaseModel):
    """Comprehensive repository metadata."""
    name: str = Field(description="Repository name")
    path: str = Field(description="Relative path from base repos directory")
    
    # Discovery phase status  
    discovery_phase_status: str = Field(
        default="No insights added. Assigned to no components.",
        description="Natural language status of discovery progress"
    )
    # Basic statistics
    total_files: int = Field(default=0, description="Total number of files")
    file_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="File counts by extension"
    )
    total_lines: int = Field(default=0, description="Total lines of code (exact count)")
    
    # Technology information
    technology_stack: TechnologyStack = Field(
        default_factory=TechnologyStack,
        description="Detected technology stack"
    )
    
    # Documentation
    has_readme: bool = Field(default=False, description="Has README file")
    
    # Dependencies (basic detection)
    config_files: List[str] = Field(
        default_factory=list,
        description="Configuration files found (package.json, requirements.txt, etc.)"
    )
    
    # Agent insights (enhanced by store_repo_insights)
    insights: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed insights stored by the agent"
    )
    
    # Component assignments
    assigned_components: List[str] = Field(
        default_factory=list,
        description="Components this repository is assigned to"
    )
    
    # Phase 2: Deep analysis (optional for backward compatibility)
    deep_analysis: Optional[DeepAnalysis] = Field(
        default=None,
        description="Phase 2 comprehensive analysis data"
    )
    
    def update_discovery_status(self):
        """Update discovery phase status based on current state."""
        has_insights = bool(self.insights)
        has_components = bool(self.assigned_components)
        
        if has_insights and has_components:
            component_list = ", ".join(self.assigned_components)
            self.discovery_phase_status = f"Insights added. Assigned to components: {component_list}."
        elif has_insights and not has_components:
            self.discovery_phase_status = "Insights added. Assigned to no components."
        elif not has_insights and has_components:
            component_list = ", ".join(self.assigned_components)
            self.discovery_phase_status = f"No insights added. Assigned to components: {component_list}."
        else:
            self.discovery_phase_status = "No insights added. Assigned to no components."
    


class ComponentData(BaseModel):
    """Logical component information."""
    name: str = Field(description="Component name")
    purpose: str = Field(description="Component purpose/description")
    rationale: str = Field(description="Rationale for component creation")
    
    # Repository assignments
    repositories: List[str] = Field(
        default_factory=list,
        description="List of repository names assigned to this component"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When component was created"
    )


class DependencyRecord(BaseModel):
    """Structured dependency information with evidence tracking."""
    source_repo: str = Field(description="Repository that has the dependency")
    target_repo: str = Field(description="Repository being depended upon")
    dependency_type: str = Field(description="Descriptive dependency type (flexible, e.g. api, database, shared-library)")
    description: str = Field(description="Clear description of the dependency")
    evidence: List[str] = Field(
        default_factory=list,
        description="File paths or code snippets as evidence"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When dependency was recorded"
    )


class AnalysisState(BaseModel):
    """Overall analysis state and progress tracking."""
    
    # Repository tracking
    repositories: Dict[str, RepoMetadata] = Field(
        default_factory=dict,
        description="All repository metadata keyed by repo name"
    )
    
    # Component tracking  
    components: Dict[str, ComponentData] = Field(
        default_factory=dict,
        description="All components keyed by component name"
    )
    
    # Phase 2: Centralized dependency tracking
    dependency_records: List[DependencyRecord] = Field(
        default_factory=list,
        description="All dependencies between repositories"
    )
    
    # Progress tracking
    total_repositories: int = Field(default=0, description="Total repositories found")
    repositories_with_insights: int = Field(default=0, description="Repositories with agent insights")
    
    # Analysis metadata
    analysis_started: Optional[datetime] = Field(
        default=None,
        description="When initial analysis started"
    )
    analysis_completed: Optional[datetime] = Field(
        default=None,
        description="When initial analysis completed"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    
    # Settings
    base_repos_path: str = Field(description="Base path to repositories")
    
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get discovery progress summary."""
        # Calculate current status counts
        insights_added = len([repo for repo in self.repositories.values() if repo.insights])
        assigned_repos = len([repo for repo in self.repositories.values() if repo.assigned_components])
        
        return {
            "total_repositories": self.total_repositories,
            "repositories_with_insights": insights_added,
            "repositories_assigned_to_components": assigned_repos,
            "components_created": len(self.components),
            "unassigned_repos": self.total_repositories - assigned_repos,
            "investigation_progress": (
                insights_added / self.total_repositories * 100 
                if self.total_repositories > 0 else 0
            ),
            "assignment_progress": (
                assigned_repos / self.total_repositories * 100
                if self.total_repositories > 0 else 0
            )
        }
    
    def needs_investigation(self) -> bool:
        """Check if any repositories still need investigation or assignment."""
        return any(
            not repo.insights or not repo.assigned_components
            for repo in self.repositories.values()
        )



# Configuration file patterns for framework detection
CONFIG_PATTERNS = {
    "package.json": {"language": "JavaScript/TypeScript", "type": "npm"},
    "requirements.txt": {"language": "Python", "type": "pip"},
    "Pipfile": {"language": "Python", "type": "pipenv"},
    "pyproject.toml": {"language": "Python", "type": "poetry/setuptools"},
    "pom.xml": {"language": "Java", "type": "maven"},
    "build.gradle": {"language": "Java/Kotlin", "type": "gradle"},
    "Cargo.toml": {"language": "Rust", "type": "cargo"},
    "go.mod": {"language": "Go", "type": "go_modules"},
    "composer.json": {"language": "PHP", "type": "composer"},
    ".csproj": {"language": "C#", "type": "dotnet_project"},
    ".vbproj": {"language": "VB.NET", "type": "dotnet_project"},
    ".fsproj": {"language": "F#", "type": "dotnet_project"},
    ".sln": {"language": "C#/.NET", "type": "dotnet_solution"},
    "packages.config": {"language": "C#", "type": "nuget"},
    "Directory.Build.props": {"language": "C#/.NET", "type": "dotnet_build"},
    "global.json": {"language": "C#/.NET", "type": "dotnet_sdk"},
    "Gemfile": {"language": "Ruby", "type": "bundler"}
}

# Framework detection patterns
FRAMEWORK_PATTERNS = {
    # .NET / C# Frameworks (Enterprise focused)
    "ASP.NET Core": ["Microsoft.AspNetCore", "AspNetCore", "Microsoft.Extensions"],
    "ASP.NET Framework": ["System.Web", "Microsoft.AspNet", "WebForms"],
    "Entity Framework": ["Microsoft.EntityFrameworkCore", "EntityFramework"],
    "WPF": ["Microsoft.WindowsDesktop.App", "PresentationFramework"],
    "WinForms": ["System.Windows.Forms", "Microsoft.WindowsDesktop"],
    "Blazor": ["Microsoft.AspNetCore.Blazor", "Blazor"],
    "SignalR": ["Microsoft.AspNetCore.SignalR", "SignalR"],
    "Minimal APIs": ["Microsoft.AspNetCore.Http", "WebApplication"],
    "Xamarin": ["Xamarin.Forms", "Xamarin.iOS", "Xamarin.Android"],
    "MAUI": ["Microsoft.Maui", ".NET MAUI"],
    
    # Java Frameworks
    "Spring Boot": ["spring-boot-starter", "SpringBootApplication"],
    "Spring Framework": ["springframework", "spring-context", "spring-core"],
    "Spring Security": ["spring-security", "spring-boot-starter-security"],
    "Spring Data": ["spring-data", "spring-boot-starter-data"],
    "Hibernate": ["hibernate-core", "hibernate-entitymanager"],
    "JPA": ["javax.persistence", "jakarta.persistence"],
    "Struts": ["struts2", "apache-struts"],
    "JSF": ["javax.faces", "jakarta.faces"],
    "Jersey": ["jersey-server", "jersey-client"],
    "Dropwizard": ["dropwizard-core", "dropwizard"],
    "Micronaut": ["micronaut-core", "micronaut"],
    "Quarkus": ["quarkus-core", "quarkus"],
    
    # Python Frameworks
    "Django": ["django", "Django"],
    "Flask": ["flask", "Flask"],
    "FastAPI": ["fastapi", "FastAPI"],
    "Tornado": ["tornado"],
    "Pyramid": ["pyramid"],
    "Bottle": ["bottle"],
    "CherryPy": ["cherrypy"],
    "Starlette": ["starlette"],
    
    # JavaScript/TypeScript Frameworks
    "Express.js": ["express", "expressjs"],
    "NestJS": ["@nestjs/core", "nestjs"],
    "Koa": ["koa", "koa2"],
    "Hapi": ["@hapi/hapi", "hapi"],
    "Fastify": ["fastify"],
    "Next.js": ["next", "nextjs"],
    "Nuxt.js": ["nuxt", "nuxtjs"],
    "React": ["react", "React"],
    "Vue.js": ["vue", "Vue"],
    "Angular": ["@angular/core", "angular"],
    "Svelte": ["svelte"],
    "Ember.js": ["ember-cli", "emberjs"],
    
    # PHP Frameworks
    "Laravel": ["laravel/framework", "Laravel"],
    "Symfony": ["symfony/framework", "Symfony"],
    "CodeIgniter": ["codeigniter", "CodeIgniter"],
    "Zend/Laminas": ["zendframework", "laminas"],
    "CakePHP": ["cakephp/cakephp", "CakePHP"],
    "Yii": ["yiisoft/yii2", "Yii"],
    
    # Ruby Frameworks
    "Ruby on Rails": ["rails", "Ruby on Rails"],
    "Sinatra": ["sinatra"],
    "Hanami": ["hanami"],
    
    # Go Frameworks
    "Gin": ["gin-gonic/gin", "gin"],
    "Echo": ["labstack/echo", "echo"],
    "Fiber": ["gofiber/fiber", "fiber"],
    "Beego": ["beego/beego", "beego"],
    "Revel": ["revel/revel", "revel"],
    
    # Rust Frameworks
    "Actix": ["actix-web"],
    "Rocket": ["rocket"],
    "Warp": ["warp"],
    "Axum": ["axum"],
    
    # Additional Enterprise Technologies
    "Apache Kafka": ["kafka", "apache-kafka"],
    "RabbitMQ": ["rabbitmq", "amqp"],
    "Redis": ["redis", "jedis"],
    "Elasticsearch": ["elasticsearch"],
    "GraphQL": ["graphql", "apollo"],
    "gRPC": ["grpc", "protobuf"],
    
    # Infrastructure as Code
    "Terraform": ["terraform", "provider", "resource"],
    "CloudFormation": ["AWSTemplateFormatVersion", "aws::"],
    "Pulumi": ["@pulumi/", "pulumi."],
    "Helm": ["Chart.yaml", "helm"],
    "Ansible": ["ansible", "playbook"],
    "CDK": ["aws-cdk", "@aws-cdk"],
    
    # Cloud Functions & Serverless
    "AWS Lambda": ["aws-lambda", "lambda_function", "handler"],
    "Azure Functions": ["azure-functions", "function.json"],
    "Google Cloud Functions": ["google-cloud-functions", "functions-framework"],
    "Serverless Framework": ["serverless", "serverless.yml"],
    
    # Modern JavaScript Frameworks
    "Remix": ["@remix-run", "remix"],
    "SvelteKit": ["@sveltejs/kit", "sveltekit"],
    "Astro": ["astro", "@astrojs"],
    "Solid.js": ["solid-js", "@solidjs"],
    "Qwik": ["@builder.io/qwik", "qwik"],
    
    # Data & Analytics
    "Apache Spark": ["pyspark", "org.apache.spark"],
    "Apache Airflow": ["airflow", "from airflow"],
    "dbt": ["dbt-core", "dbt_project.yml"],
    "Jupyter": [".ipynb", "jupyter"],
    "Pandas": ["pandas", "import pandas"],
    "NumPy": ["numpy", "import numpy"],
    
    # Testing Frameworks
    "Jest": ["jest", "@jest/"],
    "Mocha": ["mocha", "describe("],
    "Cypress": ["cypress", "@cypress/"],
    "Playwright": ["@playwright/", "playwright"],
    "pytest": ["pytest", "import pytest"],
    "JUnit": ["junit", "org.junit"],
    "TestNG": ["testng", "org.testng"],
    "RSpec": ["rspec", "describe "],
    
    # Mobile & Desktop
    "Flutter": ["flutter", "pubspec.yaml"],
    "React Native": ["react-native", "@react-native"],
    "Electron": ["electron", "@electron/"],
    "Tauri": ["@tauri-apps", "tauri"],
    
    # Additional Modern Tools
    "Vite": ["vite", "@vitejs"],
    "Webpack": ["webpack", "webpack.config"],
    "esbuild": ["esbuild"],
    "Rollup": ["rollup", "rollup.config"],
    "Turbo": ["turbo", "turbo.json"],
    "Nx": ["@nrwl/nx", "@nx/"],
}