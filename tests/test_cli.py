"""Tests for prestoplot.cli module."""

from __future__ import annotations

import logging
import pathlib
import sys
import tempfile
import textwrap
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from prestoplot import cli


class TestMainGroup:
    """Tests for the main CLI group command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def test_main_help(self, runner: CliRunner) -> None:
        """Test main command shows help."""
        result = runner.invoke(cli.main, ['--help'])
        assert result.exit_code == 0
        assert 'Main CLI group for PrestoPlot commands' in result.output
        assert '--debug' in result.output
        assert '--pdb' in result.output

    def test_main_debug_flag(self, runner: CliRunner) -> None:
        """Test main command with debug flag sets logging level."""
        # Create a temporary YAML file for testing
        content = textwrap.dedent("""
            Begin:
              - "Test"
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            with patch('prestoplot.cli.logging.basicConfig') as mock_config:
                result = runner.invoke(cli.main, ['--debug', 'run', str(temp_path)])
                assert result.exit_code == 0
                mock_config.assert_called_once_with(level=logging.DEBUG)
        finally:
            temp_path.unlink()

    def test_main_no_debug_flag(self, runner: CliRunner) -> None:
        """Test main command without debug flag sets info logging."""
        # Create a temporary YAML file for testing
        content = textwrap.dedent("""
            Begin:
              - "Test"
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            with patch('prestoplot.cli.logging.basicConfig') as mock_config:
                result = runner.invoke(cli.main, ['run', str(temp_path)])
                assert result.exit_code == 0
                mock_config.assert_called_once_with(level=logging.INFO)
        finally:
            temp_path.unlink()

    def test_main_pdb_flag_registers_atexit(self, runner: CliRunner) -> None:
        """Test main command with pdb flag registers exit handler."""
        # Create a temporary YAML file for testing
        content = textwrap.dedent("""
            Begin:
              - "Test"
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            with patch('prestoplot.cli.atexit.register') as mock_register:
                result = runner.invoke(cli.main, ['--pdb', 'run', str(temp_path)])
                assert result.exit_code == 0
                mock_register.assert_called_once()
        finally:
            temp_path.unlink()

    def test_main_pdb_debug_function(self, runner: CliRunner) -> None:
        """Test pdb debug function enters debugger when traceback exists."""
        # Create a temporary YAML file for testing
        content = textwrap.dedent("""
            Begin:
              - "Test"
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            with (
                patch('prestoplot.cli.atexit.register') as mock_register,
                patch('pdb.pm') as mock_pm,
            ):
                result = runner.invoke(cli.main, ['--pdb', 'run', str(temp_path)])
                assert result.exit_code == 0

                # Get the registered function
                debug_on_exit = mock_register.call_args[0][0]

                # Test when last_traceback exists
                sys.last_traceback = Mock()
                debug_on_exit()
                mock_pm.assert_called_once()

                # Clean up
                del sys.last_traceback
        finally:
            temp_path.unlink()


class TestRunCommand:
    """Tests for the run command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def test_yaml_file(self) -> pathlib.Path:
        """Create a temporary YAML test file."""
        content = textwrap.dedent("""
            Begin:
              - "Hello {Name}!"

            Name:
              - World
              - Universe
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            return pathlib.Path(f.name)

    @pytest.fixture
    def characters_yaml_path(self) -> pathlib.Path:
        """Path to the test characters.yaml file."""
        return pathlib.Path(__file__).parent / 'data' / 'characters.yaml'

    def test_run_help(self, runner: CliRunner) -> None:
        """Test run command shows help."""
        result = runner.invoke(cli.run, ['--help'])
        assert result.exit_code == 0
        assert (
            'Parse and consult a YAML generative grammar oracle file' in result.output
        )
        assert '--count' in result.output
        assert '--markov-start' in result.output
        assert '--markov-chainlen' in result.output
        assert '--wrap' in result.output
        assert '--wrap-length' in result.output
        assert '--seed' in result.output

    def test_run_basic_execution(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test basic run command execution."""
        try:
            result = runner.invoke(cli.run, [str(test_yaml_file)])
            assert result.exit_code == 0
            assert 'Hello' in result.output
            assert 'World' in result.output or 'Universe' in result.output
        finally:
            test_yaml_file.unlink()

    def test_run_with_count(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test run command with count parameter."""
        try:
            result = runner.invoke(cli.run, [str(test_yaml_file), '--count', '3'])
            assert result.exit_code == 0
            # Should have separators between outputs
            assert result.output.count('---') == 2
        finally:
            test_yaml_file.unlink()

    def test_run_with_seed(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test run command with seed for reproducible output."""
        try:
            result1 = runner.invoke(cli.run, [str(test_yaml_file), '--seed', 'test123'])
            result2 = runner.invoke(cli.run, [str(test_yaml_file), '--seed', 'test123'])
            assert result1.exit_code == 0
            assert result2.exit_code == 0
            assert result1.output == result2.output
        finally:
            test_yaml_file.unlink()

    def test_run_with_wrap(self, runner: CliRunner) -> None:
        """Test run command with text wrapping."""
        content = textwrap.dedent("""
            Begin:
              - "This is a very long line that should be wrapped when the wrap option is enabled because it exceeds the default wrap length of 78 characters."
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            # Test without wrap
            result_no_wrap = runner.invoke(cli.run, [str(temp_path)])
            assert result_no_wrap.exit_code == 0

            # Test with wrap
            result_wrap = runner.invoke(
                cli.run, [str(temp_path), '--wrap', '--wrap-length', '40']
            )
            assert result_wrap.exit_code == 0

            # Wrapped version should have more lines
            assert len(result_wrap.output.splitlines()) > len(
                result_no_wrap.output.splitlines()
            )
        finally:
            temp_path.unlink()

    def test_run_markov_validation_error(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test run command with invalid markov parameters."""
        try:
            result = runner.invoke(
                cli.run,
                [str(test_yaml_file), '--markov-start', 'A', '--markov-chainlen', '3'],
            )
            assert result.exit_code != 0
            assert (
                '--markov-start must be at least as long as --markov-chainlen'
                in result.output
            )
        finally:
            test_yaml_file.unlink()

    def test_run_markov_valid_parameters(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test run command with valid markov parameters."""
        try:
            result = runner.invoke(
                cli.run,
                [
                    str(test_yaml_file),
                    '--markov-start',
                    'ABC',
                    '--markov-chainlen',
                    '2',
                ],
            )
            assert result.exit_code == 0
        finally:
            test_yaml_file.unlink()

    def test_run_nonexistent_file(self, runner: CliRunner) -> None:
        """Test run command with nonexistent file."""
        result = runner.invoke(cli.run, ['/nonexistent/file.yaml'])
        assert result.exit_code != 0

    def test_run_with_characters_file(
        self, runner: CliRunner, characters_yaml_path: pathlib.Path
    ) -> None:
        """Test run command with the actual characters.yaml test file."""
        if characters_yaml_path.exists():
            result = runner.invoke(cli.run, [str(characters_yaml_path)])
            assert result.exit_code == 0
            assert len(result.output.strip()) > 0


class TestHttpCommand:
    """Tests for the http command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def test_yaml_file(self) -> pathlib.Path:
        """Create a temporary YAML test file."""
        content = textwrap.dedent("""
            Begin:
              - "Hello {Name}!"

            Name:
              - World
              - Universe
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            return pathlib.Path(f.name)

    def test_http_help(self, runner: CliRunner) -> None:
        """Test http command shows help."""
        result = runner.invoke(cli.http, ['--help'])
        assert result.exit_code == 0
        assert (
            'Parse a YAML generative grammar oracle file and serve it' in result.output
        )
        assert '--markov-start' in result.output
        assert '--markov-chainlen' in result.output
        assert '--port' in result.output

    def test_http_markov_validation_error(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test http command with invalid markov parameters."""
        try:
            result = runner.invoke(
                cli.http,
                [str(test_yaml_file), '--markov-start', 'A', '--markov-chainlen', '3'],
            )
            assert result.exit_code != 0
            assert (
                '--markov-start must be at least as long as --markov-chainlen'
                in result.output
            )
        finally:
            test_yaml_file.unlink()

    def test_http_server_setup(
        self,
        runner: CliRunner,
        test_yaml_file: pathlib.Path,
    ) -> None:
        """Test http command sets up server correctly."""
        try:
            with (
                patch('http.server.HTTPServer') as mock_http_server,
                patch('prestoplot.http.create_handler') as mock_create_handler,
                patch('prestoplot.cli.logging.basicConfig') as mock_logging,
                patch('prestoplot.cli.click.echo') as mock_echo,
            ):
                mock_handler = Mock()
                mock_create_handler.return_value = mock_handler
                mock_server_instance = Mock()
                mock_http_server.return_value = mock_server_instance

                # We need to patch serve_forever to prevent infinite loop
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()

                runner.invoke(cli.http, [str(test_yaml_file), '--port', '8080'])

                # Check that logging was configured
                mock_logging.assert_called_once()

                # Check that server was created with correct parameters
                mock_http_server.assert_called_once_with(('', 8080), mock_handler)

                # Check that appropriate message was echoed
                mock_echo.assert_called_with('Serving on http://localhost:8080')

                # Check that serve_forever was called
                mock_server_instance.serve_forever.assert_called_once()
        finally:
            test_yaml_file.unlink()

    def test_http_with_custom_markov_parameters(
        self, runner: CliRunner, test_yaml_file: pathlib.Path
    ) -> None:
        """Test http command with custom markov parameters."""
        try:
            with (
                patch('http.server.HTTPServer') as mock_server,
                patch('prestoplot.http.create_handler') as mock_handler,
            ):
                mock_server_instance = Mock()
                mock_server.return_value = mock_server_instance
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
                mock_handler.return_value = Mock()

                runner.invoke(
                    cli.http,
                    [
                        str(test_yaml_file),
                        '--markov-start',
                        'ABC',
                        '--markov-chainlen',
                        '3',
                        '--port',
                        '9090',
                    ],
                )

                # Should not error out due to markov validation
                mock_server.assert_called_once_with(
                    ('', 9090), mock_handler.return_value
                )
        finally:
            test_yaml_file.unlink()

    def test_http_nonexistent_file(self, runner: CliRunner) -> None:
        """Test http command with nonexistent file."""
        result = runner.invoke(cli.http, ['/nonexistent/file.yaml'])
        assert result.exit_code != 0


class TestCliIntegration:
    """Integration tests for the CLI module."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def characters_yaml_path(self) -> pathlib.Path:
        """Path to the test characters.yaml file."""
        return pathlib.Path(__file__).parent / 'data' / 'characters.yaml'

    def test_main_group_subcommands(self, runner: CliRunner) -> None:
        """Test that main group includes both run and http commands."""
        result = runner.invoke(cli.main, ['--help'])
        assert result.exit_code == 0
        assert 'run' in result.output
        assert 'http' in result.output

    def test_run_command_with_all_options(
        self, runner: CliRunner, characters_yaml_path: pathlib.Path
    ) -> None:
        """Test run command with all options specified."""
        # Create a simpler YAML file for testing all options
        content = textwrap.dedent("""
            Begin:
              - "Character: {Name}, Weapon: {Weapon}"

            Name:
              - Alice
              - Bob
              - Charlie

            Weapon:
              - Sword
              - Bow
              - Staff
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            result = runner.invoke(
                cli.run,
                [
                    str(temp_path),
                    '--count',
                    '2',
                    '--wrap',
                    '--wrap-length',
                    '50',
                    '--seed',
                    'integration-test',
                ],
            )
            assert result.exit_code == 0
            # Should have one separator between two outputs
            assert result.output.count('---') == 1
        finally:
            temp_path.unlink()

    def test_commands_preserve_working_directory(self, runner: CliRunner) -> None:
        """Test that CLI commands don't change working directory."""
        original_cwd = pathlib.Path.cwd()

        # Create a temporary YAML file
        content = textwrap.dedent("""
            Begin:
              - "Test"
        """).strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(content)
            temp_path = pathlib.Path(f.name)

        try:
            runner.invoke(cli.run, [str(temp_path)])
            assert pathlib.Path.cwd() == original_cwd
        finally:
            temp_path.unlink()

    def test_error_handling_preserves_exit_codes(self, runner: CliRunner) -> None:
        """Test that CLI properly propagates error exit codes."""
        # Test with nonexistent file
        result = runner.invoke(cli.run, ['/definitely/does/not/exist.yaml'])
        assert result.exit_code != 0

        # Test with invalid markov parameters
        with tempfile.NamedTemporaryFile(suffix='.yaml') as f:
            result = runner.invoke(
                cli.run, [f.name, '--markov-start', 'X', '--markov-chainlen', '5']
            )
            assert result.exit_code != 0
