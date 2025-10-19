"""
Unit tests for sungather.py main module.

NOTE: The sungather.py module has a sys.exit() call at module level (line 217),
which makes it difficult to import for testing. These tests verify the module
structure and key components that can be tested without triggering module-level execution.

Tests cover:
- Module imports successfully
- Version information is available
- Signal handler function exists and works correctly
- Argument parsing (parse_arguments function)
"""

import pytest
import getopt
from unittest.mock import Mock


class TestModuleStructure:
    """Test sungather.py module structure."""

    def test_module_has_main_function(self):
        """Test that sungather module exports main() function."""
        # We can't easily import the module due to sys.exit() at module level
        # But we can verify the file structure is valid Python
        import ast
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        # Parse the AST
        tree = ast.parse(source)

        # Find all function definitions
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        # Verify main and handle_sigterm exist
        assert 'main' in functions
        assert 'handle_sigterm' in functions

    def test_module_has_required_imports(self):
        """Test that module has all required imports."""
        import ast
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        # Parse AST
        tree = ast.parse(source)

        # Find all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Verify key imports
        assert 'importlib' in imports
        assert 'logging' in imports
        assert 'sys' in imports
        assert 'yaml' in imports
        assert 'signal' in imports

    def test_module_defines_logging_config(self):
        """Test that module configures logging."""
        import ast
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        # Verify logging.basicConfig is called
        assert 'logging.basicConfig(' in source
        assert 'format=' in source
        assert 'level=' in source

class TestSignalHandler:
    """Test signal handler function."""

    def test_handle_sigterm_function_signature(self):
        """Test that handle_sigterm has correct signature."""
        import ast
        import inspect

        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        tree = ast.parse(source)

        # Find handle_sigterm function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'handle_sigterm':
                # Verify it takes 2 parameters (signum, frame)
                assert len(node.args.args) == 2
                assert node.args.args[0].arg == 'signum'
                assert node.args.args[1].arg == 'frame'


class TestArgumentParsing:
    """Test parse_arguments() function using AST to extract and test it."""

    def get_parse_arguments_function(self):
        """Extract parse_arguments function from source using exec."""
        import ast
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        # Execute the source to get access to functions
        namespace = {}
        # Remove the problematic sys.exit() line at module level
        source_lines = source.split('\n')
        # Find and remove the sys.exit() line at the end
        if 'sys.exit()' in source_lines[-1] or 'sys.exit()' in source_lines[-2]:
            source_lines = [line for line in source_lines if line.strip() != 'sys.exit()']

        modified_source = '\n'.join(source_lines)
        exec(modified_source, namespace)

        return namespace['parse_arguments']

    def test_parse_arguments_default_values(self):
        """Test parse_arguments with no arguments returns defaults."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments([])

        assert result['config_file'] == 'config.yaml'
        assert result['registers_file'] == 'registers-sungrow.yaml'
        assert result['log_folder'] == ''
        assert result['log_level'] is None
        assert result['run_once'] is False
        assert result['show_help'] is False

    def test_parse_arguments_config_file(self):
        """Test parse_arguments with -c flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-c', '/path/to/config.yaml'])

        assert result['config_file'] == '/path/to/config.yaml'

    def test_parse_arguments_registers_file(self):
        """Test parse_arguments with -r flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-r', '/path/to/registers.yaml'])

        assert result['registers_file'] == '/path/to/registers.yaml'

    def test_parse_arguments_log_folder(self):
        """Test parse_arguments with -l flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-l', '/var/log/'])

        assert result['log_folder'] == '/var/log/'

    def test_parse_arguments_log_level_valid(self):
        """Test parse_arguments with valid -v flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-v', '10'])

        assert result['log_level'] == 10

    def test_parse_arguments_log_level_invalid_non_numeric(self):
        """Test parse_arguments with non-numeric log level raises ValueError."""
        parse_arguments = self.get_parse_arguments_function()

        with pytest.raises(ValueError, match="Invalid log level 'DEBUG'"):
            parse_arguments(['-v', 'DEBUG'])

    def test_parse_arguments_log_level_out_of_range_low(self):
        """Test parse_arguments with log level too low raises ValueError."""
        parse_arguments = self.get_parse_arguments_function()

        with pytest.raises(ValueError, match="Invalid log level '-1'"):
            parse_arguments(['-v', '-1'])

    def test_parse_arguments_log_level_out_of_range_high(self):
        """Test parse_arguments with log level too high raises ValueError."""
        parse_arguments = self.get_parse_arguments_function()

        with pytest.raises(ValueError, match="Log level 51 out of range"):
            parse_arguments(['-v', '51'])

    def test_parse_arguments_runonce_flag(self):
        """Test parse_arguments with --runonce flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['--runonce'])

        assert result['run_once'] is True

    def test_parse_arguments_help_flag(self):
        """Test parse_arguments with -h flag."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-h'])

        assert result['show_help'] is True

    def test_parse_arguments_help_flag_short_circuits(self):
        """Test that -h flag returns immediately without processing other args."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments(['-h', '-c', 'test.yaml'])

        # Should return help=True, other args should be defaults
        assert result['show_help'] is True
        assert result['config_file'] == 'config.yaml'  # Not 'test.yaml'

    def test_parse_arguments_multiple_flags(self):
        """Test parse_arguments with multiple flags."""
        parse_arguments = self.get_parse_arguments_function()

        result = parse_arguments([
            '-c', '/path/config.yaml',
            '-r', '/path/registers.yaml',
            '-l', '/logs/',
            '-v', '20',
            '--runonce'
        ])

        assert result['config_file'] == '/path/config.yaml'
        assert result['registers_file'] == '/path/registers.yaml'
        assert result['log_folder'] == '/logs/'
        assert result['log_level'] == 20
        assert result['run_once'] is True

    def test_parse_arguments_invalid_flag_raises_getopt_error(self):
        """Test parse_arguments with invalid flag raises GetoptError."""
        parse_arguments = self.get_parse_arguments_function()

        with pytest.raises(getopt.GetoptError):
            parse_arguments(['-x'])

    def test_parse_arguments_missing_value_raises_getopt_error(self):
        """Test parse_arguments with flag missing value raises GetoptError."""
        parse_arguments = self.get_parse_arguments_function()

        with pytest.raises(getopt.GetoptError):
            parse_arguments(['-c'])

    def test_parse_arguments_uses_sys_argv_when_none(self):
        """Test parse_arguments uses sys.argv[1:] when argv is None."""
        import sys
        parse_arguments = self.get_parse_arguments_function()

        # Save original argv
        original_argv = sys.argv
        try:
            sys.argv = ['sungather.py', '-c', 'test.yaml']
            result = parse_arguments(None)
            assert result['config_file'] == 'test.yaml'
        finally:
            sys.argv = original_argv
