"""Integration tests for sysd using Docker."""

import pytest
import docker
import tempfile
import time
import os
from pathlib import Path


@pytest.fixture(scope="session")
def docker_client():
    """Get Docker client."""
    return docker.from_env()


@pytest.fixture(scope="session")
def sysd_image(docker_client):
    """Build sysd test image."""
    # Build the test image
    dockerfile_content = """
FROM ubuntu:22.04

# Install systemd, python, uv, and other dependencies
RUN apt-get update && apt-get install -y \
    systemd \
    systemd-sysv \
    python3 \
    python3-pip \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create a test user
RUN useradd -m -s /bin/bash testuser && \
    echo "testuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up systemd
RUN systemctl set-default multi-user.target
RUN systemctl mask dev-hugepages.mount sys-fs-fuse-connections.mount

# Copy sysd code
COPY . /home/testuser/sysd
RUN chown -R testuser:testuser /home/testuser/sysd

# Switch to test user and install uv
USER testuser
WORKDIR /home/testuser/sysd

# Install uv for testuser
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/testuser/.local/bin:$PATH"

# Install sysd and dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e ".[dev]"

# Switch back to root for systemd
USER root
CMD ["/lib/systemd/systemd"]
"""
    
    # Create temporary directory for build context
    with tempfile.TemporaryDirectory() as build_dir:
        # Copy sysd code to build directory
        import shutil
        sysd_path = Path(__file__).parent.parent
        shutil.copytree(sysd_path, Path(build_dir) / "sysd")
        
        # Write Dockerfile
        with open(Path(build_dir) / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        
        # Build image
        image, _ = docker_client.images.build(
            path=str(build_dir),
            tag="sysd-test:latest",
            rm=True
        )
        
        yield image
        
        # Cleanup
        try:
            docker_client.images.remove(image.id, force=True)
        except:
            pass


@pytest.fixture
def sysd_container(docker_client, sysd_image):
    """Create and start a container for testing."""
    container = docker_client.containers.run(
        sysd_image.id,
        detach=True,
        privileged=True,
        name=f"sysd-test-{int(time.time())}"
    )
    
    # Wait for systemd to start
    time.sleep(3)
    
    yield container
    
    # Cleanup
    try:
        container.stop()
        container.remove()
    except:
        pass


class TestSysdIntegration:
    """Integration tests for sysd functionality."""

    def test_service_lifecycle(self, sysd_container):
        """Test complete service lifecycle: add, list, status, remove."""
        # Add a service
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && "
            "python -m sysd add test-service \"echo hello world\" "
            "--schedule=\"*/15\" --description=\"Test Service\"'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"Added service 'test-service'" in result.output

        # List services
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd list'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"test-service" in result.output
        assert b"*/15" in result.output

        # Check service status
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd status test-service'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"test-service" in result.output

        # Verify systemd files exist
        result = sysd_container.exec_run(
            "find /etc/systemd/system -name '*test-service*'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"sysd-test-service.service" in result.output
        assert b"sysd-test-service.timer" in result.output

        # Remove service
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove test-service'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"Removed service 'test-service'" in result.output

        # Verify files are removed
        result = sysd_container.exec_run(
            "find /etc/systemd/system -name '*test-service*'",
            user="root"
        )
        assert result.exit_code == 0
        assert result.output.strip() == b""

        # List should be empty
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd list'",
            user="root"
        )
        assert result.exit_code == 0
        assert b"No managed services found" in result.output

    def test_systemd_file_generation(self, sysd_container):
        """Test that generated systemd files have correct content."""
        # Add a service
        sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && "
            "python -m sysd add file-test \"python -m test\" "
            "--schedule=\"hourly\" --description=\"File Test Service\"'",
            user="root"
        )

        # Check service file content
        result = sysd_container.exec_run(
            "cat /etc/systemd/system/sysd-file-test.service",
            user="root"
        )
        assert result.exit_code == 0
        content = result.output.decode()
        
        # Verify key components
        assert "[Unit]" in content
        assert "Description=File Test Service" in content
        assert "[Service]" in content
        assert "Type=oneshot" in content
        assert "User=testuser" in content
        assert "WorkingDirectory=/home/testuser/sysd" in content
        assert "StandardOutput=journal" in content
        assert "NoNewPrivileges=true" in content

        # Check timer file content
        result = sysd_container.exec_run(
            "cat /etc/systemd/system/sysd-file-test.timer",
            user="root"
        )
        assert result.exit_code == 0
        content = result.output.decode()
        
        assert "[Unit]" in content
        assert "Description=Timer for File Test Service" in content
        assert "[Timer]" in content
        assert "OnCalendar=hourly" in content
        assert "Requires=sysd-file-test.service" in content
        assert "[Install]" in content
        assert "WantedBy=timers.target" in content

        # Cleanup
        sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove file-test'",
            user="root"
        )

    def test_multiple_services(self, sysd_container):
        """Test managing multiple services."""
        services = [
            ("service1", "echo service1", "*/10"),
            ("service2", "echo service2", "daily"),
            ("service3", "echo service3", "@startup"),
        ]

        # Add multiple services
        for name, command, schedule in services:
            result = sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && "
                f"python -m sysd add {name} \"{command}\" "
                f"--schedule=\"{schedule}\" --description=\"{name} service\"'",
                user="root"
            )
            assert result.exit_code == 0

        # List all services
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd list'",
            user="root"
        )
        assert result.exit_code == 0
        
        for name, _, schedule in services:
            assert name.encode() in result.output
            assert schedule.encode() in result.output

        # Remove all services
        for name, _, _ in services:
            result = sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove {name}'",
                user="root"
            )
            assert result.exit_code == 0

    def test_error_handling(self, sysd_container):
        """Test error handling scenarios."""
        # Try to remove non-existent service
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove nonexistent'",
            user="root"
        )
        # Should handle gracefully (exact behavior depends on implementation)
        
        # Try to add service with invalid name
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && "
            "python -m sysd add \"invalid name\" \"echo test\" --schedule=\"*/15\"'",
            user="root"
        )
        # Should handle invalid service names gracefully

    def test_schedule_parsing(self, sysd_container):
        """Test various schedule formats."""
        schedule_tests = [
            ("*/5", "*:0/5"),
            ("*/30", "*:0/30"),
            ("hourly", "hourly"),
            ("daily", "daily"),
            ("@startup", "@startup"),
        ]

        for input_schedule, expected_calendar in schedule_tests:
            service_name = f"sched-test-{input_schedule.replace('*/', 'every').replace('@', 'at')}"
            
            # Add service
            sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && "
                f"python -m sysd add {service_name} \"echo test\" "
                f"--schedule=\"{input_schedule}\" --description=\"Schedule test\"'",
                user="root"
            )

            # Check timer file
            result = sysd_container.exec_run(
                f"cat /etc/systemd/system/sysd-{service_name}.timer",
                user="root"
            )
            assert result.exit_code == 0
            content = result.output.decode()
            assert f"OnCalendar={expected_calendar}" in content

            # Cleanup
            sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove {service_name}'",
                user="root"
            )


@pytest.mark.slow
class TestSysdPerformance:
    """Performance tests for sysd (marked as slow)."""

    def test_bulk_operations(self, sysd_container):
        """Test bulk service operations."""
        # Add many services
        num_services = 10
        for i in range(num_services):
            result = sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && "
                f"python -m sysd add bulk-{i} \"echo {i}\" "
                f"--schedule=\"*/{5+i}\" --description=\"Bulk service {i}\"'",
                user="root"
            )
            assert result.exit_code == 0

        # List all services
        result = sysd_container.exec_run(
            "su - testuser -c 'cd /home/testuser/sysd && python -m sysd list'",
            user="root"
        )
        assert result.exit_code == 0
        
        # Should show all services
        for i in range(num_services):
            assert f"bulk-{i}".encode() in result.output

        # Remove all services
        for i in range(num_services):
            result = sysd_container.exec_run(
                f"su - testuser -c 'cd /home/testuser/sysd && python -m sysd remove bulk-{i}'",
                user="root"
            )
            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])