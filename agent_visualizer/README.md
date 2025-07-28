# Agent Conversation Visualizer

A comprehensive dashboard for visualizing AI agent conversation traces with observability features. This tool provides insights into agent decision-making, tool usage patterns, token consumption, and termination check logic.

## Features

### 📊 Dashboard Metrics
- **Total Messages**: Count of all conversation messages
- **Function Calls**: Number and success rate of tool invocations
- **Termination Checks**: Visualization of decision points
- **Token Usage**: Complete breakdown including cached tokens

### 💰 Token Analytics
- **Real-time Cost Calculator**: Shows actual costs vs potential costs without caching
- **Cache Efficiency**: Percentage of tokens served from cache
- **Token Timeline**: Visual representation of token usage over conversation
- **Cost Savings**: Calculated savings from cached tokens

### 🛑 Termination Timeline
- **Visual Timeline**: Interactive markers showing termination check points
- **Decision Tracking**: Shows continue/complete decisions
- **Progress Indicators**: Visual representation of conversation progress

### 🔍 Message Tracing
- **Conversation Flow**: Hierarchical view of all messages
- **Message Details**: Full content with syntax highlighting
- **Tool Call Inspector**: Arguments and results for each function call
- **Search & Filter**: Quick navigation through messages

## Installation

### Prerequisites
- Python 3.8+
- Flask 2.3+

### Setup

1. Navigate to the visualizer directory:
```bash
cd agent_visualizer
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Ensure your `agent_responses.json` file is in the parent directory (`../agent_responses.json`)

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Dashboard Interface

### Layout
- **Header**: Real-time metrics display
- **Left Sidebar**: Conversation flow with message types
- **Main Content**: 
  - Token analytics with charts
  - Termination timeline
  - Selected message details

### Message Types
- 🤖 **Assistant**: Agent reasoning messages
- 🔧 **Function Call**: Tool invocations
- 📤 **Function Result**: Tool responses
- 🛑 **Termination Check**: Decision points

### Interactive Features
- Click any message in the sidebar to view details
- Hover over termination markers for quick info
- Use search to filter messages
- Charts update in real-time

## Data Format

The visualizer expects `agent_responses.json` with the following structure:

```json
[
  {
    "role": "assistant",
    "metadata": {
      "usage": {
        "prompt_tokens": 1000,
        "prompt_tokens_details": {
          "cached_tokens": 500
        },
        "completion_tokens": 200
      }
    },
    "items": [...]
  },
  {
    "role": "termination_check",
    "content": "Check reason...",
    "should_terminate": false
  }
]
```

## Customization

### Modify Token Pricing
Edit `utils/token_analyzer.py`:
```python
self.cost_per_1k_prompt = 0.00025  # Your pricing
self.cost_per_1k_completion = 0.00125  # Your pricing
```

### Add New Message Types
1. Update `utils/data_processor.py` to handle new types
2. Add icons in `static/js/dashboard.js`
3. Add styling in `static/css/dashboard.css`

## Troubleshooting

### Common Issues

1. **"Failed to load conversation data"**
   - Check that `agent_responses.json` exists in the parent directory
   - Verify the JSON file is valid

2. **Charts not displaying**
   - Ensure JavaScript is enabled
   - Check browser console for errors

3. **Missing token data**
   - Verify your agent responses include metadata with usage information

## Development

### Project Structure
```
agent_visualizer/
├── app.py                 # Flask backend
├── templates/
│   └── dashboard.html     # Main UI template
├── static/
│   ├── css/
│   │   └── dashboard.css  # Styling
│   └── js/
│       └── dashboard.js   # Frontend logic
└── utils/
    ├── data_processor.py  # JSON parsing
    └── token_analyzer.py  # Token metrics
```

### Adding Features
1. Backend: Add new routes in `app.py`
2. Processing: Extend `DataProcessor` or `TokenAnalyzer`
3. Frontend: Update `dashboard.js` and `dashboard.html`

## License

This project is part of the LSEG Migration Agent toolkit.