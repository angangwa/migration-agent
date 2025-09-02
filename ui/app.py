"""Migration Agent UI - Main Application."""

import streamlit as st
from pathlib import Path
from components.memory_loader import MemoryLoader


# Page configuration
st.set_page_config(
    page_title="Migration Agent UI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'memory_data' not in st.session_state:
    st.session_state.memory_data = None
if 'cache_path' not in st.session_state:
    st.session_state.cache_path = MemoryLoader.get_default_cache_path()

# Main title
st.title("🚀 Migration Agent Analysis Dashboard")
st.markdown("---")

# Sidebar for file selection
with st.sidebar:
    st.header("📁 Data Source")
    
    # File path input
    cache_path = st.text_input(
        "Discovery Cache Path",
        value=st.session_state.cache_path,
        help="Path to discovery_cache.json file"
    )
    
    # Load button
    if st.button("Load Data", type="primary"):
        with st.spinner("Loading discovery cache..."):
            data = MemoryLoader.load_discovery_cache(cache_path)
            if data and MemoryLoader.validate_data(data):
                st.session_state.memory_data = data
                st.session_state.cache_path = cache_path
                st.success("✅ Data loaded successfully!")
            else:
                st.error("Failed to load or validate data")
    
    # Display load status
    if st.session_state.memory_data:
        st.success("✅ Data Loaded")
        stats = MemoryLoader.get_summary_stats(st.session_state.memory_data)
        st.markdown("### 📊 Quick Stats")
        st.metric("Repositories", stats['total_repositories'])
        st.metric("Components", stats['total_components'])
        if stats['has_dependencies']:
            st.info("📎 Dependencies available")
    else:
        st.warning("⚠️ No data loaded")

# Main content area
if st.session_state.memory_data:
    st.markdown("""
    ## Welcome to Migration Agent UI
    
    This dashboard provides comprehensive visualization of your application's migration analysis.
    
    ### 🧭 Navigation Guide
    
    Use the sidebar pages to explore:
    
    - **📊 Overview** - High-level metrics and progress tracking
    - **🏗️ Components** - Logical component groupings and their repositories
    - **📦 Repositories** - Detailed repository analysis and insights
    - **🔗 Dependencies** - Visualize inter-repository relationships
    - **💬 Chat Agent** - (Coming Soon) AI-powered Q&A about your codebase
    
    ### 📝 Data Structure
    
    Your discovery cache contains:
    """)
    
    stats = MemoryLoader.get_summary_stats(st.session_state.memory_data)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        - **{stats['total_repositories']}** repositories discovered
        - **{stats['repositories_with_insights']}** repositories with insights
        - **{stats['repositories_with_deep_analysis']}** repositories with deep analysis
        """)
    
    with col2:
        st.markdown(f"""
        - **{stats['total_components']}** logical components
        - **{stats['assigned_repositories']}** repositories assigned
        - **{stats['unassigned_repositories']}** repositories unassigned
        """)
    
    if stats['has_dependencies']:
        st.info("🔗 Dependency data is available for visualization")
    
    st.markdown("---")
    st.markdown("### 🚀 Getting Started")
    st.markdown("""
    1. Navigate to **Overview** for a high-level summary
    2. Explore **Components** to understand logical groupings
    3. Dive into **Repositories** for detailed analysis
    4. Visualize **Dependencies** to understand relationships
    """)
    
else:
    # Welcome screen when no data is loaded
    st.markdown("""
    ## 👋 Welcome to Migration Agent UI
    
    This application visualizes the analysis results from your AI migration agent.
    
    ### 🚀 Getting Started
    
    1. Enter the path to your `discovery_cache.json` file in the sidebar
    2. Click **Load Data** to import your analysis
    3. Navigate through the pages to explore your data
    
    ### 📍 Default Path
    
    The default path is set to:
    ```
    ../notebooks/.discovery_cache/discovery_cache.json
    ```
    
    Adjust this path if your cache file is located elsewhere.
    """)
    
    # Example of expected structure
    with st.expander("📖 Expected Data Structure"):
        st.markdown("""
        The discovery cache should contain:
        
        ```json
        {
            "repositories": {
                "repo_name": {
                    "name": "...",
                    "insights": {...},
                    "deep_analysis": {...},
                    "assigned_components": [...]
                }
            },
            "components": {
                "component_name": {
                    "name": "...",
                    "purpose": "...",
                    "repositories": [...]
                }
            },
            "dependency_records": [...]  // Optional
        }
        ```
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.85em;'>
    Migration Agent UI v1.0 | Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True
)