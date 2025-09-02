"""Memory loader component for discovery cache."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st


class MemoryLoader:
    """Handles loading and caching of discovery memory data."""
    
    @staticmethod
    @st.cache_data
    def load_discovery_cache(file_path: str) -> Optional[Dict[str, Any]]:
        """Load discovery cache from JSON file."""
        try:
            path = Path(file_path)
            if not path.exists():
                st.error(f"File not found: {file_path}")
                return None
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            return data
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    
    @staticmethod
    def get_default_cache_path() -> str:
        """Get default cache file path."""
        return "../notebooks/.discovery_cache/discovery_cache.json"
    
    @staticmethod
    def validate_data(data: Dict[str, Any]) -> bool:
        """Validate required fields exist in data."""
        required_fields = ['repositories', 'components']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def get_summary_stats(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary statistics from data."""
        if not data:
            return {}
        
        repos = data.get('repositories', {})
        components = data.get('components', {})
        
        # Count repos with insights
        repos_with_insights = sum(
            1 for r in repos.values() 
            if r.get('insights')
        )
        
        # Count repos with deep analysis
        repos_with_deep_analysis = sum(
            1 for r in repos.values() 
            if r.get('deep_analysis')
        )
        
        # Count assigned repos
        assigned_repos = sum(
            1 for r in repos.values() 
            if r.get('assigned_components')
        )
        
        return {
            'total_repositories': len(repos),
            'total_components': len(components),
            'repositories_with_insights': repos_with_insights,
            'repositories_with_deep_analysis': repos_with_deep_analysis,
            'assigned_repositories': assigned_repos,
            'unassigned_repositories': len(repos) - assigned_repos,
            'has_dependencies': 'dependency_records' in data
        }