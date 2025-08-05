# SK Agents Implementation Plan

## Overview
Breaking down the 5.1-code_exploration.ipynb notebook into a modular, extensible project structure while preserving exact Semantic Kernel patterns.

## Project Structure
```
sk_agents/
├── agents/
│   ├── __init__.py
│   ├── base_agents.py         # Common agent creation patterns
│   └── configs/
│       └── agents.yaml         # Agent configurations (names, prompts, models)
│
├── orchestration/
│   ├── __init__.py
│   ├── managers/
│   │   ├── __init__.py
│   │   ├── single_agent.py    # SingleAgentGroupChatManager from notebook
│   │   └── llm_based.py       # LLMBasedGroupChatManager from notebook
│   └── examples/
│       ├── group_chat.py      # Group chat examples
│       ├── sequential.py      # Sequential pipeline examples
│       ├── concurrent.py      # Concurrent execution examples
│       └── handoff.py         # Handoff examples
│
├── services/
│   ├── __init__.py
│   └── llm.py                 # Service configurations for different models
│
├── plugins/
│   └── file_system/           # Copy of existing FileSystemPlugin
│
├── config/
│   └── settings.py            # Environment variables and base settings
│
├── examples/
│   ├── run_codebase_analysis.py
│   ├── run_group_chat.py
│   └── notebooks/
│       └── test_migration.ipynb
│
└── requirements.txt
```

## Implementation Status

### Phase 1: Create Project Structure ✅
- [x] Create sk_agents directory structure
- [x] Create __init__.py files

### Phase 2: Core Components ✅
- [x] Copy FileSystemPlugin to plugins directory
- [x] Implement services/llm.py with service configurations
  - [x] Updated to Azure-only with new env var structure
  - [x] Pattern: `AZURE_<DEPLOYMENT_NAME>_ENDPOINT/API_KEY`
  - [x] Support for reasoning models (o1, o3, o4-mini)
  - [x] Fallback to AZURE_DEFAULT_* credentials
- [x] Extract SingleAgentGroupChatManager to managers/single_agent.py
  - [x] Preserved exact implementation from notebook
  - [x] Kept all method signatures and class variables

### Phase 3: Helper Functions ✅
- [x] Create agents/base_agents.py with helper functions
  - [x] `create_agent()` wrapper for ChatCompletionAgent
  - [x] `load_agent_from_config()` to read from YAML
  - [x] `get_agent_config()` for config loading
  - [x] `create_agent_team()` for multi-agent scenarios
- [x] Create config/settings.py with environment variables
  - [x] Base configuration constants
  - [x] Environment variable helpers
  - [x] Default values with env override support

### Phase 4: Configuration Files ✅
- [x] Create agents/configs/agents.yaml with agent configurations
  - [x] CodebaseAnalysisAndTestingAgent configuration (exact from notebook)
  - [x] Other common agent templates from notebook 3
  - [x] All agent configs with preserved instructions

### Phase 5: Testing & Validation ✅
- [x] Create test notebook (examples/test_migration.ipynb)
  - [x] Import from new structure
  - [x] Run exact same orchestration as notebook 5.1
  - [x] Test both direct creation and config loading
  - [x] Response tracking and comparison setup
- [x] Prepare for real orchestration test
  - [x] Structure ready for manual testing
  - [x] Clear instructions provided

### Phase 6: Documentation 🔄
- [ ] Create README.md with usage instructions
- [ ] Add docstrings to all modules
- [ ] Create example scripts

### Phase 7: Extended Examples (Optional) 🔄
- [ ] Add LLMBasedGroupChatManager from notebook 3
- [ ] Create examples for other orchestration types
- [ ] Add more agent configurations

## Testing Checklist

### Service Layer
- [ ] `get_service()` works with any deployment name
- [ ] Reasoning detection works correctly
- [ ] Environment variable lookup works
- [ ] Fallback to default credentials works
- [ ] Clear error messages when credentials missing

### Orchestration Layer
- [ ] SingleAgentGroupChatManager terminates correctly
- [ ] Agent selection works for single agent
- [ ] Message filtering returns final report
- [ ] Termination prompt renders correctly

### Agent Layer
- [ ] Agent creation preserves all parameters
- [ ] Plugins load correctly
- [ ] Instructions and descriptions preserved

### Integration
- [ ] Complete notebook scenario runs successfully
- [ ] Agent completes both objectives
- [ ] Final markdown report generated
- [ ] No SK pattern violations

## Environment Variables (.env)

### New Structure (Active) ✅
```bash
# Pattern: AZURE_<DEPLOYMENT_NAME>_<PROPERTY>
AZURE_O4_MINI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_O4_MINI_API_KEY=your-api-key-here

AZURE_GPT_4_1_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_GPT_4_1_API_KEY=your-api-key-here

# Optional fallback
AZURE_DEFAULT_ENDPOINT=https://default-endpoint.openai.azure.com/
AZURE_DEFAULT_API_KEY=default-api-key-here
```

### Old Structure (Deprecated)
- AZURE_OPENAI_DEPLOYMENT_NAME (no longer used)
- AZURE_REASONING_DEPLOYMENT_NAME (no longer used)
- AZURE_OPENAI_ENDPOINT/API_KEY (replaced by model-specific)
- AZURE_REASONING_ENDPOINT/API_KEY (replaced by model-specific)

## Notes
- Preserve exact SK patterns to avoid brittleness
- Keep SingleAgentGroupChatManager implementation identical
- Use SK orchestrations as-is, only add custom managers
- Simple imports for notebook usage
- No complex abstractions