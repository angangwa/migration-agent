"""
Agent Conversation Visualizer
A Flask application to visualize agent conversation traces with observability features.
"""

from flask import Flask, render_template, jsonify, request
import json
import os
from pathlib import Path
from datetime import datetime
from utils.data_processor import DataProcessor
from utils.token_analyzer import TokenAnalyzer

app = Flask(__name__)

# Configuration
AGENT_RESPONSES_FILE = Path(__file__).parent.parent / "agent_responses.json"

@app.route('/')
def dashboard():
    """Render the main dashboard."""
    return render_template('dashboard.html')

@app.route('/api/conversation')
def get_conversation():
    """Get the processed conversation data."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        data = processor.process_conversation()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics')
def get_metrics():
    """Get conversation metrics and statistics."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        analyzer = TokenAnalyzer()
        
        messages = processor.load_messages()
        loops = processor.group_by_tool_loops(messages)
        
        metrics = {
            'total_messages': len(messages),
            'message_types': processor.count_message_types(messages),
            'token_metrics': analyzer.calculate_metrics(messages),
            'tool_usage': processor.analyze_tool_usage(messages),
            'termination_checks': processor.analyze_termination_checks(messages),
            'timeline': processor.create_timeline(messages),
            'loop_metrics': processor.analyze_loop_metrics(loops)
        }
        
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/message/<int:index>')
def get_message(index):
    """Get a specific message by index."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        messages = processor.load_messages()
        
        if 0 <= index < len(messages):
            return jsonify(processor.format_message(messages[index], index))
        else:
            return jsonify({'error': 'Message index out of range'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/token-timeline')
def get_token_timeline():
    """Get token usage timeline data for visualization."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        analyzer = TokenAnalyzer()
        
        messages = processor.load_messages()
        timeline_data = analyzer.create_token_timeline(messages)
        
        return jsonify(timeline_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/loops')
def get_loops():
    """Get loop-grouped conversation data."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        messages = processor.load_messages()
        loops = processor.group_by_tool_loops(messages)
        
        return jsonify({'loops': loops})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/loop/<int:loop_id>')
def get_loop(loop_id):
    """Get a specific loop by ID."""
    try:
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        messages = processor.load_messages()
        loops = processor.group_by_tool_loops(messages)
        
        if 0 <= loop_id < len(loops):
            return jsonify(loops[loop_id])
        else:
            return jsonify({'error': 'Loop ID out of range'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-pricing', methods=['POST'])
def update_pricing():
    """Update token pricing configuration."""
    try:
        data = request.json
        prompt_cost = float(data.get('prompt_cost', 1.10))
        cached_prompt_cost = float(data.get('cached_prompt_cost', 0.275))
        completion_cost = float(data.get('completion_cost', 4.40))
        
        # Create analyzer with new pricing and recalculate metrics
        analyzer = TokenAnalyzer(prompt_cost, cached_prompt_cost, completion_cost)
        processor = DataProcessor(AGENT_RESPONSES_FILE)
        messages = processor.load_messages()
        
        updated_metrics = analyzer.calculate_metrics(messages)
        
        return jsonify({
            'success': True,
            'token_metrics': updated_metrics,
            'message': 'Pricing updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)