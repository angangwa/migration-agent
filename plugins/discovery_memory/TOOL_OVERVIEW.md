# get_all_repos() Tool Overview

## Purpose
Provides comprehensive repository inventory with automated analysis for discovery and migration planning. The primary entry point for repository analysis that triggers automated scanning on first use.

## What It Does
- **First call**: Automatically analyzes all repositories in parallel
- **Subsequent calls**: Returns cached results instantly
- **Output**: Clean, structured metadata optimized for AI agents

## How It Works

### Analysis Process
1. **Repository Discovery**: Scans the repos directory for all subdirectories
2. **Parallel Analysis**: Processes 4-8 repositories simultaneously
3. **File Analysis**: Counts files by extension, calculates exact line counts
4. **Framework Detection**: Parses config files to identify technologies
5. **Metadata Extraction**: README detection, repository statistics
6. **Caching**: Stores results in JSON for instant future access

### Framework Detection Engine
- **Configuration Parsing**: package.json, requirements.txt, pom.xml, .csproj, etc.
- **Enterprise Focus**: Comprehensive .NET support (ASP.NET, Entity Framework, WPF, Blazor)
- **Multi-Language**: Java (Spring), Python (Django, Flask), JavaScript (React, Express)
- **Extensible**: Easy to add new framework patterns

### Line Counting
- **Exact counts**: Uses Python's `sum(1 for line in f)` pattern
- **Cross-platform**: No dependency on external tools like `wc`
- **Performance**: Limits to files <1MB, handles encoding errors gracefully
- **Fast**: Processes thousands of files in seconds

## Output Structure

### Repository Entry
```json
{
  "name": "repository_name",
  "path": "relative/path/to/repo",
  "file_extensions": {
    ".py": 45,
    ".js": 12,
    ".yaml": 3,
    "others": 8
  },
  "frameworks": ["Django", "React", "PostgreSQL"],
  "total_files": 68,
  "total_lines": 12500,
  "has_readme": true,
  "assigned_components": ["backend-services"]
}
```

### Metadata Section
```json
{
  "total_repositories": 8,
  "analyzed_repositories": 8,
  "repositories_with_agent_insights": 0,
  "unanalyzed_count": 0,
  "analysis_progress": 100.0,
  "investigation_progress": 0.0,
  "components_created": 0,
  "unassigned_repos": 8
}
```

### Suggestions
- Actionable next steps for agents
- Priority guidance (focus on large/complex repos first)
- Workflow recommendations

## Key Features

### 🚀 **Performance**
- **Bulk analysis**: 92 repositories in 3-5 minutes
- **Individual speed**: ~2 seconds per repository
- **Parallel processing**: Configurable worker count
- **Instant caching**: Subsequent calls complete in milliseconds

### 🔍 **Comprehensive Analysis**
- **File breakdown**: Top 10 extensions + "others" for the rest
- **Exact metrics**: Real line counts, not estimates
- **Framework detection**: 50+ enterprise frameworks supported
- **README detection**: Documentation presence tracking

### 🤖 **Agent Optimized**
- **Clean output**: No unnecessary fields or verbose data
- **Structured format**: Consistent JSON schema
- **Actionable insights**: Focus on what agents need to know
- **Progress tracking**: Clear metrics for workflow management

## Behavior

### First Call
- Triggers automatic analysis of all repositories
- Shows progress output: `[1/8] (12.5%) Analyzing: repo_name`
- Returns complete inventory with fresh analysis
- Caches results for future calls

### Subsequent Calls
- Returns cached data instantly (0.000 seconds)
- No re-analysis unless cache is cleared
- Consistent data across multiple calls

### Error Handling
- Graceful failure: Partial results if some repos fail
- Permission errors: Skips inaccessible files/directories
- Encoding issues: Handles binary files and encoding errors
- Resource limits: Stops processing at 5000 files per repo

## Integration Points

### With Discovery Agent
- **Phase 1**: Primary tool for "Repository Discovery & Initial Assessment"
- **Workflow trigger**: Starts the 5-phase discovery process
- **Data foundation**: Provides baseline for all subsequent analysis

### With Other Tools
- **get_unanalyzed_repos()**: Uses analysis status from this tool
- **store_repo_insights()**: Enhances data collected here
- **Component tools**: Uses repository list from this tool

## Configuration

### Initialization Parameters
- **repos_path**: Directory containing repositories (default: './repos')
- **storage_dir**: Cache location (default: './.discovery_cache')

### Performance Tuning
- **max_workers**: Parallel processing threads (default: 4)
- **max_files_scan**: File limit per repo (default: 5000)
- **file_size_limit**: Skip files larger than 1MB for line counting

## Example Usage

```python
# First call - triggers analysis
result = await plugin.get_all_repos()
print(f"Analyzed {len(result['data'])} repositories")

# Subsequent calls - instant from cache  
result2 = await plugin.get_all_repos()  # 0.000 seconds
```

## Performance Benchmarks
- **8 repositories**: ~3-5 seconds (fresh analysis)
- **92 repositories**: ~3-5 minutes (enterprise scale)
- **Cache retrieval**: <0.001 seconds
- **Memory usage**: ~500MB peak during analysis