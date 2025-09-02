"""Overview Dashboard Page."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.memory_loader import MemoryLoader
from components.metrics_cards import display_metric_cards, display_progress_bar


st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

st.title("📊 Overview Dashboard")
st.markdown("High-level view of your migration analysis")
st.markdown("---")

# Check if data is loaded
if 'memory_data' not in st.session_state or not st.session_state.memory_data:
    st.warning("⚠️ No data loaded. Please load data from the main page.")
    st.stop()

data = st.session_state.memory_data
stats = MemoryLoader.get_summary_stats(data)

# Display metric cards
st.markdown("### 📈 Key Metrics")
display_metric_cards(stats)

# Progress Overview
st.markdown("---")
st.markdown("### 📊 Analysis Progress")

col1, col2 = st.columns(2)

with col1:
    # Insights Progress
    display_progress_bar(
        "Repositories with Insights",
        stats['repositories_with_insights'],
        stats['total_repositories']
    )
    
    # Assignment Progress
    display_progress_bar(
        "Repositories Assigned to Components",
        stats['assigned_repositories'],
        stats['total_repositories']
    )
    
    # Deep Analysis Progress (Phase 2)
    if stats['repositories_with_deep_analysis'] > 0:
        display_progress_bar(
            "Repositories with Deep Analysis",
            stats['repositories_with_deep_analysis'],
            stats['total_repositories']
        )

with col2:
    # Component Distribution Pie Chart
    if data.get('components'):
        component_sizes = []
        for comp_name, comp_data in data['components'].items():
            component_sizes.append({
                'Component': comp_name,
                'Repositories': len(comp_data.get('repositories', []))
            })
        
        df_components = pd.DataFrame(component_sizes)
        fig = px.pie(
            df_components, 
            values='Repositories', 
            names='Component',
            title='Repository Distribution by Component'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# Repository Statistics
st.markdown("---")
st.markdown("### 📦 Repository Analysis")

# Technology Stack Analysis
repos = data.get('repositories', {})
tech_stats = {}
for repo_name, repo_data in repos.items():
    for ext, count in repo_data.get('file_counts', {}).items():
        if ext:  # Skip empty extensions
            tech_stats[ext] = tech_stats.get(ext, 0) + count

if tech_stats:
    # Sort and get top 10
    sorted_tech = sorted(tech_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart of file types
        df_tech = pd.DataFrame(sorted_tech, columns=['Extension', 'Count'])
        fig = px.bar(
            df_tech, 
            x='Count', 
            y='Extension',
            orientation='h',
            title='Top 10 File Types Across All Repositories'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Repository size distribution
        repo_sizes = []
        for repo_name, repo_data in repos.items():
            repo_sizes.append({
                'Repository': repo_name,
                'Total Files': repo_data.get('total_files', 0),
                'Total Lines': repo_data.get('total_lines', 0)
            })
        
        df_sizes = pd.DataFrame(repo_sizes)
        df_sizes = df_sizes.sort_values('Total Lines', ascending=False).head(10)
        
        fig = px.bar(
            df_sizes,
            x='Total Lines',
            y='Repository',
            orientation='h',
            title='Top 10 Repositories by Lines of Code'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# Component Summary Table
if data.get('components'):
    st.markdown("---")
    st.markdown("### 🏗️ Component Summary")
    
    component_summary = []
    for comp_name, comp_data in data['components'].items():
        repo_list = comp_data.get('repositories', [])
        total_lines = sum(
            repos.get(r, {}).get('total_lines', 0) 
            for r in repo_list
        )
        component_summary.append({
            'Component': comp_name,
            'Purpose': comp_data.get('purpose', 'N/A'),
            'Repositories': len(repo_list),
            'Total Lines': total_lines
        })
    
    df_summary = pd.DataFrame(component_summary)
    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Lines": st.column_config.NumberColumn(format="%d")
        }
    )

# Timeline Information
if data.get('analysis_started'):
    st.markdown("---")
    st.markdown("### ⏱️ Analysis Timeline")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if data.get('analysis_started'):
            st.info(f"**Started:** {data['analysis_started']}")
    
    with col2:
        if data.get('analysis_completed'):
            st.info(f"**Completed:** {data['analysis_completed']}")
    
    with col3:
        if data.get('last_updated'):
            st.info(f"**Last Updated:** {data['last_updated']}")