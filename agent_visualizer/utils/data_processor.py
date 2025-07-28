"""
Data Processor for Agent Responses
Parses and processes the agent_responses.json file for visualization.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

class DataProcessor:
    def __init__(self, json_file_path: Path):
        self.json_file_path = json_file_path
    
    def load_messages(self) -> List[Dict[str, Any]]:
        """Load messages from the JSON file."""
        with open(self.json_file_path, 'r') as f:
            return json.load(f)
    
    def process_conversation(self) -> Dict[str, Any]:
        """Process the entire conversation for visualization."""
        messages = self.load_messages()
        
        # Create a simplified structure for the frontend
        processed_messages = []
        for idx, msg in enumerate(messages):
            processed_msg = self.format_message(msg, idx)
            processed_messages.append(processed_msg)
        
        # Group messages by tool calling loops
        loops = self.group_by_tool_loops(messages)
        
        return {
            'messages': processed_messages,
            'loops': loops,
            'total_count': len(messages),
            'total_loops': len(loops),
            'message_types': self.count_message_types(messages)
        }
    
    def format_message(self, message: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Format a single message for display."""
        formatted = {
            'index': index,
            'role': message.get('role', ''),
            'type': self._get_message_type(message),
            'summary': self._create_summary(message),
            'timestamp': message.get('metadata', {}).get('created', None)
        }
        
        # Handle different message types
        if message.get('role') == 'assistant':
            formatted['name'] = message.get('name', '')
            formatted['token_usage'] = message.get('metadata', {}).get('usage', {})
            formatted['items'] = message.get('items', [])
            
            # Extract content from items if available
            content = message.get('content', '')
            items = message.get('items', [])
            if not content and items:
                # Look for text content in items
                for item in items:
                    if item.get('content_type') == 'text' and item.get('text'):
                        content = item.get('text')
                        break
            formatted['content'] = content
            
        elif message.get('role') == 'tool':
            formatted['name'] = message.get('name', '')
            formatted['items'] = message.get('items', [])
            
        elif message.get('role') == 'termination_check':
            formatted['should_terminate'] = message.get('should_terminate', False)
            formatted['content'] = message.get('content', '')
            
        return formatted
    
    def _get_message_type(self, message: Dict[str, Any]) -> str:
        """Determine the message type for display."""
        role = message.get('role', '')
        
        if role == 'termination_check':
            return 'termination'
        
        if role == 'assistant':
            items = message.get('items', [])
            if items and items[0].get('content_type') == 'function_call':
                return 'function_call'
            return 'assistant'
        
        if role == 'tool':
            return 'function_result'
        
        return role
    
    def _create_summary(self, message: Dict[str, Any]) -> str:
        """Create a short summary of the message."""
        msg_type = self._get_message_type(message)
        
        if msg_type == 'termination':
            should_terminate = message.get('should_terminate', False)
            return f"Termination Check: {'✅ Complete' if should_terminate else '❌ Continue'}"
        
        if msg_type == 'function_call':
            items = message.get('items', [])
            if items:
                func_name = items[0].get('name', 'Unknown')
                return f"🔧 Calling: {func_name}"
        
        if msg_type == 'function_result':
            items = message.get('items', [])
            if items:
                func_name = items[0].get('name', 'Unknown')
                result = items[0].get('result', '')
                success = 'success' in str(result).lower()
                return f"📤 Result: {func_name} {'✅' if success else '❌'}"
        
        if msg_type == 'assistant':
            content = message.get('content', '')
            # If no direct content, extract from items
            if not content:
                items = message.get('items', [])
                for item in items:
                    if item.get('content_type') == 'text' and item.get('text'):
                        content = item.get('text')
                        break
            
            if content:
                return content[:100] + '...' if len(content) > 100 else content
            else:
                return "Assistant message (no text content)"
        
        return f"{msg_type.title()} message"
    
    def count_message_types(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count messages by type."""
        counts = defaultdict(int)
        for msg in messages:
            msg_type = self._get_message_type(msg)
            counts[msg_type] += 1
        return dict(counts)
    
    def analyze_tool_usage(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tool usage patterns including verbosity metrics."""
        tool_calls = defaultdict(int)
        tool_results = defaultdict(lambda: {'success': 0, 'failure': 0})
        tool_verbosity = defaultdict(list)  # Store result lengths for each tool
        
        for msg in messages:
            if msg.get('role') == 'assistant':
                items = msg.get('items', [])
                for item in items:
                    if item.get('content_type') == 'function_call':
                        tool_name = item.get('function_name', 'unknown')
                        tool_calls[tool_name] += 1
            
            elif msg.get('role') == 'tool':
                items = msg.get('items', [])
                for item in items:
                    if item.get('content_type') == 'function_result':
                        tool_name = item.get('function_name', 'unknown')
                        result = item.get('result', '')
                        result_str = str(result)
                        
                        # Track verbosity (character count)
                        tool_verbosity[tool_name].append(len(result_str))
                        
                        # Track success/failure (handle both Python dict and JSON formats)
                        success_indicators = [
                            "'success': True",
                            '"success": True', 
                            "'success': true",
                            '"success": true'
                        ]
                        if any(indicator in result_str for indicator in success_indicators):
                            tool_results[tool_name]['success'] += 1
                        else:
                            tool_results[tool_name]['failure'] += 1
        
        # Calculate verbosity statistics
        verbosity_stats = {}
        for tool, lengths in tool_verbosity.items():
            if lengths:
                verbosity_stats[tool] = {
                    'avg_chars': sum(lengths) / len(lengths),
                    'min_chars': min(lengths),
                    'max_chars': max(lengths),
                    'total_chars': sum(lengths),
                    'avg_tokens_est': sum(lengths) / len(lengths) / 4,  # Rough token estimate
                    'result_count': len(lengths)
                }
        
        # Create combined tool analysis
        tool_analysis = []
        for tool in set(list(tool_calls.keys()) + list(tool_results.keys())):
            calls = tool_calls.get(tool, 0)
            results = tool_results.get(tool, {'success': 0, 'failure': 0})
            verbosity = verbosity_stats.get(tool, {})
            
            total_results = results['success'] + results['failure']
            success_rate = (results['success'] / total_results * 100) if total_results > 0 else 0
            
            tool_analysis.append({
                'name': tool,
                'calls': calls,
                'success': results['success'],
                'failure': results['failure'],
                'success_rate': round(success_rate, 1),
                'avg_chars': round(verbosity.get('avg_chars', 0)),
                'min_chars': verbosity.get('min_chars', 0),
                'max_chars': verbosity.get('max_chars', 0),
                'avg_tokens_est': round(verbosity.get('avg_tokens_est', 0)),
                'total_chars': verbosity.get('total_chars', 0)
            })
        
        # Sort by number of calls (most used first)
        tool_analysis.sort(key=lambda x: x['calls'], reverse=True)
        
        return {
            'calls_by_tool': dict(tool_calls),
            'results_by_tool': dict(tool_results),
            'total_calls': sum(tool_calls.values()),
            'verbosity_stats': verbosity_stats,
            'tool_analysis': tool_analysis
        }
    
    def analyze_termination_checks(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze termination check patterns."""
        checks = []
        
        for idx, msg in enumerate(messages):
            if msg.get('role') == 'termination_check':
                checks.append({
                    'index': idx,
                    'should_terminate': msg.get('should_terminate', False),
                    'reason': msg.get('content', ''),
                    'position_percent': (idx / len(messages)) * 100
                })
        
        return {
            'total_checks': len(checks),
            'checks': checks,
            'final_decision': checks[-1]['should_terminate'] if checks else None
        }
    
    def create_timeline(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create a timeline of key events."""
        timeline = []
        
        for idx, msg in enumerate(messages):
            msg_type = self._get_message_type(msg)
            
            # Include key events in timeline
            if msg_type in ['termination', 'function_call', 'function_result'] or idx == 0 or idx == len(messages) - 1:
                timeline.append({
                    'index': idx,
                    'type': msg_type,
                    'summary': self._create_summary(msg),
                    'timestamp': msg.get('metadata', {}).get('created', None)
                })
        
        return timeline
    
    def group_by_tool_loops(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group messages by tool calling loops.
        
        A loop consists of:
        1. Function calls (assistant messages with function_call items)
        2. Function results (tool messages)
        3. Ends when we hit a termination_check or next assistant message without function calls
        """
        loops = []
        current_loop = []
        loop_id = 0
        in_tool_loop = False
        
        for idx, msg in enumerate(messages):
            msg_type = self._get_message_type(msg)
            formatted_msg = self.format_message(msg, idx)
            
            # Start of a new tool loop
            if msg_type == 'function_call':
                if not in_tool_loop:
                    # Starting a new loop
                    if current_loop:  # Save previous loop if exists
                        loops.append(self._finalize_loop(current_loop, loop_id))
                        loop_id += 1
                        current_loop = []
                    in_tool_loop = True
                current_loop.append(formatted_msg)
                
            # Function results are part of current loop
            elif msg_type == 'function_result' and in_tool_loop:
                current_loop.append(formatted_msg)
                
            # End of tool loop - termination check or assistant message without function calls
            elif msg_type == 'termination' or (msg_type == 'assistant' and in_tool_loop):
                if in_tool_loop:
                    current_loop.append(formatted_msg)
                    loops.append(self._finalize_loop(current_loop, loop_id))
                    loop_id += 1
                    current_loop = []
                    in_tool_loop = False
                else:
                    # Standalone message (not part of a loop)
                    if current_loop:
                        loops.append(self._finalize_loop(current_loop, loop_id))
                        loop_id += 1
                    current_loop = [formatted_msg]
                    
            # Other messages (standalone assistant messages, etc.)
            else:
                if in_tool_loop:
                    # This shouldn't happen in normal flow, but handle gracefully
                    current_loop.append(formatted_msg)
                else:
                    current_loop.append(formatted_msg)
        
        # Handle any remaining messages
        if current_loop:
            loops.append(self._finalize_loop(current_loop, loop_id))
            
        return loops
    
    def _finalize_loop(self, messages: List[Dict[str, Any]], loop_id: int) -> Dict[str, Any]:
        """Finalize a loop with aggregated metrics."""
        if not messages:
            return {}
            
        # Count message types in this loop
        type_counts = {}
        tool_calls = []
        total_tokens = 0
        total_cached_tokens = 0
        total_completion_tokens = 0
        
        for msg in messages:
            msg_type = msg.get('type', '')
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
            
            # Extract tool information
            if msg_type == 'function_call':
                items = msg.get('items', [])
                for item in items:
                    if item.get('content_type') == 'function_call':
                        tool_calls.append(item.get('name', 'unknown'))
            
            # Aggregate token usage
            token_usage = msg.get('token_usage', {})
            if token_usage:
                total_tokens += token_usage.get('prompt_tokens', 0) + token_usage.get('completion_tokens', 0)
                
                prompt_details = token_usage.get('prompt_tokens_details', {})
                total_cached_tokens += prompt_details.get('cached_tokens', 0)
                total_completion_tokens += token_usage.get('completion_tokens', 0)
        
        # Determine loop type
        has_function_calls = any(msg.get('type') == 'function_call' for msg in messages)
        has_termination = any(msg.get('type') == 'termination' for msg in messages)
        
        if has_termination and not has_function_calls:
            loop_type = 'termination_check'
        elif has_function_calls:
            loop_type = 'tool_loop'
            if has_termination:
                loop_type += '_with_check'
        else:
            loop_type = 'reasoning'
            
        # Create summary based on loop content
        if has_termination and not has_function_calls:
            # This is primarily a termination check
            termination_msg = next((msg for msg in messages if msg.get('type') == 'termination'), None)
            if termination_msg:
                decision = "Complete" if termination_msg.get('should_terminate') else "Continue"
                summary = f"Termination Check: {decision}"
            else:
                summary = "Termination Check"
        elif has_function_calls:
            unique_tools = list(set(tool_calls))
            summary = f"Tool Loop: {len(tool_calls)} calls to {len(unique_tools)} tools"
            if len(unique_tools) <= 3:
                summary += f" ({', '.join(unique_tools)})"
            
            # Add termination result if present
            if has_termination:
                termination_msg = next((msg for msg in messages if msg.get('type') == 'termination'), None)
                if termination_msg:
                    decision = "Complete" if termination_msg.get('should_terminate') else "Continue"
                    summary += f" → {decision}"
        else:
            summary = "Reasoning: Agent thinking/planning"
        
        return {
            'loop_id': loop_id,
            'type': loop_type,
            'summary': summary,
            'messages': messages,
            'message_count': len(messages),
            'type_counts': type_counts,
            'tool_calls': tool_calls,
            'unique_tools': list(set(tool_calls)),
            'token_metrics': {
                'total_tokens': total_tokens,
                'cached_tokens': total_cached_tokens,
                'completion_tokens': total_completion_tokens
            },
            'has_function_calls': has_function_calls,
            'has_termination': has_termination
        }
    
    def analyze_loop_metrics(self, loops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze metrics across all loops."""
        total_tool_loops = sum(1 for loop in loops if loop.get('has_function_calls', False))
        total_reasoning_loops = len(loops) - total_tool_loops
        
        # Token usage across loops
        total_loop_tokens = sum(loop.get('token_metrics', {}).get('total_tokens', 0) for loop in loops)
        total_loop_cached = sum(loop.get('token_metrics', {}).get('cached_tokens', 0) for loop in loops)
        
        # Tool usage across loops
        all_tools = []
        for loop in loops:
            all_tools.extend(loop.get('tool_calls', []))
        
        unique_tools_used = len(set(all_tools))
        
        return {
            'total_loops': len(loops),
            'tool_loops': total_tool_loops,
            'reasoning_loops': total_reasoning_loops,
            'total_tool_calls': len(all_tools),
            'unique_tools_used': unique_tools_used,
            'tokens_across_loops': total_loop_tokens,
            'cached_tokens_across_loops': total_loop_cached,
            'avg_tokens_per_loop': total_loop_tokens // len(loops) if loops else 0
        }