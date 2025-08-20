"""
JSON Storage and Caching System

Handles persistent storage of analysis state with JSON serialization,
caching for performance, and safe concurrent access for parallel processing.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import threading
from contextlib import contextmanager

from .models import AnalysisState, RepoMetadata, ComponentData, DependencyRecord, DeepAnalysis


class DiscoveryStorage:
    """Thread-safe JSON storage for discovery analysis state."""
    
    def __init__(self, storage_dir: Path, cache_name: str = "discovery_cache.json"):
        """
        Initialize storage system.
        
        Args:
            storage_dir: Directory to store cache files
            cache_name: Name of the main cache file
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.storage_dir / cache_name
        self.backup_file = self.storage_dir / f"{cache_name}.backup"
        self.temp_file = self.storage_dir / f"{cache_name}.tmp"
        
        # Thread lock for safe concurrent access
        self._lock = threading.RLock()
        
        # In-memory cache
        self._state_cache: Optional[AnalysisState] = None
        self._cache_dirty = False
        
    def load_state(self, base_repos_path: str) -> AnalysisState:
        """
        Load analysis state from storage or create new one.
        
        Args:
            base_repos_path: Base path to repositories
            
        Returns:
            AnalysisState instance
        """
        with self._lock:
            # Return cached state if available and not dirty
            if self._state_cache is not None:
                return self._state_cache
            
            # Try to load from file
            if self.cache_file.exists():
                try:
                    state = self._load_from_file(self.cache_file)
                    # Update base path in case it changed
                    state.base_repos_path = base_repos_path
                    state.last_updated = datetime.now()
                    
                    self._state_cache = state
                    return state
                    
                except Exception as e:
                    print(f"Warning: Failed to load cache file: {e}")
                    
                    # Try backup file
                    if self.backup_file.exists():
                        try:
                            state = self._load_from_file(self.backup_file)
                            state.base_repos_path = base_repos_path
                            state.last_updated = datetime.now()
                            
                            self._state_cache = state
                            return state
                        except Exception as backup_e:
                            print(f"Warning: Failed to load backup file: {backup_e}")
            
            # Create new state if no valid cache found
            state = AnalysisState(base_repos_path=base_repos_path)
            self._state_cache = state
            self._cache_dirty = True
            
            return state
    
    def save_state(self, state: AnalysisState, force: bool = False) -> bool:
        """
        Save analysis state to storage.
        
        Args:
            state: AnalysisState to save
            force: Force save even if cache is not dirty
            
        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            if not force and not self._cache_dirty and self._state_cache == state:
                return True  # No changes to save
            
            try:
                # Update timestamps
                state.last_updated = datetime.now()
                
                # Save to temporary file first
                self._save_to_file(state, self.temp_file)
                
                # Create backup of existing file
                if self.cache_file.exists():
                    shutil.copy2(self.cache_file, self.backup_file)
                
                # Atomically replace the cache file
                shutil.move(self.temp_file, self.cache_file)
                
                # Update cache
                self._state_cache = state
                self._cache_dirty = False
                
                return True
                
            except Exception as e:
                print(f"Error saving state: {e}")
                # Clean up temp file if it exists
                if self.temp_file.exists():
                    self.temp_file.unlink()
                return False
    
    def update_repository(self, repo_name: str, metadata: RepoMetadata) -> bool:
        """
        Update a single repository's metadata in storage.
        
        Args:
            repo_name: Repository name
            metadata: Updated repository metadata
            
        Returns:
            True if updated successfully
        """
        with self._lock:
            if self._state_cache is None:
                return False
            
            self._state_cache.repositories[repo_name] = metadata
            self._state_cache.last_updated = datetime.now()
            
            # Update progress counters
            self._update_progress_counters()
            
            self._cache_dirty = True
            return True
    
    def add_component(self, component_name: str, component_data: ComponentData) -> bool:
        """
        Add a new component to storage.
        
        Args:
            component_name: Component name
            component_data: Component data
            
        Returns:
            True if added successfully
        """
        with self._lock:
            if self._state_cache is None:
                return False
            
            self._state_cache.components[component_name] = component_data
            self._state_cache.last_updated = datetime.now()
            self._cache_dirty = True
            return True
    
    def assign_repo_to_component(self, repo_name: str, component_name: str) -> bool:
        """
        Assign a repository to a component.
        
        Args:
            repo_name: Repository name
            component_name: Component name
            
        Returns:
            True if assigned successfully
        """
        with self._lock:
            if self._state_cache is None:
                return False
            
            # Update repository
            if repo_name in self._state_cache.repositories:
                repo = self._state_cache.repositories[repo_name]
                if component_name not in repo.assigned_components:
                    repo.assigned_components.append(component_name)
                    repo.update_discovery_status()
            
            # Update component
            if component_name in self._state_cache.components:
                component = self._state_cache.components[component_name]
                if repo_name not in component.repositories:
                    component.repositories.append(repo_name)
            
            self._state_cache.last_updated = datetime.now()
            self._cache_dirty = True
            return True
    
    def get_progress_summary(self) -> Optional[Dict[str, Any]]:
        """Get current analysis progress summary."""
        with self._lock:
            if self._state_cache is None:
                return None
            return self._state_cache.get_progress_summary()
    
    @contextmanager
    def batch_update(self):
        """Context manager for batch updates to avoid frequent saves."""
        with self._lock:
            old_dirty = self._cache_dirty
            try:
                yield
            finally:
                # Only mark as dirty if changes were made during batch
                if self._cache_dirty != old_dirty:
                    self._cache_dirty = True
    
    def _load_from_file(self, file_path: Path) -> AnalysisState:
        """Load AnalysisState from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert dictionaries back to model instances
        repositories = {}
        for repo_name, repo_data in data.get('repositories', {}).items():
            # Handle Phase 2 deep_analysis if present
            if 'deep_analysis' in repo_data and repo_data['deep_analysis']:
                deep_analysis_data = repo_data['deep_analysis']
                if 'analysis_timestamp' in deep_analysis_data and deep_analysis_data['analysis_timestamp']:
                    deep_analysis_data['analysis_timestamp'] = datetime.fromisoformat(deep_analysis_data['analysis_timestamp'])
                repo_data['deep_analysis'] = DeepAnalysis(**deep_analysis_data)
            
            repositories[repo_name] = RepoMetadata(**repo_data)
        
        components = {}
        for comp_name, comp_data in data.get('components', {}).items():
            if 'created_at' in comp_data and comp_data['created_at']:
                comp_data['created_at'] = datetime.fromisoformat(comp_data['created_at'])
            components[comp_name] = ComponentData(**comp_data)
        
        # Handle Phase 2 dependency_records if present
        dependency_records = []
        for dep_data in data.get('dependency_records', []):
            if 'created_at' in dep_data and dep_data['created_at']:
                dep_data['created_at'] = datetime.fromisoformat(dep_data['created_at'])
            dependency_records.append(DependencyRecord(**dep_data))
        
        # Handle timestamps in main state
        if 'analysis_started' in data and data['analysis_started']:
            data['analysis_started'] = datetime.fromisoformat(data['analysis_started'])
        if 'analysis_completed' in data and data['analysis_completed']:
            data['analysis_completed'] = datetime.fromisoformat(data['analysis_completed'])
        if 'last_updated' in data and data['last_updated']:
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Reconstruct AnalysisState
        data['repositories'] = repositories
        data['components'] = components
        data['dependency_records'] = dependency_records
        
        return AnalysisState(**data)
    
    def _save_to_file(self, state: AnalysisState, file_path: Path):
        """Save AnalysisState to JSON file."""
        
        # Convert to serializable dictionary
        data = state.model_dump()
        
        # Convert datetime objects to ISO strings
        def convert_datetime(obj):
            if isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj
        
        data = convert_datetime(data)
        
        # Write to file with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _update_progress_counters(self):
        """Update progress counters based on current repository states."""
        if self._state_cache is None:
            return
        
        total = len(self._state_cache.repositories)
        insights_count = sum(1 for repo in self._state_cache.repositories.values() 
                            if repo.insights)
        
        self._state_cache.total_repositories = total
        self._state_cache.repositories_with_insights = insights_count
    
    def clear_cache(self):
        """Clear in-memory cache to force reload from disk."""
        with self._lock:
            self._state_cache = None
            self._cache_dirty = False
    
    def backup_current_state(self, backup_name: Optional[str] = None) -> Path:
        """
        Create a timestamped backup of current state.
        
        Args:
            backup_name: Optional custom backup name
            
        Returns:
            Path to the created backup file
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"discovery_backup_{timestamp}.json"
        
        backup_path = self.storage_dir / backup_name
        
        if self.cache_file.exists():
            shutil.copy2(self.cache_file, backup_path)
        
        return backup_path
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage files."""
        info = {
            'storage_dir': str(self.storage_dir),
            'cache_file_exists': self.cache_file.exists(),
            'backup_file_exists': self.backup_file.exists(),
            'cache_dirty': self._cache_dirty,
            'in_memory_cache': self._state_cache is not None
        }
        
        if self.cache_file.exists():
            stat = self.cache_file.stat()
            info['cache_file_size'] = stat.st_size
            info['cache_file_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info