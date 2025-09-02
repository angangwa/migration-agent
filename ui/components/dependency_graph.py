"""Dependency graph visualization component."""

from typing import Dict, List, Any, Optional


def generate_mermaid_graph(
    dependencies: List[Dict[str, Any]],
    highlight_repo: Optional[str] = None
) -> str:
    """Generate Mermaid diagram code for dependencies."""
    
    if not dependencies:
        return "graph LR\n    No_Dependencies[No Dependencies Found]"
    
    # Start Mermaid graph
    lines = ["graph LR"]
    
    # Track unique nodes
    nodes = set()
    
    # Add edges
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        dep_type = dep.get('type', dep.get('dependency_type', 'depends'))
        
        if source and target:
            nodes.add(source)
            nodes.add(target)
            
            # Create edge with label
            edge_label = f"|{dep_type}|" if dep_type else ""
            
            # Highlight if needed
            if highlight_repo and (source == highlight_repo or target == highlight_repo):
                lines.append(f"    {source} ==>{edge_label} {target}")
            else:
                lines.append(f"    {source} -->{edge_label} {target}")
    
    # Style highlighted node
    if highlight_repo and highlight_repo in nodes:
        lines.append(f"    style {highlight_repo} fill:#f96,stroke:#333,stroke-width:4px")
    
    return "\n".join(lines)


def analyze_dependencies(dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze dependency patterns and issues."""
    
    analysis = {
        'total_dependencies': len(dependencies),
        'unique_sources': set(),
        'unique_targets': set(),
        'dependency_types': {},
        'most_dependent': {},
        'most_depended_upon': {},
        'circular_dependencies': [],
        'orphaned_repos': []
    }
    
    # Count dependencies
    source_counts = {}
    target_counts = {}
    
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        dep_type = dep.get('type', dep.get('dependency_type', 'unknown'))
        
        if source:
            analysis['unique_sources'].add(source)
            source_counts[source] = source_counts.get(source, 0) + 1
        
        if target:
            analysis['unique_targets'].add(target)
            target_counts[target] = target_counts.get(target, 0) + 1
        
        # Count dependency types
        analysis['dependency_types'][dep_type] = \
            analysis['dependency_types'].get(dep_type, 0) + 1
    
    # Find most dependent/depended upon
    if source_counts:
        most_dep = max(source_counts.items(), key=lambda x: x[1])
        analysis['most_dependent'] = {'repo': most_dep[0], 'count': most_dep[1]}
    
    if target_counts:
        most_depended = max(target_counts.items(), key=lambda x: x[1])
        analysis['most_depended_upon'] = {'repo': most_depended[0], 'count': most_depended[1]}
    
    # Detect circular dependencies (simple check)
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        
        # Check if reverse dependency exists
        for other_dep in dependencies:
            other_source = other_dep.get('source', other_dep.get('source_repo', ''))
            other_target = other_dep.get('target', other_dep.get('target_repo', ''))
            
            if source == other_target and target == other_source:
                circular = f"{source} <-> {target}"
                if circular not in analysis['circular_dependencies']:
                    analysis['circular_dependencies'].append(circular)
    
    return analysis


def create_dependency_matrix(dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a dependency matrix for visualization."""
    
    # Get all unique repos
    all_repos = set()
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        if source:
            all_repos.add(source)
        if target:
            all_repos.add(target)
    
    # Create matrix
    matrix = {}
    for source in all_repos:
        matrix[source] = {}
        for target in all_repos:
            matrix[source][target] = []
    
    # Fill matrix
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        dep_type = dep.get('type', dep.get('dependency_type', 'depends'))
        
        if source and target:
            matrix[source][target].append(dep_type)
    
    return {
        'matrix': matrix,
        'repos': sorted(list(all_repos))
    }