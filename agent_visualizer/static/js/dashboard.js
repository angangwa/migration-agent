// Agent Conversation Visualizer - Dashboard JavaScript

// Global state
let conversationData = null;
let loopsData = null;
let metricsData = null;
let selectedMessageIndex = null;
let selectedLoopId = null;
let charts = {};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConversationData();
    loadLoopsData();
    loadMetrics();
    setupEventListeners();
});

// Load conversation data
async function loadConversationData() {
    try {
        const response = await fetch('/api/conversation');
        conversationData = await response.json();
        
        if (conversationData.error) {
            showError(conversationData.error);
            return;
        }
        
        // Don't render here - wait for loops data
    } catch (error) {
        showError('Failed to load conversation data: ' + error.message);
    }
}

// Load loops data
async function loadLoopsData() {
    try {
        const response = await fetch('/api/loops');
        loopsData = await response.json();
        
        if (loopsData.error) {
            showError(loopsData.error);
            return;
        }
        
        renderLoopBasedFlow();
    } catch (error) {
        showError('Failed to load loops data: ' + error.message);
    }
}

// Load metrics data
async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        metricsData = await response.json();
        
        if (metricsData.error) {
            showError(metricsData.error);
            return;
        }
        
        updateHeaderMetrics();
        renderTokenAnalytics();
        renderToolDistribution();
        renderTerminationChecks();
    } catch (error) {
        showError('Failed to load metrics: ' + error.message);
    }
}

// Update header metrics
function updateHeaderMetrics() {
    document.getElementById('total-messages').textContent = metricsData.total_messages;
    document.getElementById('total-tools').textContent = metricsData.tool_usage.total_calls;
    document.getElementById('total-loops').textContent = metricsData.loop_metrics.total_loops;
    
    const tokenMetrics = metricsData.token_metrics;
    document.getElementById('total-tokens').textContent = formatNumber(tokenMetrics.total_tokens);
    document.getElementById('cache-percentage').textContent = `(${tokenMetrics.cache_hit_rate.toFixed(1)}% cached)`;
}

// Render loop-based conversation flow in sidebar
function renderLoopBasedFlow() {
    const flowContainer = document.getElementById('conversation-flow');
    flowContainer.innerHTML = '';
    
    if (!loopsData || !loopsData.loops) {
        flowContainer.innerHTML = '<p class="text-muted">No loop data available</p>';
        return;
    }
    
    loopsData.loops.forEach((loop, loopIndex) => {
        const loopEl = createLoopElement(loop, loopIndex);
        flowContainer.appendChild(loopEl);
    });
}

// Create loop element for sidebar
function createLoopElement(loop, loopIndex) {
    const div = document.createElement('div');
    div.className = 'loop-item';
    div.dataset.loopId = loopIndex;
    
    // Determine loop icon and color
    const hasTools = loop.has_function_calls;
    const hasTermination = loop.has_termination;
    const icon = hasTools ? '<i class="fas fa-cogs"></i>' : '<i class="fas fa-brain"></i>';
    const typeClass = hasTools ? 'type-tool-loop' : 'type-reasoning';
    
    // Create collapsible loop header
    div.innerHTML = `
        <div class="loop-header ${typeClass}" data-bs-toggle="collapse" data-bs-target="#loop-${loopIndex}" aria-expanded="false">
            <div class="loop-summary">
                ${icon} <strong>Loop ${loopIndex + 1}</strong>
                <small class="text-muted ms-2">(${loop.message_count} messages)</small>
            </div>
            <div class="loop-metrics">
                <small>${loop.summary}</small>
            </div>
        </div>
        <div class="collapse loop-messages" id="loop-${loopIndex}">
            <div class="loop-content"></div>
        </div>
    `;
    
    // Add messages within the loop
    const loopContent = div.querySelector('.loop-content');
    loop.messages.forEach((message, msgIndex) => {
        const messageEl = createMessageElement(message, msgIndex, loopIndex);
        loopContent.appendChild(messageEl);
    });
    
    // Add loop click handler
    const loopHeader = div.querySelector('.loop-header');
    loopHeader.addEventListener('click', () => selectLoop(loopIndex));
    
    return div;
}

// Create message element for sidebar (within loop)
function createMessageElement(message, messageIndex, loopIndex) {
    const div = document.createElement('div');
    div.className = 'message-item-in-loop';
    div.dataset.index = message.index;
    div.dataset.loopId = loopIndex;
    
    // Add icon based on message type
    const icon = getMessageIcon(message.type);
    const typeClass = `type-${message.type}`;
    
    div.innerHTML = `
        <div class="message-type-small ${typeClass}">
            ${icon} ${message.type.replace('_', ' ')}
        </div>
        <div class="message-summary-small">${message.summary}</div>
    `;
    
    div.addEventListener('click', (e) => {
        e.stopPropagation();
        selectMessage(message.index, loopIndex);
    });
    
    return div;
}

// Get icon for message type
function getMessageIcon(type) {
    const icons = {
        'assistant': '<i class="fas fa-robot"></i>',
        'function_call': '<i class="fas fa-cog"></i>',
        'function_result': '<i class="fas fa-check-circle"></i>',
        'termination': '<i class="fas fa-stop-circle"></i>',
        'user': '<i class="fas fa-user"></i>'
    };
    return icons[type] || '<i class="fas fa-comment"></i>';
}

// Select and display loop details
async function selectLoop(loopId) {
    // Update active state in sidebar
    document.querySelectorAll('.loop-item').forEach(el => el.classList.remove('active-loop'));
    document.querySelector(`[data-loop-id="${loopId}"]`).classList.add('active-loop');
    
    selectedLoopId = loopId;
    
    // Show/hide loop navigation
    const navigation = document.getElementById('loop-navigation');
    navigation.style.display = 'block';
    
    // Update navigation buttons
    document.getElementById('prev-loop').disabled = loopId === 0;
    document.getElementById('next-loop').disabled = loopId === loopsData.loops.length - 1;
    
    // Load and display loop details
    try {
        const response = await fetch(`/api/loop/${loopId}`);
        const loopData = await response.json();
        
        if (loopData.error) {
            showError(loopData.error);
            return;
        }
        
        renderLoopDetails(loopData);
    } catch (error) {
        showError('Failed to load loop details: ' + error.message);
    }
}

// Select and display message details
async function selectMessage(index, loopId = null) {
    // Update active state in sidebar
    document.querySelectorAll('.message-item-in-loop').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-index="${index}"]`).classList.add('active');
    
    selectedMessageIndex = index;
    selectedLoopId = loopId;
    
    // Show/hide loop navigation
    const navigation = document.getElementById('loop-navigation');
    if (loopId !== null) {
        navigation.style.display = 'block';
        document.getElementById('prev-loop').disabled = loopId === 0;
        document.getElementById('next-loop').disabled = loopId === loopsData.loops.length - 1;
    } else {
        navigation.style.display = 'none';
    }
    
    // Load and display message details
    try {
        const response = await fetch(`/api/message/${index}`);
        const messageData = await response.json();
        
        if (messageData.error) {
            showError(messageData.error);
            return;
        }
        
        renderMessageDetails(messageData);
    } catch (error) {
        showError('Failed to load message details: ' + error.message);
    }
}

// Render loop details in main content
function renderLoopDetails(loop) {
    const detailsContainer = document.getElementById('message-details');
    let detailsHTML = '';
    
    // Loop header
    const icon = loop.has_function_calls ? '<i class="fas fa-cogs"></i>' : '<i class="fas fa-brain"></i>';
    detailsHTML += `
        <div class="loop-detail-header">
            <h6>${icon} Loop ${loop.loop_id + 1} - ${loop.type.replace('_', ' ').toUpperCase()}</h6>
            <p class="text-muted">${loop.summary}</p>
        </div>
    `;
    
    // Loop metrics
    detailsHTML += `
        <div class="loop-metrics-section">
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-info-circle"></i> Loop Metrics</h6>
                    <ul class="list-unstyled">
                        <li><strong>Messages:</strong> ${loop.message_count}</li>
                        <li><strong>Tool Calls:</strong> ${loop.tool_calls.length}</li>
                        <li><strong>Unique Tools:</strong> ${loop.unique_tools.length}</li>
                        <li><strong>Has Termination:</strong> ${loop.has_termination ? 'Yes' : 'No'}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-coins"></i> Token Usage</h6>
                    <ul class="list-unstyled">
                        <li><strong>Total:</strong> ${formatNumber(loop.token_metrics.total_tokens)}</li>
                        <li><strong>Cached:</strong> ${formatNumber(loop.token_metrics.cached_tokens)}</li>
                        <li><strong>Completion:</strong> ${formatNumber(loop.token_metrics.completion_tokens)}</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
    
    // Messages in loop
    detailsHTML += `
        <div class="loop-messages-section">
            <h6><i class="fas fa-list"></i> Messages in Loop</h6>
            <div class="messages-in-loop">
    `;
    
    loop.messages.forEach((message, idx) => {
        const messageIcon = getMessageIcon(message.type);
        const typeClass = `type-${message.type}`;
        detailsHTML += `
            <div class="message-in-loop-detail ${typeClass}" data-message-index="${message.index}">
                <div class="message-header-inline">
                    <span class="message-icon">${messageIcon}</span>
                    <span class="message-type-text">${message.type.replace('_', ' ')}</span>
                    <small class="text-muted">#${message.index + 1}</small>
                </div>
                <div class="message-summary-inline">${message.summary}</div>
            </div>
        `;
    });
    
    detailsHTML += `
            </div>
        </div>
    `;
    
    detailsContainer.innerHTML = detailsHTML;
    
    // Add click handlers for messages in loop
    document.querySelectorAll('.message-in-loop-detail').forEach(el => {
        el.addEventListener('click', () => {
            const messageIndex = parseInt(el.dataset.messageIndex);
            selectMessage(messageIndex, loop.loop_id);
        });
    });
}

// Render message details in main content
function renderMessageDetails(message) {
    const detailsContainer = document.getElementById('message-details');
    let detailsHTML = '';
    
    // Header
    detailsHTML += `
        <div class="message-detail-header">
            <h6>${getMessageIcon(message.type)} Message #${message.index + 1}</h6>
            <small class="text-muted">Type: ${message.type} | Role: ${message.role}</small>
        </div>
    `;
    
    // Content based on message type
    if (message.type === 'termination') {
        detailsHTML += renderTerminationDetails(message);
    } else if (message.type === 'function_call') {
        detailsHTML += renderFunctionCallDetails(message);
    } else if (message.type === 'function_result') {
        detailsHTML += renderFunctionResultDetails(message);
    } else if (message.type === 'assistant') {
        detailsHTML += renderAssistantDetails(message);
    }
    
    // Token usage if available
    if (message.token_usage && Object.keys(message.token_usage).length > 0) {
        detailsHTML += renderTokenUsageDetails(message.token_usage);
    }
    
    detailsContainer.innerHTML = detailsHTML;
    
    // Re-highlight code blocks
    Prism.highlightAll();
}

// Render termination check details
function renderTerminationDetails(message) {
    const iconClass = message.should_terminate ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
    const decision = message.should_terminate ? 'TERMINATE' : 'CONTINUE';
    
    return `
        <div class="termination-detail">
            <h6><i class="fas ${iconClass}"></i> Decision: ${decision}</h6>
            <p><strong>Reason:</strong></p>
            <div class="message-content">${escapeHtml(message.content)}</div>
        </div>
    `;
}

// Render function call details
function renderFunctionCallDetails(message) {
    let html = '<div class="function-call-detail">';
    
    message.items.forEach(item => {
        if (item.content_type === 'function_call') {
            html += `
                <h6><i class="fas fa-cog"></i> Function Call: ${item.name}</h6>
                <p><strong>Arguments:</strong></p>
                <pre><code class="language-json">${JSON.stringify(JSON.parse(item.arguments), null, 2)}</code></pre>
            `;
        }
    });
    
    html += '</div>';
    return html;
}

// Render function result details
function renderFunctionResultDetails(message) {
    let html = '<div class="function-result-detail">';
    
    message.items.forEach(item => {
        if (item.content_type === 'function_result') {
            html += `
                <h6><i class="fas fa-check-circle"></i> Function Result: ${item.name}</h6>
                <p><strong>Result:</strong></p>
                <pre><code class="language-json">${formatJsonResult(item.result)}</code></pre>
            `;
        }
    });
    
    html += '</div>';
    return html;
}

// Render assistant message details
function renderAssistantDetails(message) {
    const content = message.content || 'No content';
    const renderedContent = content !== 'No content' ? marked.parse(content) : content;
    
    return `
        <div class="message-content">
            <h6><i class="fas fa-robot"></i> Assistant Message</h6>
            <div class="markdown-content">${renderedContent}</div>
        </div>
    `;
}

// Render token usage details
function renderTokenUsageDetails(usage) {
    const promptDetails = usage.prompt_tokens_details || {};
    const completionDetails = usage.completion_tokens_details || {};
    
    return `
        <div class="token-usage-detail mt-3">
            <h6><i class="fas fa-coins"></i> Token Usage</h6>
            <div class="row">
                <div class="col-md-6">
                    <strong>Prompt Tokens: ${usage.prompt_tokens || 0}</strong>
                    <ul class="small">
                        <li>Cached: ${promptDetails.cached_tokens || 0}</li>
                        <li>Audio: ${promptDetails.audio_tokens || 0}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <strong>Completion Tokens: ${usage.completion_tokens || 0}</strong>
                    <ul class="small">
                        <li>Reasoning: ${completionDetails.reasoning_tokens || 0}</li>
                        <li>Accepted: ${completionDetails.accepted_prediction_tokens || 0}</li>
                        <li>Rejected: ${completionDetails.rejected_prediction_tokens || 0}</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

// Render token analytics section
function renderTokenAnalytics() {
    const tokenMetrics = metricsData.token_metrics;
    
    // Update statistics
    document.getElementById('stat-prompt-tokens').textContent = formatNumber(tokenMetrics.total_prompt_tokens);
    document.getElementById('stat-cached-tokens').textContent = formatNumber(tokenMetrics.total_cached_tokens);
    document.getElementById('stat-completion-tokens').textContent = formatNumber(tokenMetrics.total_completion_tokens);
    document.getElementById('stat-reasoning-tokens').textContent = formatNumber(tokenMetrics.total_reasoning_tokens);
    
    // Update cost analysis
    const costAnalysis = tokenMetrics.cost_analysis;
    document.getElementById('actual-cost').textContent = costAnalysis.actual_cost.toFixed(4);
    document.getElementById('cost-savings').textContent = costAnalysis.savings_from_cache.toFixed(4);
    document.getElementById('savings-percentage').textContent = costAnalysis.savings_percentage + '%';
}

// Render tool distribution section
function renderToolDistribution() {
    if (!metricsData.tool_usage || !metricsData.tool_usage.tool_analysis) {
        return;
    }
    
    const toolAnalysis = metricsData.tool_usage.tool_analysis;
    
    // Render frequency table
    renderToolFrequencyTable(toolAnalysis);
    
    // Render verbosity table
    renderToolVerbosityTable(toolAnalysis);
}

// Render tool frequency table
function renderToolFrequencyTable(toolAnalysis) {
    const container = document.getElementById('tool-frequency-table');
    
    if (toolAnalysis.length === 0) {
        container.innerHTML = '<p class="text-muted">No tool usage data available</p>';
        return;
    }
    
    let tableHtml = `
        <table class="table table-sm table-hover">
            <thead class="table-light">
                <tr>
                    <th>Tool</th>
                    <th>Calls</th>
                    <th>Success</th>
                    <th>Success Rate</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    toolAnalysis.forEach(tool => {
        const successBadge = tool.success_rate >= 90 ? 'success' : 
                           tool.success_rate >= 70 ? 'warning' : 'danger';
        
        tableHtml += `
            <tr>
                <td><strong>${tool.name}</strong></td>
                <td><span class="badge bg-primary">${tool.calls}</span></td>
                <td>${tool.success}/${tool.success + tool.failure}</td>
                <td><span class="badge bg-${successBadge}">${tool.success_rate}%</span></td>
            </tr>
        `;
    });
    
    tableHtml += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHtml;
}

// Render tool verbosity table
function renderToolVerbosityTable(toolAnalysis) {
    const container = document.getElementById('tool-verbosity-table');
    
    if (toolAnalysis.length === 0) {
        container.innerHTML = '<p class="text-muted">No verbosity data available</p>';
        return;
    }
    
    // Sort by total characters for verbosity display
    const sortedByVerbosity = [...toolAnalysis].sort((a, b) => b.total_chars - a.total_chars);
    
    let tableHtml = `
        <table class="table table-sm table-hover">
            <thead class="table-light">
                <tr>
                    <th>Tool</th>
                    <th title="Total characters across all responses">Total Chars</th>
                    <th title="Average characters per response">Avg Chars</th>
                    <th title="Rough token estimate (chars ÷ 4)">Est. Tokens</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    sortedByVerbosity.forEach(tool => {
        if (tool.avg_chars > 0) {  // Only show tools with results
            const verbosityLevel = tool.avg_chars > 5000 ? 'danger' : 
                                  tool.avg_chars > 2000 ? 'warning' : 
                                  tool.avg_chars > 500 ? 'info' : 'success';
            
            tableHtml += `
                <tr>
                    <td><strong>${tool.name}</strong></td>
                    <td>${formatNumber(tool.total_chars)}</td>
                    <td><span class="badge bg-${verbosityLevel}">${formatNumber(tool.avg_chars)}</span></td>
                    <td>${formatNumber(tool.avg_tokens_est)}</td>
                </tr>
            `;
        }
    });
    
    tableHtml += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHtml;
}


// Setup event listeners
function setupEventListeners() {
    // Search functionality
    document.getElementById('search-messages').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        filterLoops(searchTerm);
    });
    
    // Cost configuration
    document.getElementById('update-pricing').addEventListener('click', updatePricing);
    
    // Loop navigation
    document.getElementById('prev-loop').addEventListener('click', () => {
        if (selectedLoopId > 0) {
            selectLoop(selectedLoopId - 1);
        }
    });
    
    document.getElementById('next-loop').addEventListener('click', () => {
        if (selectedLoopId < loopsData.loops.length - 1) {
            selectLoop(selectedLoopId + 1);
        }
    });
}

// Filter loops based on search
function filterLoops(searchTerm) {
    const loopItems = document.querySelectorAll('.loop-item');
    
    loopItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Update pricing configuration
async function updatePricing() {
    const promptCost = parseFloat(document.getElementById('prompt-cost').value);
    const cachedCost = parseFloat(document.getElementById('cached-cost').value);
    const completionCost = parseFloat(document.getElementById('completion-cost').value);
    
    try {
        const response = await fetch('/api/update-pricing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt_cost: promptCost,
                cached_prompt_cost: cachedCost,
                completion_cost: completionCost
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            showError(result.error);
            return;
        }
        
        // Update the display with new metrics
        const costAnalysis = result.token_metrics.cost_analysis;
        document.getElementById('actual-cost').textContent = costAnalysis.actual_cost.toFixed(4);
        document.getElementById('cost-savings').textContent = costAnalysis.savings_from_cache.toFixed(4);
        document.getElementById('savings-percentage').textContent = costAnalysis.savings_percentage + '%';
        
        // Show success message briefly
        const button = document.getElementById('update-pricing');
        const originalText = button.textContent;
        button.textContent = 'Updated!';
        button.classList.add('btn-success');
        button.classList.remove('btn-primary');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-primary');
        }, 2000);
        
    } catch (error) {
        showError('Failed to update pricing: ' + error.message);
    }
}

// Render termination checks section
function renderTerminationChecks() {
    if (!metricsData.termination_checks || !metricsData.termination_checks.checks) {
        return;
    }
    
    const checks = metricsData.termination_checks.checks;
    const container = document.getElementById('termination-checks-table');
    
    if (checks.length === 0) {
        container.innerHTML = '<p class="text-muted">No termination checks found</p>';
        return;
    }
    
    let tableHtml = `
        <table class="table table-sm table-hover">
            <thead class="table-light">
                <tr>
                    <th>Check #</th>
                    <th>Decision</th>
                    <th>Reasoning</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    checks.forEach((check, index) => {
        const decisionBadge = check.should_terminate ? 'success' : 'warning';
        const decisionText = check.should_terminate ? 'Complete' : 'Continue';
        const reasoning = check.reason || '';
        const reasoningPreview = reasoning.length > 100 ? 
            reasoning.substring(0, 100) + '...' : reasoning;
        
        tableHtml += `
            <tr>
                <td><strong>${index + 1}</strong></td>
                <td><span class="badge bg-${decisionBadge}">${decisionText}</span></td>
                <td><small>${escapeHtml(reasoningPreview)}</small></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-termination-btn" 
                            data-check-index="${check.index}">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHtml;
    
    // Add click handlers for view buttons
    document.querySelectorAll('.view-termination-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const checkIndex = parseInt(e.target.closest('.view-termination-btn').dataset.checkIndex);
            selectTerminationCheck(checkIndex);
        });
    });
}

// Select and display termination check details
async function selectTerminationCheck(messageIndex) {
    
    // Clear any active states in sidebar (no sidebar selection for termination)
    document.querySelectorAll('.message-item-in-loop').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.loop-item').forEach(el => el.classList.remove('active-loop'));
    
    // Hide loop navigation
    const navigation = document.getElementById('loop-navigation');
    navigation.style.display = 'none';
    
    selectedMessageIndex = messageIndex;
    selectedLoopId = null;
    
    // Load and display termination check details
    try {
        const response = await fetch(`/api/message/${messageIndex}`);
        const messageData = await response.json();
        
        if (messageData.error) {
            showError(messageData.error);
            return;
        }
        
        renderMessageDetails(messageData);
    } catch (error) {
        showError('Failed to load termination check details: ' + error.message);
    }
}

// Utility functions
function formatNumber(num) {
    return num.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatResult(result) {
    try {
        const parsed = JSON.parse(result);
        return JSON.stringify(parsed, null, 2);
    } catch {
        return result;
    }
}

function formatJsonResult(result) {
    try {
        // If it's already a string that looks like JSON, parse and reformat
        if (typeof result === 'string') {
            const parsed = JSON.parse(result);
            return JSON.stringify(parsed, null, 2);
        }
        // If it's already an object, stringify it
        else if (typeof result === 'object') {
            return JSON.stringify(result, null, 2);
        }
        // Otherwise return as is
        else {
            return String(result);
        }
    } catch (e) {
        // If parsing fails, try to pretty-print as best we can
        if (typeof result === 'string' && (result.startsWith('{') || result.startsWith('['))) {
            // Try to fix common JSON issues and reformat
            try {
                // Remove any trailing commas and fix quotes
                let cleaned = result.replace(/,(\s*[}\]])/g, '$1');
                const parsed = JSON.parse(cleaned);
                return JSON.stringify(parsed, null, 2);
            } catch {
                // If still fails, return with basic formatting
                return result.replace(/,/g, ',\n').replace(/{/g, '{\n  ').replace(/}/g, '\n}');
            }
        }
        return String(result);
    }
}

function showError(message) {
    const container = document.querySelector('.main-content');
    container.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-triangle"></i> ${message}
        </div>
    `;
}