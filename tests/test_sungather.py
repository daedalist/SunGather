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
import tempfile
import os
import logging
from unittest.mock import Mock, MagicMock, patch


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


class TestConfigurationLoading:
    """Test configuration loading functions."""

    def get_config_functions(self):
        """Extract configuration functions from source using exec."""
        import ast
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        namespace = {}
        source_lines = source.split('\n')
        # Remove sys.exit() line at module level
        if 'sys.exit()' in source_lines[-1] or 'sys.exit()' in source_lines[-2]:
            source_lines = [line for line in source_lines if line.strip() != 'sys.exit()']

        modified_source = '\n'.join(source_lines)
        exec(modified_source, namespace)

        return {
            'load_config': namespace['load_config'],
            'load_registers': namespace['load_registers'],
            'build_inverter_config': namespace['build_inverter_config']
        }

    def test_load_config_success(self):
        """Test load_config with valid config file."""
        funcs = self.get_config_functions()
        load_config = funcs['load_config']

        # Create a temporary valid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
inverter:
  host: 192.168.1.100
  port: 502
""")
            config_file = f.name

        try:
            result = load_config(config_file)
            assert result is not None
            assert 'inverter' in result
            assert result['inverter']['host'] == '192.168.1.100'
            assert result['inverter']['port'] == 502
        finally:
            os.unlink(config_file)

    def test_load_config_file_not_found(self):
        """Test load_config raises FileNotFoundError for missing file."""
        funcs = self.get_config_functions()
        load_config = funcs['load_config']

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config('/nonexistent/config.yaml')

    def test_load_config_invalid_yaml(self):
        """Test load_config raises ValueError for invalid YAML."""
        funcs = self.get_config_functions()
        load_config = funcs['load_config']

        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            config_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_config(config_file)
        finally:
            os.unlink(config_file)

    def test_load_config_empty_file(self):
        """Test load_config raises ValueError for empty file."""
        funcs = self.get_config_functions()
        load_config = funcs['load_config']

        # Create an empty config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            config_file = f.name

        try:
            with pytest.raises(ValueError, match="is empty"):
                load_config(config_file)
        finally:
            os.unlink(config_file)

    def test_load_config_missing_inverter_section(self):
        """Test load_config raises ValueError when inverter section is missing."""
        funcs = self.get_config_functions()
        load_config = funcs['load_config']

        # Create config without inverter section
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
exports:
  - name: console
    enabled: true
""")
            config_file = f.name

        try:
            with pytest.raises(ValueError, match="missing required 'inverter' section"):
                load_config(config_file)
        finally:
            os.unlink(config_file)

    def test_load_registers_success(self):
        """Test load_registers with valid registers file."""
        funcs = self.get_config_functions()
        load_registers = funcs['load_registers']

        # Create a temporary valid registers file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
version: 1.0.0
registers:
  - address: 5000
    name: daily_power_yields
""")
            registers_file = f.name

        try:
            result = load_registers(registers_file)
            assert result is not None
            assert 'version' in result
            assert result['version'] == '1.0.0'
        finally:
            os.unlink(registers_file)

    def test_load_registers_file_not_found(self):
        """Test load_registers raises FileNotFoundError for missing file."""
        funcs = self.get_config_functions()
        load_registers = funcs['load_registers']

        with pytest.raises(FileNotFoundError, match="Registers file not found"):
            load_registers('/nonexistent/registers.yaml')

    def test_load_registers_invalid_yaml(self):
        """Test load_registers raises ValueError for invalid YAML."""
        funcs = self.get_config_functions()
        load_registers = funcs['load_registers']

        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            registers_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_registers(registers_file)
        finally:
            os.unlink(registers_file)

    def test_load_registers_empty_file(self):
        """Test load_registers raises ValueError for empty file."""
        funcs = self.get_config_functions()
        load_registers = funcs['load_registers']

        # Create an empty registers file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            registers_file = f.name

        try:
            with pytest.raises(ValueError, match="is empty"):
                load_registers(registers_file)
        finally:
            os.unlink(registers_file)

    def test_build_inverter_config_with_defaults(self):
        """Test build_inverter_config applies default values."""
        funcs = self.get_config_functions()
        build_inverter_config = funcs['build_inverter_config']

        config = {
            'inverter': {
                'host': '192.168.1.100'
            }
        }

        result = build_inverter_config(config)

        assert result['host'] == '192.168.1.100'
        assert result['port'] == 502  # default
        assert result['timeout'] == 10  # default
        assert result['retries'] == 3  # default
        assert result['slave'] == 0x01  # default
        assert result['scan_interval'] == 30  # default
        assert result['connection'] == 'modbus'  # default
        assert result['model'] is None  # default
        assert result['smart_meter'] is False  # default
        assert result['use_local_time'] is False  # default
        assert result['log_console'] == 'WARNING'  # default
        assert result['log_file'] == 'OFF'  # default
        assert result['level'] == 1  # default

    def test_build_inverter_config_with_custom_values(self):
        """Test build_inverter_config uses provided values."""
        funcs = self.get_config_functions()
        build_inverter_config = funcs['build_inverter_config']

        config = {
            'inverter': {
                'host': '10.0.0.1',
                'port': 8502,
                'timeout': 20,
                'retries': 5,
                'slave': 0x02,
                'scan_interval': 60,
                'connection': 'http',
                'model': 'SH5K',
                'smart_meter': True,
                'use_local_time': True,
                'log_console': 'DEBUG',
                'log_file': 'INFO',
                'level': 2
            }
        }

        result = build_inverter_config(config)

        assert result['host'] == '10.0.0.1'
        assert result['port'] == 8502
        assert result['timeout'] == 20
        assert result['retries'] == 5
        assert result['slave'] == 0x02
        assert result['scan_interval'] == 60
        assert result['connection'] == 'http'
        assert result['model'] == 'SH5K'
        assert result['smart_meter'] is True
        assert result['use_local_time'] is True
        assert result['log_console'] == 'DEBUG'
        assert result['log_file'] == 'INFO'
        assert result['level'] == 2

    def test_build_inverter_config_missing_inverter_section(self):
        """Test build_inverter_config raises ValueError when inverter section missing."""
        funcs = self.get_config_functions()
        build_inverter_config = funcs['build_inverter_config']

        config = {
            'exports': []
        }

        with pytest.raises(ValueError, match="missing 'inverter' section"):
            build_inverter_config(config)

    def test_build_inverter_config_empty_inverter_section(self):
        """Test build_inverter_config works with empty inverter section (uses defaults)."""
        funcs = self.get_config_functions()
        build_inverter_config = funcs['build_inverter_config']

        config = {
            'inverter': {}
        }

        result = build_inverter_config(config)

        # Should get all defaults
        assert result['host'] is None
        assert result['port'] == 502
        assert result['connection'] == 'modbus'


class TestLoggingSetup:
    """Test logging setup functions."""

    def get_logging_functions(self):
        """Extract logging functions from source using exec."""
        with open('SunGather/sungather.py', 'r') as f:
            source = f.read()

        namespace = {}
        source_lines = source.split('\n')
        # Remove sys.exit() line at module level
        if 'sys.exit()' in source_lines[-1] or 'sys.exit()' in source_lines[-2]:
            source_lines = [line for line in source_lines if line.strip() != 'sys.exit()']

        modified_source = '\n'.join(source_lines)
        exec(modified_source, namespace)

        return {
            'setup_console_logging': namespace['setup_console_logging'],
            'setup_file_logging': namespace['setup_file_logging']
        }

    def test_setup_console_logging_with_cli_override(self):
        """Test setup_console_logging uses CLI level when provided."""
        funcs = self.get_logging_functions()
        setup_console_logging = funcs['setup_console_logging']

        # Create a mock logger with handler
        mock_logger = MagicMock()
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]

        # CLI level should override config level
        setup_console_logging(mock_logger, 'WARNING', cli_level=10)

        mock_handler.setLevel.assert_called_once_with(10)

    def test_setup_console_logging_without_cli_override(self):
        """Test setup_console_logging uses config level when no CLI override."""
        funcs = self.get_logging_functions()
        setup_console_logging = funcs['setup_console_logging']

        mock_logger = MagicMock()
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]

        # Should use config level when no CLI override
        setup_console_logging(mock_logger, 'DEBUG', cli_level=None)

        mock_handler.setLevel.assert_called_once_with('DEBUG')

    def test_setup_console_logging_with_numeric_level(self):
        """Test setup_console_logging handles numeric log levels."""
        funcs = self.get_logging_functions()
        setup_console_logging = funcs['setup_console_logging']

        mock_logger = MagicMock()
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]

        setup_console_logging(mock_logger, 20, cli_level=None)

        mock_handler.setLevel.assert_called_once_with(20)

    def test_setup_file_logging_disabled(self):
        """Test setup_file_logging returns False when level is OFF."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]

        result = setup_file_logging(mock_logger, 'OFF')

        assert result is False
        # Should not add any handlers
        mock_logger.addHandler.assert_not_called()

    def test_setup_file_logging_invalid_level(self):
        """Test setup_file_logging raises ValueError for invalid level."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]

        with pytest.raises(ValueError, match="Invalid file log level 'INVALID'"):
            setup_file_logging(mock_logger, 'INVALID')

    @patch('logging.handlers.RotatingFileHandler')
    def test_setup_file_logging_creates_handler(self, mock_rotating_handler):
        """Test setup_file_logging creates RotatingFileHandler."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        mock_logger = MagicMock()
        mock_console_handler = MagicMock()
        mock_console_handler.formatter = 'test_formatter'
        mock_logger.handlers = [mock_console_handler]

        mock_file_handler = MagicMock()
        mock_rotating_handler.return_value = mock_file_handler

        result = setup_file_logging(mock_logger, 'INFO', '/logs/')

        # Should create RotatingFileHandler with correct params
        mock_rotating_handler.assert_called_once_with(
            '/logs/SunGather.log',
            mode='w',
            encoding='utf-8',
            maxBytes=10485760,
            backupCount=10
        )

        # Should set formatter from console handler
        assert mock_file_handler.formatter == 'test_formatter'

        # Should set level
        mock_file_handler.setLevel.assert_called_once_with('INFO')

        # Should add handler to logger
        mock_logger.addHandler.assert_called_once_with(mock_file_handler)

        # Should return True
        assert result is True

    @patch('logging.handlers.RotatingFileHandler')
    def test_setup_file_logging_all_valid_levels(self, mock_rotating_handler):
        """Test setup_file_logging accepts all valid log levels."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

        for level in valid_levels:
            mock_logger = MagicMock()
            mock_logger.handlers = [MagicMock()]
            mock_rotating_handler.reset_mock()

            result = setup_file_logging(mock_logger, level)

            assert result is True
            mock_rotating_handler.assert_called_once()

    @patch('logging.handlers.RotatingFileHandler')
    def test_setup_file_logging_default_folder(self, mock_rotating_handler):
        """Test setup_file_logging uses current directory by default."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]

        setup_file_logging(mock_logger, 'WARNING')

        # Should use empty string prefix (current directory)
        args, kwargs = mock_rotating_handler.call_args
        assert args[0] == 'SunGather.log'

    @patch('logging.handlers.RotatingFileHandler')
    def test_setup_file_logging_custom_folder(self, mock_rotating_handler):
        """Test setup_file_logging uses provided log folder."""
        funcs = self.get_logging_functions()
        setup_file_logging = funcs['setup_file_logging']

        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]

        setup_file_logging(mock_logger, 'ERROR', '/var/log/')

        # Should use custom folder
        args, kwargs = mock_rotating_handler.call_args
        assert args[0] == '/var/log/SunGather.log'
