#!/usr/bin/env python3
"""
Systemd Service Manager - Clean abstractions for managing systemd services and timers.
"""

import getpass
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader


class SystemdManager:
    """Manages systemd services and timers with clean abstractions."""

    def __init__(self, service_prefix: str = "sysd"):
        self.service_prefix = service_prefix
        self.systemd_dir = Path("/etc/systemd/system")
        self.templates_dir = Path(__file__).parent / "templates"
        self.config_dir = Path.home() / ".config" / "sysd"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.services_file = self.config_dir / "services.json"

        # Setup Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def _get_service_name(self, name: str) -> str:
        """Get the full systemd service name."""
        return f"{self.service_prefix}-{name}"

    def _get_timer_name(self, name: str) -> str:
        """Get the full systemd timer name."""
        return f"{self.service_prefix}-{name}"

    def _load_services(self) -> Dict[str, Dict[str, Any]]:
        """Load services configuration from file."""
        if not self.services_file.exists():
            return {}
        try:
            with open(self.services_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_services(self, services: Dict[str, Dict[str, Any]]) -> None:
        """Save services configuration to file."""
        with open(self.services_file, "w") as f:
            json.dump(services, f, indent=2)

    def _parse_schedule(self, schedule: str) -> Tuple[str, str]:
        """Parse schedule string into systemd timer format."""
        schedule = schedule.lower().strip()

        # Handle common shortcuts
        shortcuts = {
            "hourly": ("calendar", "hourly"),
            "daily": ("calendar", "daily"),
            "weekly": ("calendar", "weekly"),
            "monthly": ("calendar", "monthly"),
        }

        if schedule in shortcuts:
            return shortcuts[schedule]

        # Handle startup/boot
        if schedule.startswith("@startup"):
            delay = schedule.split("=")[1] if "=" in schedule else "1min"
            return ("startup", delay)

        if schedule.startswith("@boot"):
            delay = schedule.split("=")[1] if "=" in schedule else "1min"
            return ("boot", delay)

        # Handle cron-like syntax (convert to OnCalendar)
        if schedule.startswith("*/"):
            minutes = schedule[2:]
            return ("calendar", f"*:0/{minutes}")

        # Assume it's a direct OnCalendar specification
        return ("calendar", schedule)

    def _detect_uv_project(self, working_dir: Path) -> bool:
        """Detect if this is a uv project."""
        return (working_dir / "pyproject.toml").exists() and shutil.which(
            "uv"
        ) is not None

    def _build_command(self, command: str, working_dir) -> str:
        """Build the full command with uv if needed."""
        working_path = Path(working_dir)
        if self._detect_uv_project(working_path):
            if not command.startswith("uv "):
                # Wrap in uv run if not already
                if command.startswith("python "):
                    command = command.replace("python ", "uv run python ", 1)
                elif " -m " in command:
                    command = f"uv run {command}"
                else:
                    command = f"uv run {command}"

        # Ensure absolute path for uv
        if command.startswith("uv "):
            uv_path = shutil.which("uv")
            if uv_path:
                command = command.replace("uv ", f"{uv_path} ", 1)

        return command

    def _run_systemctl(
        self, command: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run systemctl command with sudo."""
        cmd = ["sudo", "systemctl"] + command
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def add(
        self,
        name: str,
        command: str,
        schedule: str = "*/15",
        description: str = "",
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        data_dirs: Optional[List[str]] = None,
    ) -> None:
        """
        Add a new systemd service and timer.

        Args:
            name: Service name (will be prefixed)
            command: Command to run
            schedule: Schedule specification (*/15, hourly, daily, @startup, etc.)
            description: Service description
            working_dir: Working directory (defaults to current)
            environment: Environment variables
            data_dirs: Additional writable directories
        """
        if not description:
            description = f"Managed service: {name}"

        working_dir = Path(working_dir or os.getcwd()).absolute()
        full_command = self._build_command(command, working_dir)
        schedule_type, schedule_value = self._parse_schedule(schedule)

        service_name = self._get_service_name(name)
        timer_name = self._get_timer_name(name)

        # Prepare template context
        context = {
            "name": service_name,
            "description": description,
            "user": getpass.getuser(),
            "group": getpass.getuser(),
            "working_dir": str(working_dir),
            "command": full_command,
            "environment": environment or {},
            "data_dirs": data_dirs or [],
            "dependencies": [],
        }

        timer_context = {
            "description": description,
            "service_name": service_name,
            "schedule_type": schedule_type,
            "schedule": schedule_value,
        }

        # Render templates
        service_template = self.jinja_env.get_template("service.j2")
        timer_template = self.jinja_env.get_template("timer.j2")

        service_content = service_template.render(**context)
        timer_content = timer_template.render(**timer_context)

        # Write service files
        service_file = self.systemd_dir / f"{service_name}.service"
        timer_file = self.systemd_dir / f"{timer_name}.timer"

        try:
            # Write files with sudo using a temporary file approach

            # Write service file
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".service"
            ) as f:
                f.write(service_content)
                temp_service = f.name

            # Write timer file
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".timer"
            ) as f:
                f.write(timer_content)
                temp_timer = f.name

            try:
                # Copy files to systemd directory
                subprocess.run(
                    ["sudo", "cp", temp_service, str(service_file)], check=True
                )
                subprocess.run(["sudo", "cp", temp_timer, str(timer_file)], check=True)
            finally:
                # Clean up temp files
                os.unlink(temp_service)
                os.unlink(temp_timer)

            # Reload systemd and enable timer
            self._run_systemctl(["daemon-reload"])
            self._run_systemctl(["enable", "--now", f"{timer_name}.timer"])

            # Save service configuration
            services = self._load_services()
            services[name] = {
                "command": command,
                "schedule": schedule,
                "description": description,
                "working_dir": str(working_dir),
                "environment": environment or {},
                "data_dirs": data_dirs or [],
                "service_name": service_name,
                "timer_name": f"{timer_name}.timer",
            }
            self._save_services(services)

            print(f"✓ Added service '{name}' with schedule '{schedule}'")

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to add service: {e}")
            raise

    def remove(self, name: str) -> None:
        """Remove a systemd service and timer."""
        services = self._load_services()
        if name not in services:
            print(f"✗ Service '{name}' not found")
            return

        service_name = self._get_service_name(name)
        timer_name = self._get_timer_name(name)

        try:
            # Stop and disable
            self._run_systemctl(["stop", f"{timer_name}.timer"], check=False)
            self._run_systemctl(["disable", f"{timer_name}.timer"], check=False)
            self._run_systemctl(["stop", f"{service_name}.service"], check=False)

            # Remove files
            service_file = self.systemd_dir / f"{service_name}.service"
            timer_file = self.systemd_dir / f"{timer_name}.timer"

            subprocess.run(["sudo", "rm", "-f", str(service_file)], check=True)
            subprocess.run(["sudo", "rm", "-f", str(timer_file)], check=True)

            # Reload systemd
            self._run_systemctl(["daemon-reload"])

            # Remove from config
            del services[name]
            self._save_services(services)

            print(f"✓ Removed service '{name}'")

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to remove service: {e}")
            raise

    def update(
        self,
        name: str,
        command: Optional[str] = None,
        schedule: Optional[str] = None,
        description: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> None:
        """Update an existing service."""
        services = self._load_services()
        if name not in services:
            print(f"✗ Service '{name}' not found")
            return

        service = services[name]

        # Update values
        if command is not None:
            service["command"] = command
        if schedule is not None:
            service["schedule"] = schedule
        if description is not None:
            service["description"] = description
        if environment is not None:
            service["environment"] = environment

        # Remove and re-add
        self.remove(name)
        self.add(
            name=name,
            command=service["command"],
            schedule=service["schedule"],
            description=service["description"],
            working_dir=service["working_dir"],
            environment=service["environment"],
            data_dirs=service["data_dirs"],
        )

        print(f"✓ Updated service '{name}'")

    def list_services(self) -> None:
        """List all managed services with their status."""
        services = self._load_services()
        if not services:
            print("No managed services found")
            return

        print("Managed Services:")
        print("-" * 80)

        for name, config in services.items():
            service_name = config["service_name"]
            timer_name = config["timer_name"]

            # Get status
            try:
                timer_result = self._run_systemctl(
                    ["is-active", timer_name], check=False
                )
                timer_status = timer_result.stdout.strip()

                service_result = self._run_systemctl(
                    ["is-failed", f"{service_name}.service"], check=False
                )
                service_failed = service_result.returncode == 0

                status_icon = (
                    "✗"
                    if service_failed
                    else ("✓" if timer_status == "active" else "○")
                )

            except Exception:
                status_icon = "?"
                timer_status = "unknown"

            print(
                f"{status_icon} {name:20} {config['schedule']:15} {timer_status:10} {config['description']}"
            )

    def status(self, name: Optional[str] = None) -> None:
        """Show detailed status for a service or all services."""
        services = self._load_services()

        if name:
            if name not in services:
                print(f"✗ Service '{name}' not found")
                return
            services = {name: services[name]}

        for svc_name, config in services.items():
            timer_name = config["timer_name"]

            print(f"\n=== {svc_name} ===")
            print(f"Command: {config['command']}")
            print(f"Schedule: {config['schedule']}")
            print(f"Working Dir: {config['working_dir']}")

            # Show systemctl status
            try:
                result = self._run_systemctl(["status", timer_name], check=False)
                print(f"\nTimer Status:\n{result.stdout}")

                result = self._run_systemctl(["list-timers", timer_name], check=False)
                print(f"Timer Info:\n{result.stdout}")

            except Exception as e:
                print(f"Could not get status: {e}")

    def logs(
        self,
        name: Optional[str] = None,
        follow: bool = False,
        lines: int = 50,
        all_services: bool = False,
    ) -> None:
        """Show logs for services."""
        services = self._load_services()

        if all_services:
            # Show logs for all services
            identifiers = [
                f"--identifier={svc['service_name']}" for svc in services.values()
            ]
            if not identifiers:
                print("No services to show logs for")
                return
        elif name:
            if name not in services:
                print(f"✗ Service '{name}' not found")
                return
            identifiers = [f"--identifier={services[name]['service_name']}"]
        else:
            print("Must specify service name or use --all")
            return

        cmd = ["journalctl"] + identifiers + [f"--lines={lines}"]
        if follow:
            cmd.append("--follow")

        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            pass
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to show logs: {e}")

    def _validate_service_name(self, name: str) -> None:
        """Validate service name."""
        if not name:
            raise ValueError("Service name cannot be empty")

        if " " in name:
            raise ValueError("Service name cannot contain spaces")

        if "/" in name:
            raise ValueError("Service name cannot contain forward slashes")

        # Check for other invalid characters
        invalid_chars = ["\\", ":", "*", "?", "<", ">", "|"]
        for char in invalid_chars:
            if char in name:
                raise ValueError(f"Service name cannot contain '{char}'")
