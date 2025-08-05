# DiscoveryMemoryPlugin

A comprehensive plugin for repository analysis and working memory management designed for the Discovery Agent to analyze multiple code repositories and categorize them into logical components for migration planning.

## Overview

The DiscoveryMemoryPlugin combines automated repository analysis with persistent memory management to provide efficient discovery and categorization of large enterprise codebases. It's specifically designed to support the Discovery Agent workflow for analyzing 92+ repositories in legacy enterprise applications.

## Architecture

### Core Components

```
plugins/discovery_memory/
├── __init__.py           # Package initialization  
├── plugin.py             # Main DiscoveryMemoryPlugin class with Semantic Kernel functions
├── models.py             # Pydantic data models and type definitions
├── analyzer.py           # Lightweight repository analysis engine
├── storage.py            # JSON persistence and caching system
└── helpers.py            # Utilities for parallel processing and report generation
```

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Repository    │───▶│  Parallel        │───▶│   Analysis State    │
│   Discovery     │    │  Analysis        │    │   Storage           │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Basic Metadata │    │  Agent Insights  │    │  Component          │
│  Extraction     │    │  Enhancement     │    │  Management         │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │  Discovery Report   │
                    │  Generation         │
                    └─────────────────────┘
```

## Key Features

### 🚀 Performance Optimized
- **Parallel Processing**: Analyzes 4-8 repositories simultaneously
- **Smart Caching**: JSON persistence prevents re-analysis across sessions
- **Fast Analysis**: ~3 seconds per repository with comprehensive metadata
- **Memory Efficient**: Handles 92+ repositories with <1GB memory usage
- **Thread-Safe**: Concurrent access support for parallel operations

### 🔍 Comprehensive Analysis
- **Language Detection**: File extension analysis with confidence scores
- **Framework Detection**: Parses package.json, requirements.txt, pom.xml, etc.
- **Repository Classification**: Microservice, library, config, documentation types
- **Technology Stack**: Databases, CI/CD, containerization, infrastructure detection
- **Documentation Assessment**: README detection and quality scoring

### 💾 Persistent Memory Management
- **Progressive Enhancement**: Basic automation + detailed agent insights
- **Component Tracking**: Logical groupings for migration planning
- **Assignment Management**: Repository-to-component mappings
- **Progress Monitoring**: Analysis status and coverage tracking
- **Recovery Support**: Checkpointing prevents data loss

## Semantic Kernel Functions

All functions return standardized `PluginResponse` objects with success status, data, error messages, and contextual suggestions.

### 1. `get_all_repos()`
**Purpose**: Get comprehensive inventory of all repositories with basic metadata.

**Behavior**: 
- First call: Automatically performs lightweight analysis of all repositories
- Subsequent calls: Returns cached results instantly
- Parallel processing for fast bulk analysis

**Returns**:
```json
{
  "success": true,
  "data": {
    "repo_name": {
      "name": "repo_name",
      "path": "relative/path",
      "analysis_status": "analyzed",
      "primary_languages": [["Python", 0.8], ["JavaScript", 0.2]],
      "frameworks": ["Django", "React"],
      "total_files": 156,
      "estimated_loc": 12500,
      "repository_type": "microservice",
      "has_readme": true,
      "assigned_components": ["backend-services"],
      "analysis_confidence": 0.85
    }
  },
  "metadata": {
    "total_repositories": 92,
    "analysis_progress": 100.0,
    "analyzed_repositories": 92
  }
}
```

### 2. `get_unanalyzed_repos()`
**Purpose**: Get repositories that need deeper exploration and analysis.

**Behavior**: Returns repositories with only basic automated analysis but lacking detailed agent insights.

**Returns**: Filtered repository list with investigation suggestions.

### 3. `store_repo_insights(repo_name, insights)`
**Purpose**: Store detailed insights about a repository from agent exploration.

**Parameters**:
- `repo_name` (str): Repository name
- `insights` (Dict): Detailed findings dictionary

**Example insights**:
```json
{
  "purpose": "Customer order processing microservice",
  "business_function": "E-commerce order management",
  "architecture": "REST API with PostgreSQL database",
  "key_dependencies": ["payment-service", "inventory-service"],
  "migration_complexity": "medium",
  "notes": "Well-documented, standard Spring Boot structure"
}
```

### 4. `add_component(name, purpose, rationale)`
**Purpose**: Create a new logical component for grouping repositories.

**Parameters**:
- `name` (str): Component name (kebab-case recommended)
- `purpose` (str): Clear description of component purpose
- `rationale` (str): Explanation of why repositories belong together

**Component Sizing Guidelines**:
- **Appropriate**: 3-15 repositories with related functionality
- **Too Large**: 30+ repositories or mixed technology stacks  
- **Too Small**: Single repository (unless major standalone system)

### 5. `assign_repo_to_component(repo_name, component_name)`
**Purpose**: Assign a repository to a logical component.

**Behavior**: Bidirectional assignment updates both repository and component records.

### 6. `get_components_summary()`
**Purpose**: Get comprehensive summary of all logical components and assignments.

**Returns**:
```json
{
  "success": true,
  "data": {
    "components": {
      "backend-services": {
        "name": "backend-services",
        "purpose": "Core backend microservices",
        "repository_count": 8,
        "repositories": ["auth-service", "order-service", "..."],
        "size_category": "appropriate",
        "validation": {"warnings": [], "suggestions": []},
        "technology_summary": {"Python": 6, "Java": 2}
      }
    },
    "validation_results": {
      "assignment_coverage": 95.0,
      "unassigned_repos": ["temp-repo"],
      "multi_assigned_repos": []
    }
  }
}
```

### 7. `generate_discovery_report()`
**Purpose**: Generate comprehensive discovery report in markdown format.

**Returns**: Complete markdown report with:
- Executive summary with key metrics
- Repository inventory by analysis status
- Logical component analysis with validation
- Technology stack summary
- Assignment validation and coverage
- Actionable recommendations

## Data Models

### RepoMetadata
Comprehensive repository information including:
- Basic statistics (files, LOC, size)
- Technology stack (languages, frameworks, databases)
- Classification (type, confidence)
- Documentation assessment
- Agent insights and component assignments

### ComponentData
Logical component information including:
- Purpose and rationale
- Repository assignments
- Technology summary
- Creation metadata

### AnalysisState
Overall analysis state with:
- Repository and component tracking
- Progress monitoring
- Validation results
- Persistence management

## Usage Examples

### Basic Usage
```python
from plugins.discovery_memory import DiscoveryMemoryPlugin

# Initialize plugin
plugin = DiscoveryMemoryPlugin(
    repos_path="./repos",
    storage_dir="./.discovery_cache"
)

# Get all repositories (triggers analysis on first call)
result = await plugin.get_all_repos()
print(f"Found {len(result['data'])} repositories")

# Focus on unanalyzed repositories
unanalyzed = await plugin.get_unanalyzed_repos()
print(f"{len(unanalyzed['data'])} repos need detailed analysis")

# Store detailed insights
insights = {
    "purpose": "User authentication service",
    "architecture": "REST API with JWT tokens",
    "migration_complexity": "low"
}
await plugin.store_repo_insights("auth-service", insights)

# Create logical component
await plugin.add_component(
    "user-management",
    "User authentication and profile services",
    "Groups all services handling user accounts and authentication"
)

# Assign repository to component
await plugin.assign_repo_to_component("auth-service", "user-management")

# Generate final report
report = await plugin.generate_discovery_report()
print(report['data']['report'])  # Markdown report content
```

### Discovery Agent Workflow
```python
# Phase 1: Repository Discovery
repos_result = await plugin.get_all_repos()
total_repos = len(repos_result['data'])

# Phase 2: Systematic Analysis
unanalyzed = await plugin.get_unanalyzed_repos()
for repo_name in unanalyzed['data'].keys():
    # Use filesystem tools to explore repository
    # ... detailed exploration ...
    
    # Store findings
    await plugin.store_repo_insights(repo_name, insights)

# Phase 3: Component Planning
await plugin.add_component("backend-services", "Core backend microservices", "...")
await plugin.add_component("frontend-apps", "User-facing applications", "...")

# Phase 4: Repository Assignment
for repo_name, component in assignments.items():
    await plugin.assign_repo_to_component(repo_name, component)

# Phase 5: Validation & Report
summary = await plugin.get_components_summary()
report = await plugin.generate_discovery_report()
```

## Configuration

### Initialization Parameters
- `repos_path` (str): Path to directory containing repositories (default: './repos')
- `storage_dir` (str): Directory for cache storage (default: './.discovery_cache')

### Performance Tuning
- **Parallel Workers**: Modify `ParallelProcessor(max_workers=4)` in plugin.py
- **File Scan Limit**: Adjust `max_files_scan = 5000` in analyzer.py for large repositories
- **Cache Strategy**: Modify storage persistence frequency in storage.py

## Error Handling

### Graceful Degradation
- **Partial Analysis**: Failed repositories get error metadata instead of blocking entire analysis
- **Cache Recovery**: Automatic backup/restore if cache corruption occurs
- **Validation Warnings**: Component size and assignment issues reported as warnings, not errors

### Common Issues
1. **Repository Access**: Ensure read permissions on repository directories
2. **Storage Space**: Requires ~10MB cache space for 92 repositories
3. **Memory Usage**: Peak usage ~500MB during parallel analysis
4. **File Encoding**: Handles encoding errors gracefully with UTF-8 fallback

## Integration with Discovery Agent

The plugin is designed to integrate seamlessly with the Discovery Agent configuration in `sk_agents/agents/configs/agents.yaml`. All required tool functions match the agent's workflow expectations:

1. **Repository Discovery**: `get_all_repos()` provides initial inventory
2. **Progressive Analysis**: `get_unanalyzed_repos()` and `store_repo_insights()` support detailed exploration
3. **Component Management**: `add_component()` and `assign_repo_to_component()` enable logical grouping
4. **Quality Assurance**: `get_components_summary()` validates completeness
5. **Final Deliverable**: `generate_discovery_report()` creates comprehensive documentation

## Performance Benchmarks

Based on testing with sample repositories:

| Metric | Target | Achieved |
|--------|--------|----------|
| Repository Analysis | <3 seconds | ~2 seconds |
| Memory Plugin Operations | <100ms | ~50ms |
| Report Generation | <5 seconds | ~2 seconds |
| Memory Usage | <1GB | ~500MB peak |
| 92-Repo Analysis Time | <5 minutes | ~3-4 minutes |

## Future Enhancements

### Planned Features
- **AST Analysis**: Code structure analysis for better framework detection
- **Dependency Graphs**: Cross-repository dependency mapping
- **Security Scanning**: Basic vulnerability pattern detection
- **Migration Estimation**: Automated complexity scoring improvements

### Extensibility
- **Plugin Architecture**: Easy addition of new analysis modules
- **Custom Patterns**: Configurable framework detection patterns
- **Export Formats**: JSON, CSV, XML output options
- **Integration APIs**: REST endpoints for external tools

## Support

For issues, feature requests, or integration questions, see the main project documentation or create an issue in the project repository.