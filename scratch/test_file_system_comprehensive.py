#!/usr/bin/env python3
"""
AI GENERATED. NOT CHECKED FOR CORRECTNESS OR ACCURACY.

Comprehensive Test Suite for FileSystemPlugin 
Tests all functions with various scenarios and formats outputs for qualitative analysis.

This test suite has been updated to work with the optimized FileSystemPlugin that 
returns token-efficient responses. It handles both old and new response formats 
for backward compatibility during testing.

This test suite captures and stores the complete raw tool responses in the JSON output
for detailed analysis of the tool response structure. Each test result includes a 
'raw_response' field containing the full unprocessed response from the FileSystemPlugin.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Import the plugin
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.file_system import FileSystemPlugin


class TestFormatter:
    """Formats test results for easy reading and analysis."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
    
    def print_header(self, title: str, level: int = 1):
        """Print a formatted header."""
        symbols = {1: "="*80, 2: "-"*60, 3: "."*40}
        symbol = symbols.get(level, "-"*40)
        
        print(f"\n{symbol}")
        print(f"{title:^80}" if level == 1 else title)
        print(symbol)
    
    def print_test_result(self, test_name: str, result: Dict[str, Any], 
                         description: str = "", show_full_data: bool = False):
        """Print formatted test result."""
        success = result.get('success', False)
        status_icon = "✅" if success else "❌"
        
        print(f"\n{status_icon} {test_name}")
        if description:
            print(f"   Description: {description}")
        
        print(f"   Success: {success}")
        
        if not success:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Show suggestions
        suggestions = result.get('suggestions', [])
        if suggestions:
            print(f"   Suggestions ({len(suggestions)}):")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"     {i}. {suggestion}")
            if len(suggestions) > 3:
                print(f"     ... and {len(suggestions) - 3} more")
        
        # Show metadata summary
        metadata = result.get('metadata', {})
        if metadata:
            key_items = []
            for key, value in metadata.items():
                if isinstance(value, (int, str, bool)):
                    key_items.append(f"{key}: {value}")
                elif isinstance(value, dict) and len(value) <= 3:
                    key_items.append(f"{key}: {value}")
            
            if key_items:
                print(f"   Metadata: {', '.join(key_items[:3])}")
        
        # Show data summary
        data = result.get('data', {})
        if data and success:
            if isinstance(data, dict):
                if 'count' in data:
                    print(f"   Results: {data['count']} items")
                elif 'files' in data:
                    files = data['files']
                    if isinstance(files, list):
                        print(f"   Files found: {len(files)}")
                        if files and len(files) > 0:
                            # For new format, files are just strings
                            if isinstance(files[0], str):
                                print(f"   Sample files: {files[:3]}")
                            else:
                                # Old format compatibility
                                file_types = {}
                                for f in files[:5]:
                                    ftype = f.get('type', 'unknown') if isinstance(f, dict) else 'unknown'
                                    file_types[ftype] = file_types.get(ftype, 0) + 1
                                print(f"   Sample types: {dict(file_types)}")
                elif 'matches_by_file' in data:
                    # New search format
                    matches_by_file = data['matches_by_file']
                    if isinstance(matches_by_file, dict):
                        total_matches = sum(len(matches) for matches in matches_by_file.values())
                        print(f"   Matches found: {total_matches} across {len(matches_by_file)} files")
                elif 'matches' in data:
                    # Old search format
                    matches = data['matches']
                    if isinstance(matches, list):
                        print(f"   Matches found: {len(matches)}")
                elif 'tree' in data:
                    # New directory tree format
                    tree = data['tree']
                    if isinstance(tree, str):
                        lines = tree.split('\n')
                        print(f"   Tree structure: {len(lines)} lines")
                        summary = data.get('summary', {})
                        print(f"   Contains: {summary.get('total_files', 0)} files, {summary.get('total_directories', 0)} dirs")
                elif 'structure' in data:
                    # Old directory format
                    structure = data['structure']
                    if isinstance(structure, dict):
                        print(f"   Directory: {structure.get('name', 'unknown')}")
                        summary = data.get('summary', {})
                        print(f"   Contains: {summary.get('total_files', 0)} files, {summary.get('total_directories', 0)} dirs")
                elif 'content' in data:
                    # File content
                    content = data['content']
                    if isinstance(content, str):
                        lines = len(content.split('\n'))
                        print(f"   Content: {lines} lines, {len(content)} characters")
                elif 'lines' in data:
                    # File lines
                    lines = data['lines']
                    if isinstance(lines, list):
                        print(f"   Lines: {len(lines)} lines returned")
                elif 'path' in data:
                    # File info
                    path = data['path']
                    size = data.get('size', 'unknown')
                    file_type = data.get('type', 'unknown')
                    print(f"   File: {path} ({size}, type: {file_type})")
        
        if show_full_data and data:
            print(f"\n   Full Data Preview:")
            print(f"   {json.dumps(data, indent=2)[:500]}...")
        
        # Store result for later analysis
        self.test_results.append({
            'test_name': test_name,
            'description': description,
            'success': success,
            'error': result.get('error'),
            'execution_time': time.time() - self.start_time,
            'data_size': len(str(data)) if data else 0,
            'suggestions_count': len(suggestions),
            'metadata_keys': list(metadata.keys()) if metadata else [],
            'raw_response': result  # Store the complete raw tool response
        })
    
    def print_summary(self):
        """Print test execution summary."""
        self.print_header("TEST EXECUTION SUMMARY", 1)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - successful_tests
        
        print(f"Total Tests:     {total_tests}")
        print(f"Successful:      {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"Failed:          {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"Total Time:      {time.time() - self.start_time:.2f} seconds")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test_name']}: {result['error']}")
        
        # Quality metrics
        self.print_header("QUALITY ANALYSIS", 2)
        
        avg_suggestions = sum(r['suggestions_count'] for r in self.test_results) / total_tests
        avg_data_size = sum(r['data_size'] for r in self.test_results) / total_tests
        
        print(f"Average suggestions per test: {avg_suggestions:.1f}")
        print(f"Average data size per response: {avg_data_size:.0f} characters")
        
        # Metadata analysis
        all_metadata_keys = []
        for result in self.test_results:
            all_metadata_keys.extend(result['metadata_keys'])
        
        from collections import Counter
        metadata_freq = Counter(all_metadata_keys)
        print(f"Most common metadata keys: {dict(metadata_freq.most_common(5))}")
        
        # Raw response structure analysis
        self.print_raw_response_analysis()
    
    def print_raw_response_analysis(self):
        """Analyze and print summary of raw response structures."""
        self.print_header("RAW RESPONSE STRUCTURE ANALYSIS", 2)
        
        # Analyze response structure patterns
        response_structures = {}
        data_field_types = {}
        
        for result in self.test_results:
            raw_response = result.get('raw_response', {})
            
            # Analyze top-level structure
            top_level_keys = tuple(sorted(raw_response.keys()))
            response_structures[top_level_keys] = response_structures.get(top_level_keys, 0) + 1
            
            # Analyze data field structure
            data = raw_response.get('data', {})
            if isinstance(data, dict):
                data_keys = tuple(sorted(data.keys()))
                data_field_types[data_keys] = data_field_types.get(data_keys, 0) + 1
        
        print(f"Response structure patterns:")
        for structure, count in sorted(response_structures.items(), key=lambda x: x[1], reverse=True):
            print(f"  {count}x: {list(structure)}")
        
        print(f"\nData field patterns:")
        for structure, count in sorted(data_field_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {count}x: {list(structure)}")
        
        # Sample raw response for reference
        if self.test_results:
            sample_response = self.test_results[0].get('raw_response', {})
            print(f"\nSample raw response structure:")
            print(f"  Keys: {list(sample_response.keys())}")
            if 'data' in sample_response and isinstance(sample_response['data'], dict):
                print(f"  Data keys: {list(sample_response['data'].keys())}")
            if 'metadata' in sample_response and isinstance(sample_response['metadata'], dict):
                print(f"  Metadata keys: {list(sample_response['metadata'].keys())}")
    
    def save_results(self, filename: str):
        """Save detailed results to JSON file."""
        output = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'total_time': time.time() - self.start_time,
                'total_tests': len(self.test_results),
                'successful_tests': sum(1 for r in self.test_results if r['success']),
                'note': 'Each test result includes a raw_response field with the complete tool response structure'
            },
            'test_results': self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {filename}")
        print(f"   ℹ️  Raw tool responses are included in the 'raw_response' field of each test result")
        print(f"\n📋 JSON Structure Preview:")
        print(f"   {{")
        print(f"     'test_execution': {{ timestamp, total_time, total_tests, successful_tests, note }},")
        print(f"     'test_results': [")
        print(f"       {{")
        print(f"         'test_name': str,")
        print(f"         'description': str,")
        print(f"         'success': bool,")
        print(f"         'error': str|None,")
        print(f"         'execution_time': float,")
        print(f"         'data_size': int,")
        print(f"         'suggestions_count': int,")
        print(f"         'metadata_keys': [str],")
        print(f"         'raw_response': {{ complete_tool_response }}")
        print(f"       }}, ...")
        print(f"     ]")
        print(f"   }}")


class FileSystemPluginTester:
    """Comprehensive tester for FileSystemPlugin."""
    
    def __init__(self, base_path: str = None):
        self.plugin = FileSystemPlugin(base_path=base_path)
        self.formatter = TestFormatter()
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        self.formatter.print_header("FileSystemPlugin v2 - Comprehensive Test Suite", 1)
        print(f"Base Path: {self.base_path}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run test categories
        await self.test_find_files()
        await self.test_list_directory()
        await self.test_read_file()
        await self.test_search_in_files()
        await self.test_get_file_info()
        await self.test_error_scenarios()
        await self.test_edge_cases()
        
        # Show summary
        self.formatter.print_summary()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.formatter.save_results(f"test_results_file_system_plugin_{timestamp}.json")
    
    async def test_find_files(self):
        """Test find_files function with various patterns."""
        self.formatter.print_header("Testing find_files Function", 2)
        
        test_cases = [
            ("*.py", ".", "Find Python files in current directory"),
            ("**/*.py", ".", "Find Python files recursively"),
            ("**/*.json", ".", "Find JSON config files"),
            ("**/*.tf", ".", "Find Terraform files"),
            ("**/test_*.py", ".", "Find test files"),
            ("**/*.{md,txt}", ".", "Find documentation files (Note: will test multiple patterns)"),
            ("nonexistent/*", ".", "Pattern with no matches"),
            ("*.py", "consult", "Find Python files in specific directory"),
        ]
        
        for pattern, search_path, description in test_cases:
            try:
                if pattern == "**/*.{md,txt}":
                    # Test multiple patterns since glob doesn't support {a,b} syntax
                    result1 = await self.plugin.find_files("**/*.md", search_path, max_results=10)
                    result2 = await self.plugin.find_files("**/*.txt", search_path, max_results=10)
                    
                    # Combine results for analysis
                    combined_count = 0
                    if result1.get('success'):
                        combined_count += result1.get('data', {}).get('count', 0)
                    if result2.get('success'):
                        combined_count += result2.get('data', {}).get('count', 0)
                    
                    # Show the more successful result
                    result = result1 if result1.get('success') else result2
                    self.formatter.print_test_result(
                        f"find_files('{pattern}', '{search_path}')",
                        result,
                        f"{description} (Combined: {combined_count} files)"
                    )
                else:
                    result = await self.plugin.find_files(pattern, search_path, max_results=20)
                    self.formatter.print_test_result(
                        f"find_files('{pattern}', '{search_path}')",
                        result,
                        description
                    )
            
            except Exception as e:
                print(f"❌ Exception in find_files test: {e}")
    
    async def test_list_directory(self):
        """Test list_directory function."""
        self.formatter.print_header("Testing list_directory Function", 2)
        
        test_cases = [
            (".", 2, False, "List current directory (depth 2)"),
            (".", 1, False, "List current directory (depth 1)"),
            ("consult", 2, False, "List consult directory"),
            ("tools", 1, False, "List tools directory"),
            (".", 3, True, "List with hidden files"),
            ("nonexistent", 1, False, "Non-existent directory"),
        ]
        
        for path, max_depth, include_hidden, description in test_cases:
            try:
                result = await self.plugin.list_directory(
                    path, max_depth=max_depth, include_hidden=include_hidden, max_entries=50
                )
                self.formatter.print_test_result(
                    f"list_directory('{path}', depth={max_depth}, hidden={include_hidden})",
                    result,
                    description
                )
                
                # Show tree output for successful results
                if result.get('success') and 'tree' in result.get('data', {}):
                    tree = result['data']['tree']
                    if isinstance(tree, str) and tree.strip():
                        print(f"   Tree Preview:")
                        tree_lines = tree.split('\n')[:8]  # Show first 8 lines
                        for line in tree_lines:
                            print(f"     {line}")
                        total_lines = len(tree.split('\n'))
                        if total_lines > 8:
                            print(f"     ... ({total_lines - 8} more lines)")
            except Exception as e:
                print(f"❌ Exception in list_directory test: {e}")
    
    async def test_read_file(self):
        """Test read_file function."""
        self.formatter.print_header("Testing read_file Function", 2)
        
        # Find some existing files to test with
        py_files_result = await self.plugin.find_files("*.py", ".", max_results=3)
        json_files_result = await self.plugin.find_files("**/*.json", ".", max_results=2)
        
        test_files = []
        
        # Add found Python files
        if py_files_result.get('success'):
            files = py_files_result.get('data', {}).get('files', [])
            # Handle both old and new formats
            if files and isinstance(files[0], str):
                # New format: files are just strings
                test_files.extend(files[:2])
            elif files and isinstance(files[0], dict):
                # Old format: files are objects with path
                test_files.extend([f['path'] for f in files[:2]])
        
        # Add found JSON files
        if json_files_result.get('success'):
            files = json_files_result.get('data', {}).get('files', [])
            # Handle both old and new formats
            if files and isinstance(files[0], str):
                # New format: files are just strings
                test_files.extend(files[:1])
            elif files and isinstance(files[0], dict):
                # Old format: files are objects with path
                test_files.extend([f['path'] for f in files[:1]])
        
        # Add some common files that might exist
        common_files = ["requirements.txt", "README.md", "plan.md"]
        for file in common_files:
            if (self.base_path / file).exists():
                test_files.append(file)
        
        test_cases = [
            # Regular file reading (0 means "not specified" in the plugin)
            *[(f, 0, 0, f"Read entire file: {f}") for f in test_files[:3]],
            # Line-based reading
            *[(f, 1, 10, f"Read first 10 lines: {f}") for f in test_files[:2]],
            # Error cases
            ("nonexistent.txt", 0, 0, "Non-existent file"),
            (".", 0, 0, "Try to read directory as file"),
        ]
        
        for file_path, start_line, num_lines, description in test_cases:
            try:
                # Only pass start_line and num_lines if they're not 0
                if start_line == 0 and num_lines == 0:
                    result = await self.plugin.read_file(file_path)
                else:
                    result = await self.plugin.read_file(
                        file_path, start_line=start_line, num_lines=num_lines
                    )
                self.formatter.print_test_result(
                    f"read_file('{file_path}', start={start_line}, lines={num_lines})",
                    result,
                    description
                )
            except Exception as e:
                print(f"❌ Exception in read_file test: {e}")
    
    async def test_search_in_files(self):
        """Test search_in_files function."""
        self.formatter.print_header("Testing search_in_files Function", 2)
        
        test_cases = [
            ("import", ["*.py"], ".", True, "Find import statements in Python files"),
            ("class.*:", ["**/*.py"], ".", True, "Find class definitions"),
            ("def ", ["**/*.py"], ".", True, "Find function definitions"),
            ("TODO|FIXME", ["**/*.py", "**/*.js"], ".", False, "Find TODO/FIXME comments (case insensitive)"),
            ("FileSystemPlugin", ["**/*.py"], ".", True, "Find specific class name"),
            ("nonexistentpattern123", ["*.py"], ".", True, "Pattern with no matches"),
            ("invalid[regex", ["*.py"], ".", True, "Invalid regex pattern"),
            ("async def", ["**/*.py"], ".", True, "Find async functions"),
        ]
        
        for pattern, file_patterns, search_path, case_sensitive, description in test_cases:
            try:
                result = await self.plugin.search_in_files(
                    pattern, file_patterns, search_path, 
                    case_sensitive=case_sensitive, max_results=15
                )
                self.formatter.print_test_result(
                    f"search_in_files('{pattern}', {file_patterns}, case_sensitive={case_sensitive})",
                    result,
                    description
                )
            except Exception as e:
                print(f"❌ Exception in search_in_files test: {e}")
    
    async def test_get_file_info(self):
        """Test get_file_info function."""
        self.formatter.print_header("Testing get_file_info Function", 2)
        
        # Find some files to test
        files_result = await self.plugin.find_files("*", ".", max_results=5)
        test_files = []
        
        if files_result.get('success'):
            files = files_result.get('data', {}).get('files', [])
            # Handle both old and new formats
            if files and isinstance(files[0], str):
                # New format: files are just strings
                test_files = files[:3]
            elif files and isinstance(files[0], dict):
                # Old format: files are objects with path
                test_files = [f['path'] for f in files[:3]]
        
        # Add some specific files that might exist
        potential_files = ["requirements.txt", "tools/file_system.py", "plan.md"]
        for file in potential_files:
            if (self.base_path / file).exists():
                test_files.append(file)
        
        test_cases = [
            *[(f, True, 5, f"Get info with preview: {f}") for f in test_files[:3]],
            *[(f, False, 0, f"Get info without preview: {f}") for f in test_files[3:5]],
            ("nonexistent.file", True, 5, "Non-existent file"),
            (".", True, 5, "Try to get info on directory"),
        ]
        
        for file_path, include_preview, preview_lines, description in test_cases:
            try:
                result = await self.plugin.get_file_info(
                    file_path, include_preview=include_preview, preview_lines=preview_lines
                )
                self.formatter.print_test_result(
                    f"get_file_info('{file_path}', preview={include_preview})",
                    result,
                    description
                )
            except Exception as e:
                print(f"❌ Exception in get_file_info test: {e}")
    
    async def test_error_scenarios(self):
        """Test various error scenarios."""
        self.formatter.print_header("Testing Error Handling", 2)
        
        error_tests = [
            # find_files errors
            ("find_files", ["invalid**pattern", ".", 10], "Invalid glob pattern"),
            ("find_files", ["*.py", "nonexistent_dir", 10], "Non-existent search directory"),
            
            # list_directory errors
            ("list_directory", ["nonexistent_dir"], "Non-existent directory"),
            ("list_directory", ["requirements.txt"], "File instead of directory"),
            
            # read_file errors
            ("read_file", ["nonexistent.txt"], "Non-existent file"),
            ("read_file", ["."], "Directory instead of file"),
            
            # search_in_files errors
            ("search_in_files", ["[invalid", ["*.py"]], "Invalid regex"),
            ("search_in_files", ["test", ["*.py"], "nonexistent_dir"], "Non-existent search dir"),
            
            # get_file_info errors
            ("get_file_info", ["nonexistent.txt"], "Non-existent file for info"),
            ("get_file_info", ["."], "Directory instead of file for info"),
        ]
        
        for func_name, args, description in error_tests:
            try:
                func = getattr(self.plugin, func_name)
                result = await func(*args)
                self.formatter.print_test_result(
                    f"{func_name}({args})",
                    result,
                    f"Error case: {description}"
                )
            except Exception as e:
                print(f"❌ Exception in error test {func_name}: {e}")
    
    async def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        self.formatter.print_header("Testing Edge Cases", 2)
        
        edge_cases = [
            # Large result sets
            ("find_files", ["**/*", ".", 5], "Large result set with limit"),
            ("find_files", ["**/*", ".", 1000], "Large result set with high limit"),
            
            # Empty patterns
            ("find_files", ["", "."], "Empty pattern"),
            
            # Deep directory traversal
            ("list_directory", [".", 5, False, 10], "Deep directory traversal"),
            
            # Search edge cases
            ("search_in_files", [".", ["**/*.py"], ".", True, 5], "Search for single character"),
            ("search_in_files", [".*", ["**/*.py"], ".", True, 3], "Search for regex any character"),
        ]
        
        for func_name, args, description in edge_cases:
            try:
                func = getattr(self.plugin, func_name)
                result = await func(*args)
                self.formatter.print_test_result(
                    f"{func_name}({args[:2]}...)",
                    result,
                    f"Edge case: {description}"
                )
            except Exception as e:
                print(f"❌ Exception in edge case {func_name}: {e}")


async def main():
    """Main test execution function."""
    import sys
    
    # Set base path to the consult directory for testing
    base_path = "/home/agangwal/lseg-migration-agent/migration-agent/consult"
    
    print("🧪 Starting FileSystemPlugin Comprehensive Test Suite")
    print(f"📁 Testing in: {base_path}")
    
    tester = FileSystemPluginTester(base_path=base_path)
    
    try:
        await tester.run_all_tests()
        print("\n✅ All tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
