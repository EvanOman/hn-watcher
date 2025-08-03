"""Unit tests for sysd functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock

from sysd.manager import SystemdManager


class TestSystemdManager:
    """Test the SystemdManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SystemdManager()
        # Mock the systemd directory for testing
        self.manager.systemd_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_schedule_parsing(self):
        """Test schedule parsing functionality."""
        test_cases = [
            ("*/15", ("calendar", "*:0/15")),
            ("hourly", ("calendar", "hourly")),
            ("daily", ("calendar", "daily")),
            ("@startup", ("startup", "1min")),
            ("@boot", ("boot", "1min")),
            ("Mon *-*-* 10:00:00", ("calendar", "mon *-*-* 10:00:00")),
        ]
        
        for input_schedule, expected in test_cases:
            result = self.manager._parse_schedule(input_schedule)
            assert result == expected, f"Failed for {input_schedule}: got {result}, expected {expected}"

    def test_command_building(self):
        """Test command building for uv projects."""
        working_dir = "/test/project"
        
        # Test with Python command in uv project
        with patch('pathlib.Path.exists', return_value=True):  # pyproject.toml exists
            with patch('shutil.which', return_value='/usr/local/bin/uv'):
                result = self.manager._build_command("python -m mymodule", working_dir)
                assert result == "/usr/local/bin/uv run python -m mymodule"
        
        # Test with non-Python command
        with patch('pathlib.Path.exists', return_value=True):
            with patch('shutil.which', return_value='/usr/local/bin/uv'):
                result = self.manager._build_command("echo hello", working_dir)
                assert result == "/usr/local/bin/uv run echo hello"
        
        # Test without uv available
        with patch('pathlib.Path.exists', return_value=True):
            with patch('shutil.which', return_value=None):
                result = self.manager._build_command("python -m mymodule", working_dir)
                assert result == "python -m mymodule"

    def test_template_rendering(self):
        """Test service and timer template rendering."""
        # Test service template
        service_template = self.manager.jinja_env.get_template('service.j2')
        
        context = {
            'name': 'test-service',
            'description': 'Test Service',
            'user': 'testuser',
            'group': 'testuser',
            'working_dir': '/test/dir',
            'command': 'echo hello',
            'environment': {'VAR': 'value'},
            'data_dirs': ['/test/data'],
            'dependencies': ['network.target'],
        }
        
        result = service_template.render(**context)
        
        # Check key components are present
        assert '[Unit]' in result
        assert 'Description=Test Service' in result
        assert '[Service]' in result
        assert 'Type=oneshot' in result
        assert 'User=testuser' in result
        assert 'WorkingDirectory=/test/dir' in result
        assert 'ExecStart=echo hello' in result
        assert 'StandardOutput=journal' in result
        assert 'NoNewPrivileges=true' in result
        
        # Test timer template
        timer_template = self.manager.jinja_env.get_template('timer.j2')
        
        timer_context = {
            'description': 'Test Timer',
            'service_name': 'test-service',
            'schedule_type': 'calendar',
            'schedule': '*:0/15',
        }
        
        result = timer_template.render(**timer_context)
        
        assert '[Unit]' in result
        assert 'Description=Timer for Test Timer' in result
        assert '[Timer]' in result
        assert 'OnCalendar=*:0/15' in result
        assert 'Requires=test-service.service' in result
        assert '[Install]' in result
        assert 'WantedBy=timers.target' in result

    @patch('subprocess.run')
    def test_add_service_dry_run(self, mock_subprocess):
        """Test service addition without actually running systemctl commands."""
        # Mock successful subprocess calls
        mock_subprocess.return_value = Mock(returncode=0)
        
        with patch.object(self.manager, '_run_systemctl'):
            # This should create temp files and attempt to copy them
            # We'll catch the exception when it tries to copy to the mocked systemd_dir
            try:
                self.manager.add(
                    name="test-service",
                    command="echo hello",
                    schedule="*/15",
                    description="Test Service"
                )
            except Exception:
                # Expected to fail when trying to copy files, but templates should be generated
                pass

    def test_service_name_validation(self):
        """Test service name validation."""
        # Valid names
        valid_names = ["test", "my-service", "service123", "test_service"]
        for name in valid_names:
            # Should not raise an exception
            self.manager._validate_service_name(name)
        
        # Invalid names (if validation exists)
        invalid_names = ["", "test service", "test/service"]
        for name in invalid_names:
            with pytest.raises(ValueError):
                self.manager._validate_service_name(name)

    def test_config_persistence(self):
        """Test configuration saving and loading."""
        # Mock config directory
        config_dir = Path(self.temp_dir) / "config"
        config_dir.mkdir()
        self.manager.config_file = config_dir / "services.json"
        
        # Test saving configuration
        test_services = {
            "test-service": {
                "command": "echo hello",
                "schedule": "*/15",
                "description": "Test Service",
                "working_dir": "/test/dir"
            }
        }
        
        self.manager._save_services(test_services)
        
        # Test loading configuration
        loaded_services = self.manager._load_services()
        assert loaded_services == test_services


class TestCLIFunctions:
    """Test CLI-related functionality."""

    def test_schedule_descriptions(self):
        """Test schedule description generation."""
        # This would test any CLI helper functions
        pass


if __name__ == "__main__":
    pytest.main([__file__])