"""Components Explorer Page."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))


st.set_page_config(page_title="Components", page_icon="🏗️", layout="wide")

st.title("🏗️ Components Explorer")
st.markdown("Explore logical component groupings and their repositories")
st.markdown("---")

# Check if data is loaded
if 'memory_data' not in st.session_state or not st.session_state.memory_data:
    st.warning("⚠️ No data loaded. Please load data from the main page.")
    st.stop()

data = st.session_state.memory_data
components = data.get('components', {})
repos = data.get('repositories', {})

if not components:
    st.info("No components found in the data.")
    st.stop()

# Component selector
st.markdown("### 🎯 Select Component")
component_names = list(components.keys())
selected_component = st.selectbox(
    "Choose a component to explore:",
    component_names,
    format_func=lambda x: f"{x} ({len(components[x].get('repositories', []))} repos)"
)

if selected_component:
    comp_data = components[selected_component]
    
    # Component header
    st.markdown(f"## {selected_component}")
    
    # Component details in columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Component Details")
        st.markdown(f"**Purpose:** {comp_data.get('purpose', 'N/A')}")
        st.markdown(f"**Rationale:** {comp_data.get('rationale', 'N/A')}")
        
        if comp_data.get('created_at'):
            st.markdown(f"**Created:** {comp_data['created_at']}")
    
    with col2:
        st.metric("Repositories", len(comp_data.get('repositories', [])))
        
        # Calculate total lines
        total_lines = sum(
            repos.get(r, {}).get('total_lines', 0) 
            for r in comp_data.get('repositories', [])
        )
        st.metric("Total Lines", f"{total_lines:,}")
    
    # Repository list
    st.markdown("---")
    st.markdown("### 📦 Assigned Repositories")
    
    repo_list = comp_data.get('repositories', [])
    if repo_list:
        # Create detailed table
        repo_details = []
        for repo_name in repo_list:
            repo_data = repos.get(repo_name, {})
            
            # Get primary language/tech
            file_counts = repo_data.get('file_counts', {})
            primary_ext = max(file_counts.items(), key=lambda x: x[1])[0] if file_counts else 'N/A'
            
            repo_details.append({
                'Repository': repo_name,
                'Total Files': repo_data.get('total_files', 0),
                'Total Lines': repo_data.get('total_lines', 0),
                'Primary Type': primary_ext,
                'Has Insights': '✅' if repo_data.get('insights') else '❌',
                'Has Deep Analysis': '✅' if repo_data.get('deep_analysis') else '❌'
            })
        
        df_repos = pd.DataFrame(repo_details)
        
        # Display as expandable cards
        for _, row in df_repos.iterrows():
            repo_name = row['Repository']
            repo_data = repos.get(repo_name, {})
            
            with st.expander(f"📦 **{repo_name}** - {row['Total Lines']:,} lines"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Statistics:**")
                    st.markdown(f"- Files: {row['Total Files']}")
                    st.markdown(f"- Lines: {row['Total Lines']:,}")
                    st.markdown(f"- Primary Type: {row['Primary Type']}")
                
                with col2:
                    st.markdown("**Analysis Status:**")
                    st.markdown(f"- Insights: {row['Has Insights']}")
                    st.markdown(f"- Deep Analysis: {row['Has Deep Analysis']}")
                
                # Show insights if available
                if repo_data.get('insights'):
                    st.markdown("---")
                    st.markdown("**Insights:**")
                    insights = repo_data['insights']
                    
                    if insights.get('purpose'):
                        st.markdown(f"**Purpose:** {insights['purpose']}")
                    
                    if insights.get('business_function'):
                        st.markdown(f"**Business Function:** {insights['business_function']}")
                    
                    if insights.get('architecture'):
                        st.markdown(f"**Architecture:** {insights['architecture']}")
                    
                    if insights.get('key_dependencies'):
                        deps = insights['key_dependencies']
                        if isinstance(deps, list):
                            st.markdown(f"**Key Dependencies:** {', '.join(deps)}")
    else:
        st.info("No repositories assigned to this component.")

# Component comparison
st.markdown("---")
st.markdown("### 📊 All Components Overview")

# Create summary table
component_comparison = []
for comp_name, comp_data in components.items():
    repo_list = comp_data.get('repositories', [])
    
    # Calculate metrics
    total_repos = len(repo_list)
    total_lines = sum(
        repos.get(r, {}).get('total_lines', 0) 
        for r in repo_list
    )
    repos_with_insights = sum(
        1 for r in repo_list 
        if repos.get(r, {}).get('insights')
    )
    
    component_comparison.append({
        'Component': comp_name,
        'Repositories': total_repos,
        'Total Lines': total_lines,
        'With Insights': f"{repos_with_insights}/{total_repos}",
        'Purpose': comp_data.get('purpose', 'N/A')[:50] + '...' 
                   if len(comp_data.get('purpose', 'N/A')) > 50 
                   else comp_data.get('purpose', 'N/A')
    })

df_comparison = pd.DataFrame(component_comparison)
st.dataframe(
    df_comparison,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Total Lines": st.column_config.NumberColumn(format="%d"),
        "Purpose": st.column_config.TextColumn(width="large")
    }
)