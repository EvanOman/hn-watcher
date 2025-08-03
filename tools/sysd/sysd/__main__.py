#!/usr/bin/env python3
"""
Systemd Service Manager CLI
Usage: python -m sysd <command> [args...]
"""

import fire
from .manager import SystemdManager


def main():
    """Main CLI interface for systemd service management."""
    manager = SystemdManager()
    
    # Create a custom Fire class with better help
    class SysdCLI:
        """Systemd Service Manager - Clean abstractions for managing systemd services and timers."""
        
        def add(self, name: str, command: str, schedule: str = "*/15", 
                description: str = "", working_dir: str = "",
                env: str = "", data_dirs: str = ""):
            """
            Add a new systemd service and timer.
            
            Args:
                name: Service name (will be prefixed with 'sysd-')
                command: Command to run (e.g., 'python -m hn_watcher 12345')
                schedule: Schedule (*/15, hourly, daily, @startup, etc.)
                description: Service description
                working_dir: Working directory (defaults to current)
                env: Environment variables as JSON string or KEY=VALUE,KEY2=VALUE2
                data_dirs: Comma-separated list of additional writable directories
            
            Examples:
                sysd add hn-watcher "python -m hn_watcher 43858554" --schedule="*/15"
                sysd add backup "backup.sh" --schedule="daily" --description="Daily backup"
                sysd add startup-task "init.py" --schedule="@startup"
            """
            environment = None
            if env:
                try:
                    import json
                    environment = json.loads(env)
                except json.JSONDecodeError:
                    # Parse KEY=VALUE,KEY2=VALUE2 format
                    environment = {}
                    for pair in env.split(','):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            environment[key.strip()] = value.strip()
            
            data_dir_list = [d.strip() for d in data_dirs.split(',') if d.strip()] if data_dirs else None
            working_directory = working_dir if working_dir else None
            
            # Validate service name
            manager._validate_service_name(name)
            
            manager.add(
                name=name,
                command=command,
                schedule=schedule,
                description=description,
                working_dir=working_directory,
                environment=environment,
                data_dirs=data_dir_list
            )
        
        def remove(self, name: str):
            """
            Remove a systemd service and timer.
            
            Args:
                name: Service name to remove
            
            Examples:
                sysd remove hn-watcher
            """
            manager.remove(name)
        
        def rm(self, name: str):
            """Alias for remove."""
            self.remove(name)
        
        def update(self, name: str, command: str = "", schedule: str = "", 
                  description: str = "", env: str = ""):
            """
            Update an existing service.
            
            Args:
                name: Service name to update
                command: New command (optional)
                schedule: New schedule (optional)
                description: New description (optional)
                env: New environment variables (optional)
            
            Examples:
                sysd update hn-watcher --command="python -m hn_watcher 99999"
                sysd update hn-watcher --schedule="hourly"
            """
            kwargs = {}
            if command:
                kwargs['command'] = command
            if schedule:
                kwargs['schedule'] = schedule
            if description:
                kwargs['description'] = description
            if env:
                try:
                    import json
                    kwargs['environment'] = json.loads(env)
                except json.JSONDecodeError:
                    environment = {}
                    for pair in env.split(','):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            environment[key.strip()] = value.strip()
                    kwargs['environment'] = environment
            
            manager.update(name, **kwargs)
        
        def list(self):
            """
            List all managed services with their status.
            
            Examples:
                sysd list
            """
            manager.list_services()
        
        def ls(self):
            """Alias for list."""
            self.list()
        
        def status(self, name: str = ""):
            """
            Show detailed status for a service or all services.
            
            Args:
                name: Service name (optional, shows all if not specified)
            
            Examples:
                sysd status
                sysd status hn-watcher
            """
            manager.status(name if name else None)
        
        def logs(self, name: str = "", follow: bool = False, 
                lines: int = 50, all: bool = False):
            """
            Show logs for services.
            
            Args:
                name: Service name (required unless --all is used)
                follow: Follow logs in real-time (like tail -f)
                lines: Number of lines to show (default: 50)
                all: Show logs for all services
            
            Examples:
                sysd logs hn-watcher
                sysd logs hn-watcher --follow
                sysd logs --all
                sysd logs hn-watcher --lines=100
            """
            manager.logs(
                name=name if name else None, 
                follow=follow, 
                lines=lines, 
                all_services=all
            )
        
        def help(self):
            """Show detailed help information."""
            help_text = """
Systemd Service Manager (sysd) - Clean abstractions for managing systemd services and timers

USAGE:
    python -m sysd <command> [args...]

COMMANDS:
    add <name> <command>           Add a new service with timer
    remove|rm <name>               Remove a service and timer  
    update <name> [options]        Update an existing service
    list|ls                        List all managed services
    status [name]                  Show service status
    logs <name> [options]          Show service logs
    help                          Show this help

SCHEDULE FORMATS:
    */15                          Every 15 minutes
    */30                          Every 30 minutes
    hourly                        Every hour
    daily                         Every day
    weekly                        Every week
    monthly                       Every month
    @startup                      On system startup
    @boot                         On system boot
    "Mon *-*-* 09:00:00"         Custom systemd calendar format

EXAMPLES:
    # Add HN watcher that runs every 15 minutes
    python -m sysd add hn-watcher "python -m hn_watcher 43858554" --schedule="*/15"
    
    # Add a daily backup script
    python -m sysd add backup "./backup.sh" --schedule="daily" --description="Daily backup"
    
    # Add startup initialization
    python -m sysd add init "python init.py" --schedule="@startup"
    
    # List all services
    python -m sysd list
    
    # Show logs for a service
    python -m sysd logs hn-watcher
    
    # Follow logs in real-time
    python -m sysd logs hn-watcher --follow
    
    # Update a service command
    python -m sysd update hn-watcher --command="python -m hn_watcher 99999"
    
    # Remove a service
    python -m sysd remove hn-watcher

For more details on systemd timer calendar format:
    man systemd.time
            """
            print(help_text)
    
    # Initialize Fire with the CLI class
    fire.Fire(SysdCLI)


if __name__ == "__main__":
    main()