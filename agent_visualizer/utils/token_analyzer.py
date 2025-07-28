"""
Token Analyzer for Agent Responses
Analyzes token usage patterns including cached tokens.
"""

from typing import List, Dict, Any
from collections import defaultdict

class TokenAnalyzer:
    def __init__(self, prompt_cost=1.10, cached_prompt_cost=0.275, completion_cost=4.40):
        # Default to o4-mini pricing (per million tokens, converted to per 1k)
        self.cost_per_1k_prompt = prompt_cost / 1000  # Convert per million to per 1k
        self.cost_per_1k_cached_prompt = cached_prompt_cost / 1000  # Separate cached pricing
        self.cost_per_1k_completion = completion_cost / 1000
    
    def calculate_metrics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive token metrics."""
        metrics = {
            'total_prompt_tokens': 0,
            'total_cached_tokens': 0,
            'total_completion_tokens': 0,
            'total_reasoning_tokens': 0,
            'total_tokens': 0,
            'cache_hit_rate': 0,
            'cost_analysis': {},
            'token_efficiency': {}
        }
        
        messages_with_tokens = 0
        
        for msg in messages:
            if msg.get('role') == 'assistant' and 'metadata' in msg:
                usage = msg.get('metadata', {}).get('usage', {})
                if usage:
                    messages_with_tokens += 1
                    
                    # Prompt tokens
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    metrics['total_prompt_tokens'] += prompt_tokens
                    
                    # Cached tokens
                    prompt_details = usage.get('prompt_tokens_details', {})
                    cached_tokens = prompt_details.get('cached_tokens', 0)
                    metrics['total_cached_tokens'] += cached_tokens
                    
                    # Completion tokens
                    completion_tokens = usage.get('completion_tokens', 0)
                    metrics['total_completion_tokens'] += completion_tokens
                    
                    # Reasoning tokens
                    completion_details = usage.get('completion_tokens_details', {})
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0)
                    metrics['total_reasoning_tokens'] += reasoning_tokens
        
        # Calculate totals and ratios
        metrics['total_tokens'] = metrics['total_prompt_tokens'] + metrics['total_completion_tokens']
        
        # Cache hit rate
        if metrics['total_prompt_tokens'] > 0:
            metrics['cache_hit_rate'] = (metrics['total_cached_tokens'] / metrics['total_prompt_tokens']) * 100
        
        # Cost analysis
        metrics['cost_analysis'] = self._calculate_costs(metrics)
        
        # Token efficiency
        metrics['token_efficiency'] = {
            'avg_prompt_per_message': metrics['total_prompt_tokens'] / messages_with_tokens if messages_with_tokens > 0 else 0,
            'avg_completion_per_message': metrics['total_completion_tokens'] / messages_with_tokens if messages_with_tokens > 0 else 0,
            'reasoning_percentage': (metrics['total_reasoning_tokens'] / metrics['total_completion_tokens'] * 100) if metrics['total_completion_tokens'] > 0 else 0
        }
        
        return metrics
    
    def _calculate_costs(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost analysis including savings from cached tokens."""
        # Actual costs
        uncached_prompt_tokens = metrics['total_prompt_tokens'] - metrics['total_cached_tokens']
        cached_prompt_cost = (metrics['total_cached_tokens'] / 1000) * self.cost_per_1k_cached_prompt
        uncached_prompt_cost = (uncached_prompt_tokens / 1000) * self.cost_per_1k_prompt
        completion_cost = (metrics['total_completion_tokens'] / 1000) * self.cost_per_1k_completion
        
        actual_total_cost = cached_prompt_cost + uncached_prompt_cost + completion_cost
        
        # Potential cost without caching (all prompt tokens at full price)
        potential_prompt_cost = (metrics['total_prompt_tokens'] / 1000) * self.cost_per_1k_prompt
        potential_total_cost = potential_prompt_cost + completion_cost
        
        # Savings
        savings = potential_total_cost - actual_total_cost
        
        return {
            'actual_cost': round(actual_total_cost, 4),
            'potential_cost_without_cache': round(potential_total_cost, 4),
            'savings_from_cache': round(savings, 4),
            'savings_percentage': round((savings / potential_total_cost * 100) if potential_total_cost > 0 else 0, 2),
            'pricing': {
                'prompt_per_1k': self.cost_per_1k_prompt,
                'cached_prompt_per_1k': self.cost_per_1k_cached_prompt,
                'completion_per_1k': self.cost_per_1k_completion
            }
        }
    
    def create_token_timeline(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create timeline data for token usage visualization with proper scaling."""
        timeline = {
            'labels': [],
            'prompt_tokens': [],
            'cached_tokens': [],
            'completion_tokens': [],
            'reasoning_tokens': [],
            'cache_percentages': [],
            'cumulative_tokens': []
        }
        
        cumulative = 0
        message_count = 0
        token_values = []  # For calculating proper scaling
        
        for idx, msg in enumerate(messages):
            if msg.get('role') == 'assistant' and 'metadata' in msg:
                usage = msg.get('metadata', {}).get('usage', {})
                if usage:
                    message_count += 1
                    
                    # Extract token data
                    prompt = usage.get('prompt_tokens', 0)
                    cached = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                    completion = usage.get('completion_tokens', 0)
                    reasoning = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)
                    
                    # Calculate cache percentage for this message
                    cache_pct = (cached / prompt * 100) if prompt > 0 else 0
                    
                    # Update cumulative
                    cumulative += prompt + completion
                    token_values.append(cumulative)
                    
                    # Add to timeline
                    timeline['labels'].append(f"Msg {idx + 1}")
                    timeline['prompt_tokens'].append(prompt)
                    timeline['cached_tokens'].append(cached)
                    timeline['completion_tokens'].append(completion)
                    timeline['reasoning_tokens'].append(reasoning)
                    timeline['cache_percentages'].append(round(cache_pct, 1))
                    timeline['cumulative_tokens'].append(cumulative)
        
        # Add scaling metadata for better chart rendering
        if token_values:
            timeline['scaling'] = {
                'min_tokens': min(token_values),
                'max_tokens': max(token_values),
                'range': max(token_values) - min(token_values),
                'avg_tokens': sum(token_values) / len(token_values)
            }
        
        return timeline
    
    def update_pricing(self, prompt_cost: float, cached_prompt_cost: float, completion_cost: float):
        """Update pricing configuration (prices per million tokens)."""
        self.cost_per_1k_prompt = prompt_cost / 1000
        self.cost_per_1k_cached_prompt = cached_prompt_cost / 1000
        self.cost_per_1k_completion = completion_cost / 1000
    
    def analyze_cache_patterns(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze caching patterns across the conversation."""
        cache_growth = []
        total_cached = 0
        total_prompt = 0
        
        for msg in messages:
            if msg.get('role') == 'assistant' and 'metadata' in msg:
                usage = msg.get('metadata', {}).get('usage', {})
                if usage:
                    prompt = usage.get('prompt_tokens', 0)
                    cached = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                    
                    total_prompt += prompt
                    total_cached += cached
                    
                    if total_prompt > 0:
                        cache_growth.append({
                            'total_prompt': total_prompt,
                            'total_cached': total_cached,
                            'cache_rate': (total_cached / total_prompt) * 100
                        })
        
        return {
            'cache_growth': cache_growth,
            'final_cache_rate': cache_growth[-1]['cache_rate'] if cache_growth else 0,
            'cache_improvement': cache_growth[-1]['cache_rate'] - cache_growth[0]['cache_rate'] if len(cache_growth) > 1 else 0
        }