#!/usr/bin/env python3
"""
SK Agents Structure Validation Script

This script validates that our modular structure is correctly set up
and can be imported without errors.
"""

import sys
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("🔍 Testing imports...")
    
    try:
        # Test services
        from sk_agents.services import get_service, get_reasoning_service, get_chat_service
        print("  ✅ Services module imported")
        
        # Test orchestration
        from sk_agents.orchestration.managers import SingleAgentGroupChatManager
        print("  ✅ Orchestration managers imported")
        
        # Test agents
        from sk_agents.agents import create_agent, load_agent_from_config
        print("  ✅ Agent helpers imported")
        
        # Test plugins
        from plugins.file_system import FileSystemPlugin
        print("  ✅ FileSystemPlugin imported")
        
        # Test config
        from sk_agents.config import MAX_ROUNDS, DEFAULT_REASONING_EFFORT
        print("  ✅ Configuration imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_service_creation():
    """Test service creation functions."""
    print("\n🔧 Testing service creation...")
    
    try:
        from sk_agents.services.llm import _deployment_to_env_prefix, _is_reasoning_model
        
        # Test utility functions
        assert _deployment_to_env_prefix("o4-mini") == "O4_MINI"
        assert _deployment_to_env_prefix("gpt-4.1") == "GPT_4_1"
        assert _deployment_to_env_prefix("o4-mini-custom") == "O4_MINI_CUSTOM"
        print("  ✅ Deployment name conversion works")
        
        assert _is_reasoning_model("o4-mini") == True
        assert _is_reasoning_model("o1-preview") == True
        assert _is_reasoning_model("gpt-4.1") == False
        assert _is_reasoning_model("gpt-4o-mini") == False
        print("  ✅ Reasoning model detection works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Service creation test failed: {e}")
        traceback.print_exc()
        return False


def test_agent_config():
    """Test agent configuration loading."""
    print("\n👤 Testing agent configuration...")
    
    try:
        from sk_agents.agents import get_agent_config
        
        # Test loading a config
        config = get_agent_config("codebase_analysis")
        
        assert "name" in config
        assert "description" in config
        assert "instructions" in config
        assert config["name"] == "CodebaseAnalysisAndTestingAgent"
        
        print("  ✅ Agent config loading works")
        print(f"  📋 Loaded config for: {config['name']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Agent config test failed: {e}")
        traceback.print_exc()
        return False


def test_file_system_plugin():
    """Test FileSystemPlugin functionality."""
    print("\n📁 Testing FileSystemPlugin...")
    
    try:
        from plugins.file_system import FileSystemPlugin
        
        # Create plugin with current directory
        plugin = FileSystemPlugin(base_path=".")
        
        # Check if it has the expected functions
        assert hasattr(plugin, 'find_files')
        assert hasattr(plugin, 'list_directory')
        assert hasattr(plugin, 'read_file')
        assert hasattr(plugin, 'search_in_files')
        assert hasattr(plugin, 'get_file_info')
        
        print("  ✅ FileSystemPlugin created successfully")
        print("  ✅ All expected functions present")
        
        return True
        
    except Exception as e:
        print(f"  ❌ FileSystemPlugin test failed: {e}")
        traceback.print_exc()
        return False


def test_single_agent_manager():
    """Test SingleAgentGroupChatManager structure."""
    print("\n🤖 Testing SingleAgentGroupChatManager...")
    
    try:
        from sk_agents.orchestration.managers import SingleAgentGroupChatManager
        
        # Check methods exist
        assert hasattr(SingleAgentGroupChatManager, 'should_request_user_input')
        assert hasattr(SingleAgentGroupChatManager, 'should_terminate')
        assert hasattr(SingleAgentGroupChatManager, 'select_next_agent')
        assert hasattr(SingleAgentGroupChatManager, 'filter_results')
        assert hasattr(SingleAgentGroupChatManager, '__init__')
        
        # For Pydantic models, check class annotations
        annotations = getattr(SingleAgentGroupChatManager, '__annotations__', {})
        assert 'topic' in annotations, f"Available annotations: {list(annotations.keys())}"
        assert 'service' in annotations, f"Available annotations: {list(annotations.keys())}"
        
        # Check the termination prompt is accessible (should be a class attribute)
        assert hasattr(SingleAgentGroupChatManager, 'termination_prompt')
        prompt = SingleAgentGroupChatManager.termination_prompt
        assert isinstance(prompt, str)
        assert "code analysis agent" in prompt.lower()
        assert "FileSystemPlugin functions" in prompt
        assert "find_files, list_directory, read_file, search_in_files, and get_file_info" in prompt
        
        print("  ✅ SingleAgentGroupChatManager structure correct")
        print("  ✅ All required methods present") 
        print("  ✅ Pydantic fields properly annotated")
        print("  ✅ Termination prompt preserved from notebook")
        
        return True
        
    except Exception as e:
        print(f"  ❌ SingleAgentGroupChatManager test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("🚀 SK Agents Structure Validation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_service_creation,
        test_agent_config,
        test_file_system_plugin,
        test_single_agent_manager,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! Structure is ready for testing.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please fix before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())