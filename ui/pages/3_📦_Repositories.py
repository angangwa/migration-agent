"""Repositories Detail Viewer Page."""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.markdown_viewer import (
    display_markdown_with_mermaid,
    create_collapsible_section
)


st.set_page_config(page_title="Repositories", page_icon="📦", layout="wide")

st.title("📦 Repository Details")
st.markdown("Deep dive into individual repository analysis")
st.markdown("---")

# Check if data is loaded
if 'memory_data' not in st.session_state or not st.session_state.memory_data:
    st.warning("⚠️ No data loaded. Please load data from the main page.")
    st.stop()

data = st.session_state.memory_data
repos = data.get('repositories', {})

if not repos:
    st.info("No repositories found in the data.")
    st.stop()

# Repository selector
st.markdown("### 🔍 Select Repository")

# Create searchable list with additional info
repo_options = []
for repo_name, repo_data in repos.items():
    lines = repo_data.get('total_lines', 0)
    has_insights = '✅' if repo_data.get('insights') else '❌'
    has_deep = '🔬' if repo_data.get('deep_analysis') else ''
    repo_options.append(f"{repo_name} ({lines:,} lines) {has_insights} {has_deep}")

# Extract just the repo name from selection
selected_option = st.selectbox(
    "Choose a repository to explore:",
    repo_options,
    help="✅ = Has insights, 🔬 = Has deep analysis"
)

if selected_option:
    # Extract repo name from the formatted string
    selected_repo = selected_option.split(' (')[0]
    repo_data = repos[selected_repo]
    
    # Repository header
    st.markdown(f"## {selected_repo}")
    
    # Basic metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", repo_data.get('total_files', 0))
    
    with col2:
        st.metric("Total Lines", f"{repo_data.get('total_lines', 0):,}")
    
    with col3:
        components = repo_data.get('assigned_components', [])
        st.metric("Components", len(components))
    
    with col4:
        status = []
        if repo_data.get('insights'):
            status.append("✅ Insights")
        if repo_data.get('deep_analysis'):
            status.append("🔬 Deep Analysis")
        st.metric("Analysis", " | ".join(status) if status else "❌ None")
    
    # Tabbed interface for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "💡 Insights", 
        "🔬 Deep Analysis",
        "📁 File Structure",
        "🏗️ Components"
    ])
    
    with tab1:
        st.markdown("### Repository Overview")
        
        # Status
        st.markdown(f"**Discovery Status:** {repo_data.get('discovery_phase_status', 'Unknown')}")
        
        # File type distribution
        if repo_data.get('file_counts'):
            st.markdown("### File Type Distribution")
            
            file_counts = repo_data['file_counts']
            df_files = pd.DataFrame(
                list(file_counts.items()),
                columns=['Extension', 'Count']
            )
            df_files = df_files.sort_values('Count', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(df_files, use_container_width=True, hide_index=True)
            
            with col2:
                # Show as bar chart
                st.bar_chart(df_files.set_index('Extension')['Count'])
        
        # Technology stack
        if repo_data.get('technology_stack', {}).get('frameworks'):
            st.markdown("### Detected Frameworks")
            frameworks = repo_data['technology_stack']['frameworks']
            for fw in frameworks:
                st.markdown(f"- {fw}")
        
        # Configuration files
        if repo_data.get('config_files'):
            st.markdown("### Configuration Files")
            for cf in repo_data['config_files']:
                st.markdown(f"- {cf}")
    
    with tab2:
        st.markdown("### Repository Insights")
        
        insights = repo_data.get('insights', {})
        if insights:
            # Purpose
            if insights.get('purpose'):
                create_collapsible_section(
                    "🎯 Purpose",
                    insights['purpose'],
                    expanded=True
                )
            
            # Business Function
            if insights.get('business_function'):
                create_collapsible_section(
                    "💼 Business Function",
                    insights['business_function'],
                    expanded=True
                )
            
            # Architecture
            if insights.get('architecture'):
                create_collapsible_section(
                    "🏛️ Architecture",
                    insights['architecture'],
                    expanded=True
                )
            
            # Key Dependencies
            if insights.get('key_dependencies'):
                deps = insights['key_dependencies']
                if isinstance(deps, list):
                    deps_text = "\n".join([f"- {d}" for d in deps])
                else:
                    deps_text = str(deps)
                
                create_collapsible_section(
                    "📦 Key Dependencies",
                    deps_text,
                    expanded=False
                )
            
            # Notes
            if insights.get('notes'):
                create_collapsible_section(
                    "📝 Notes",
                    insights['notes'],
                    expanded=False
                )
            
            # Raw JSON view
            with st.expander("🔧 Raw Insights JSON"):
                st.json(insights)
        else:
            st.info("No insights available for this repository.")
    
    with tab3:
        st.markdown("### Deep Analysis (Phase 2)")
        
        deep_analysis = repo_data.get('deep_analysis')
        if deep_analysis:
            # Markdown report
            if deep_analysis.get('markdown_summary'):
                st.markdown("#### 📄 Analysis Report")
                display_markdown_with_mermaid(deep_analysis['markdown_summary'])
            
            # Deep insights
            if deep_analysis.get('deep_insights'):
                st.markdown("#### 🔍 Deep Insights")
                
                for key, value in deep_analysis['deep_insights'].items():
                    if isinstance(value, list):
                        value_str = "\n".join([f"- {v}" for v in value])
                    elif isinstance(value, dict):
                        value_str = json.dumps(value, indent=2)
                    else:
                        value_str = str(value)
                    
                    create_collapsible_section(
                        key.replace('_', ' ').title(),
                        value_str
                    )
            
            # Analysis timestamp
            if deep_analysis.get('analysis_timestamp'):
                st.info(f"Analysis performed: {deep_analysis['analysis_timestamp']}")
        else:
            st.info("No deep analysis available for this repository.")
            st.markdown("""
            Deep analysis is performed in Phase 2 and includes:
            - Comprehensive markdown reports
            - Detailed architectural insights
            - Cloud service mappings
            - Migration recommendations
            """)
    
    with tab4:
        st.markdown("### File Structure Analysis")
        
        # File statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Statistics")
            st.markdown(f"- **Total Files:** {repo_data.get('total_files', 0)}")
            st.markdown(f"- **Total Lines:** {repo_data.get('total_lines', 0):,}")
            st.markdown(f"- **Has README:** {'✅' if repo_data.get('has_readme') else '❌'}")
        
        with col2:
            st.markdown("#### 📁 File Types")
            if repo_data.get('file_counts'):
                for ext, count in sorted(
                    repo_data['file_counts'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]:
                    ext_display = ext if ext else "(no extension)"
                    st.markdown(f"- `{ext_display}`: {count} files")
    
    with tab5:
        st.markdown("### Component Assignments")
        
        components = repo_data.get('assigned_components', [])
        if components:
            for comp_name in components:
                comp_data = data.get('components', {}).get(comp_name)
                if comp_data:
                    with st.expander(f"🏗️ {comp_name}"):
                        st.markdown(f"**Purpose:** {comp_data.get('purpose', 'N/A')}")
                        st.markdown(f"**Rationale:** {comp_data.get('rationale', 'N/A')}")
                        
                        # Show other repos in this component
                        other_repos = [
                            r for r in comp_data.get('repositories', [])
                            if r != selected_repo
                        ]
                        if other_repos:
                            st.markdown("**Other repositories in this component:**")
                            for r in other_repos:
                                st.markdown(f"- {r}")
        else:
            st.info("This repository is not assigned to any components.")