"""Markdown viewer component with Mermaid support."""

import streamlit as st
from typing import Optional


def display_markdown(content: str, title: Optional[str] = None):
    """Display markdown content with proper formatting."""
    if title:
        st.markdown(f"### {title}")
    
    # Basic markdown rendering (Mermaid requires streamlit-markdown)
    st.markdown(content)


def display_markdown_with_mermaid(content: str, title: Optional[str] = None):
    """Display markdown with Mermaid diagram support."""
    try:
        from streamlit_markdown import st_markdown
        
        if title:
            st.markdown(f"### {title}")
        
        # Use streamlit-markdown for enhanced rendering
        st_markdown(content, theme="light")
    except ImportError:
        # Fallback to basic markdown if streamlit-markdown not installed
        st.warning("Install 'streamlit-markdown' for Mermaid diagram support")
        display_markdown(content, title)


def format_code_block(code: str, language: str = "python"):
    """Format code with syntax highlighting."""
    return f"```{language}\n{code}\n```"


def create_collapsible_section(title: str, content: str, expanded: bool = False):
    """Create a collapsible section for long content."""
    with st.expander(title, expanded=expanded):
        st.markdown(content)