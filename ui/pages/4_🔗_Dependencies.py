"""Dependencies Visualization Page."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.dependency_graph import (
    generate_mermaid_graph,
    analyze_dependencies,
    create_dependency_matrix
)
from components.markdown_viewer import display_markdown_with_mermaid


st.set_page_config(page_title="Dependencies", page_icon="🔗", layout="wide")

st.title("🔗 Dependency Visualization")
st.markdown("Explore repository dependencies and relationships")
st.markdown("---")

# Check if data is loaded
if 'memory_data' not in st.session_state or not st.session_state.memory_data:
    st.warning("⚠️ No data loaded. Please load data from the main page.")
    st.stop()

data = st.session_state.memory_data

# Check if dependencies exist
dependencies = data.get('dependency_records', [])

if not dependencies:
    st.info("📎 No dependencies found in the data.")
    st.markdown("""
    Dependencies are recorded during Phase 2 analysis and include:
    - API dependencies between services
    - Database connections
    - Shared libraries
    - Configuration dependencies
    - Build/runtime dependencies
    
    If Phase 2 has not been completed, dependencies will not be available.
    """)
    st.stop()

# Analyze dependencies
analysis = analyze_dependencies(dependencies)

# Display summary metrics
st.markdown("### 📊 Dependency Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Dependencies", analysis['total_dependencies'])

with col2:
    st.metric("Unique Sources", len(analysis['unique_sources']))

with col3:
    st.metric("Unique Targets", len(analysis['unique_targets']))

with col4:
    circular_count = len(analysis['circular_dependencies'])
    st.metric("Circular Dependencies", circular_count, delta="⚠️" if circular_count > 0 else "✅")

# Dependency Types
if analysis['dependency_types']:
    st.markdown("---")
    st.markdown("### 📈 Dependency Types")
    
    df_types = pd.DataFrame(
        list(analysis['dependency_types'].items()),
        columns=['Type', 'Count']
    )
    df_types = df_types.sort_values('Count', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(df_types, use_container_width=True, hide_index=True)
    
    with col2:
        st.bar_chart(df_types.set_index('Type')['Count'])

# Most Connected Repositories
st.markdown("---")
st.markdown("### 🌟 Most Connected Repositories")

col1, col2 = st.columns(2)

with col1:
    if analysis['most_dependent']:
        st.info(f"**Most Dependent:** {analysis['most_dependent']['repo']} ({analysis['most_dependent']['count']} dependencies)")

with col2:
    if analysis['most_depended_upon']:
        st.info(f"**Most Depended Upon:** {analysis['most_depended_upon']['repo']} ({analysis['most_depended_upon']['count']} dependents)")

# Issues and Warnings
if analysis['circular_dependencies'] or analysis['orphaned_repos']:
    st.markdown("---")
    st.markdown("### ⚠️ Issues Detected")
    
    if analysis['circular_dependencies']:
        st.warning("**Circular Dependencies Found:**")
        for circular in analysis['circular_dependencies']:
            st.markdown(f"- {circular}")
    
    if analysis['orphaned_repos']:
        with st.expander(f"Orphaned Repositories ({len(analysis['orphaned_repos'])})"):
            for orphan in analysis['orphaned_repos']:
                st.markdown(f"- {orphan}")

# Dependency visualization tabs
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Graph View", "📋 List View", "🔍 Repository Focus", "📊 Matrix View"])

with tab1:
    st.markdown("### Dependency Graph")
    
    # Generate Mermaid diagram
    mermaid_code = generate_mermaid_graph(dependencies)
    
    # Display using markdown viewer
    display_markdown_with_mermaid(f"```mermaid\n{mermaid_code}\n```")
    
    # Option to copy mermaid code
    with st.expander("📋 Copy Mermaid Code"):
        st.code(mermaid_code, language="mermaid")

with tab2:
    st.markdown("### All Dependencies")
    
    # Create dataframe from dependencies
    dep_list = []
    for dep in dependencies:
        dep_list.append({
            'Source': dep.get('source', dep.get('source_repo', '')),
            'Target': dep.get('target', dep.get('target_repo', '')),
            'Type': dep.get('type', dep.get('dependency_type', '')),
            'Description': dep.get('description', ''),
            'Evidence': len(dep.get('evidence', [])) if dep.get('evidence') else 0
        })
    
    df_deps = pd.DataFrame(dep_list)
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        source_filter = st.multiselect(
            "Filter by Source",
            options=df_deps['Source'].unique() if not df_deps.empty else [],
            default=[]
        )
    
    with col2:
        type_filter = st.multiselect(
            "Filter by Type",
            options=df_deps['Type'].unique() if not df_deps.empty else [],
            default=[]
        )
    
    # Apply filters
    filtered_df = df_deps
    if source_filter:
        filtered_df = filtered_df[filtered_df['Source'].isin(source_filter)]
    if type_filter:
        filtered_df = filtered_df[filtered_df['Type'].isin(type_filter)]
    
    # Display table
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Evidence": st.column_config.NumberColumn("Evidence Items")
        }
    )

with tab3:
    st.markdown("### Repository Focus View")
    
    # Select repository to focus on
    all_repos = set()
    for dep in dependencies:
        source = dep.get('source', dep.get('source_repo', ''))
        target = dep.get('target', dep.get('target_repo', ''))
        if source:
            all_repos.add(source)
        if target:
            all_repos.add(target)
    
    selected_repo = st.selectbox(
        "Select repository to analyze:",
        sorted(list(all_repos))
    )
    
    if selected_repo:
        # Find dependencies for selected repo
        outgoing = []
        incoming = []
        
        for dep in dependencies:
            source = dep.get('source', dep.get('source_repo', ''))
            target = dep.get('target', dep.get('target_repo', ''))
            
            if source == selected_repo:
                outgoing.append(dep)
            if target == selected_repo:
                incoming.append(dep)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### Depends On ({len(outgoing)})")
            for dep in outgoing:
                target = dep.get('target', dep.get('target_repo', ''))
                dep_type = dep.get('type', dep.get('dependency_type', ''))
                st.markdown(f"- **{target}** ({dep_type})")
                if dep.get('description'):
                    st.caption(dep['description'])
        
        with col2:
            st.markdown(f"#### Depended Upon By ({len(incoming)})")
            for dep in incoming:
                source = dep.get('source', dep.get('source_repo', ''))
                dep_type = dep.get('type', dep.get('dependency_type', ''))
                st.markdown(f"- **{source}** ({dep_type})")
                if dep.get('description'):
                    st.caption(dep['description'])
        
        # Generate focused graph
        st.markdown("---")
        st.markdown("#### Focused Dependency Graph")
        
        focused_deps = outgoing + incoming
        if focused_deps:
            focused_mermaid = generate_mermaid_graph(focused_deps, highlight_repo=selected_repo)
            display_markdown_with_mermaid(f"```mermaid\n{focused_mermaid}\n```")

with tab4:
    st.markdown("### Dependency Matrix")
    
    matrix_data = create_dependency_matrix(dependencies)
    
    if matrix_data['repos']:
        # Create visual matrix
        repos = matrix_data['repos']
        matrix = matrix_data['matrix']
        
        # Build dataframe
        df_matrix = pd.DataFrame(index=repos, columns=repos)
        
        for source in repos:
            for target in repos:
                deps = matrix.get(source, {}).get(target, [])
                if deps:
                    df_matrix.loc[source, target] = f"✓ ({len(deps)})"
                else:
                    df_matrix.loc[source, target] = ""
        
        st.dataframe(df_matrix, use_container_width=True)
        
        st.caption("✓ indicates dependency exists (number shows count of different dependency types)")
    else:
        st.info("No dependencies to display in matrix form.")