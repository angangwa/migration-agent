# Migration Agent UI

A comprehensive Streamlit dashboard for visualizing cloud migration analysis results from the AI Migration Agent.

## Features

### 📊 Overview Dashboard
- High-level metrics and statistics
- Repository and component counts
- Analysis progress tracking
- Technology stack distribution
- Timeline visualization

### 🏗️ Components Explorer
- Browse logical component groupings
- View component purposes and rationale
- Explore repository assignments
- Technology summary per component

### 📦 Repository Details
- Deep dive into individual repositories
- View Phase 1 insights and metadata
- Access Phase 2 deep analysis (when available)
- Browse file structure and technology stack
- Component assignments

### 🔗 Dependency Visualization
- Interactive dependency graphs with Mermaid
- Dependency statistics and analysis
- Circular dependency detection
- Repository focus view
- Dependency matrix

### 💬 Chat Agent (Coming Soon)
- Placeholder for future Semantic Kernel integration
- Will enable Q&A about codebase
- Context-aware responses using memory

## Installation

1. Navigate to the UI directory:
```bash
cd migration-agent/ui
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: If you want Mermaid diagram support, ensure `streamlit-markdown` is installed:
```bash
pip install streamlit-markdown
```

## Running the Application

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the displayed URL (typically http://localhost:8501)

3. Load your discovery cache:
   - Enter the path to your `discovery_cache.json` file in the sidebar
   - Default path: `../notebooks/.discovery_cache/discovery_cache.json`
   - Click "Load Data"

## Data Requirements

The UI expects a discovery cache JSON file with the following structure:

```json
{
  "repositories": {
    "repo_name": {
      "name": "...",
      "insights": {...},
      "deep_analysis": {...},  // Optional Phase 2
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
  "dependency_records": [...]  // Optional Phase 2
}
```

## Navigation Guide

### Main Page
- Load data source
- View quick stats
- Navigate to different sections

### Overview Page
- Key metrics cards
- Analysis progress bars
- Repository distribution charts
- Component summary table

### Components Page
- Select and explore components
- View assigned repositories
- Check technology stack
- Component comparison table

### Repositories Page
- Search and select repositories
- View insights and analysis
- Browse file structure
- Access markdown reports

### Dependencies Page
- View dependency graph
- Analyze relationships
- Filter by type or source
- Focus on specific repositories

## Customization

### Adjusting File Path
Edit the default path in `components/memory_loader.py`:
```python
def get_default_cache_path() -> str:
    return "your/custom/path/discovery_cache.json"
```

### Theme Configuration
Modify custom CSS in `app.py` to adjust styling:
```python
st.markdown("""
<style>
    /* Your custom styles */
</style>
""", unsafe_allow_html=True)
```

## Troubleshooting

### Data Not Loading
- Verify the JSON file path is correct
- Check file permissions
- Ensure JSON is valid format

### Mermaid Diagrams Not Rendering
- Install `streamlit-markdown`: `pip install streamlit-markdown`
- Check browser compatibility
- Try refreshing the page

### Performance Issues
- Large datasets may take time to load
- Use filters to reduce displayed data
- Consider upgrading system resources

## Development

### Project Structure
```
ui/
├── app.py                    # Main application
├── pages/                    # Multi-page structure
│   ├── 1_📊_Overview.py
│   ├── 2_🏗️_Components.py
│   ├── 3_📦_Repositories.py
│   ├── 4_🔗_Dependencies.py
│   └── 5_💬_Chat_Agent.py
├── components/               # Reusable components
│   ├── memory_loader.py
│   ├── markdown_viewer.py
│   ├── dependency_graph.py
│   └── metrics_cards.py
└── requirements.txt
```

### Adding New Pages
1. Create new file in `pages/` with format: `N_emoji_Name.py`
2. Import required components
3. Add page configuration
4. Implement functionality

### Extending Components
1. Add new functions to component modules
2. Import in relevant pages
3. Update documentation

## Future Enhancements

- [ ] Export functionality for reports
- [ ] Advanced filtering and search
- [ ] Comparison views between repositories
- [ ] Annotation and notes system
- [ ] Real-time collaboration features
- [ ] Integration with Semantic Kernel chat agent

## License

Part of the Migration Agent project.

## Support

For issues or questions, refer to the main Migration Agent documentation.