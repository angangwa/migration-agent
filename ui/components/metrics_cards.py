"""Metrics display components."""

import streamlit as st
from typing import Dict, Any


def display_metric_cards(stats: Dict[str, Any]):
    """Display metric cards in columns."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Repositories",
            stats.get('total_repositories', 0)
        )
    
    with col2:
        st.metric(
            "Components",
            stats.get('total_components', 0)
        )
    
    with col3:
        insights = stats.get('repositories_with_insights', 0)
        total = stats.get('total_repositories', 0)
        pct = (insights / total * 100) if total > 0 else 0
        st.metric(
            "With Insights",
            insights,
            f"{pct:.0f}%"
        )
    
    with col4:
        assigned = stats.get('assigned_repositories', 0)
        total = stats.get('total_repositories', 0)
        pct = (assigned / total * 100) if total > 0 else 0
        st.metric(
            "Assigned",
            assigned,
            f"{pct:.0f}%"
        )


def display_progress_bar(label: str, value: int, total: int):
    """Display a progress bar with percentage."""
    if total == 0:
        pct = 0
    else:
        pct = value / total
    
    st.text(f"{label}: {value}/{total}")
    st.progress(pct)