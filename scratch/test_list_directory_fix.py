#!/usr/bin/env python3
"""
Quick test to verify the list_directory fix shows "./" instead of "consult/"
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.file_system import FileSystemPlugin


async def test_list_directory_fix():
    """Test that list_directory shows ./ for root directory."""
    
    # Test with consult directory as base
    consult_path = "/home/agangwal/lseg-migration-agent/migration-agent/consult"
    plugin = FileSystemPlugin(base_path=consult_path)
    
    print("Testing list_directory with consult as base path...")
    print(f"Base path: {consult_path}\n")
    
    # Call list_directory on root
    result = await plugin.list_directory(".", max_depth="2", max_entries="50")
    
    if result['success']:
        tree = result['data']['tree']
        print("Directory tree output:")
        print("-" * 50)
        print(tree)
        print("-" * 50)
        
        # Also print the summary
        summary = result['data'].get('summary', {})
        print(f"\nSummary: {summary}")
        print(f"Metadata: {result.get('metadata', {})}")
        
        # Check if it starts with ./ instead of consult/
        if tree.startswith("./"):
            print("\n✅ SUCCESS: Root directory shown as './'")
        elif tree.startswith("consult/"):
            print("\n❌ FAIL: Root directory still shown as 'consult/'")
        else:
            print(f"\n❓ Unexpected output: starts with '{tree.split('/')[0]}/'")
    else:
        print(f"❌ Error: {result['error']}")
        

async def test_relative_paths():
    """Test that other tools still work correctly with relative paths."""
    
    consult_path = "/home/agangwal/lseg-migration-agent/migration-agent/consult"
    plugin = FileSystemPlugin(base_path=consult_path)
    
    print("\n\nTesting other tools with relative paths...")
    
    # Test find_files
    print("\n1. Testing find_files...")
    result = await plugin.find_files("*.py", max_results=5)
    if result['success']:
        files = result['data']['files']
        print(f"   Found {len(files)} files:")
        for f in files[:3]:
            print(f"   - {f}")
        if all(not f.startswith('consult/') for f in files):
            print("   ✅ Paths are relative (don't start with 'consult/')")
        else:
            print("   ❌ Some paths start with 'consult/'")
    
    # Test get_file_info on a known file
    print("\n2. Testing get_file_info...")
    result = await plugin.get_file_info("manage.py", include_preview=False)
    if result['success']:
        path = result['data']['path']
        print(f"   File path: {path}")
        if not path.startswith('consult/'):
            print("   ✅ Path is relative (doesn't start with 'consult/')")
        else:
            print("   ❌ Path starts with 'consult/'")


if __name__ == "__main__":
    asyncio.run(test_list_directory_fix())
    asyncio.run(test_relative_paths())