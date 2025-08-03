# Systemd Management Tool (sysd) - Implementation Plan

## Problem Statement
The original systemd setup script (`scripts/setup_systemd.sh`) was difficult to manage, had hardcoded values, and lacked proper abstractions for managing multiple services. User requirements:
- No always-running apps (timers are perfect)
- Easy management of several apps at once
- Centralized/managed logs
- Clean abstractions for scheduling

## Solution: sysd Tool

### What's Been Implemented ✅

1. **Core SystemdManager Class** (`sysd/manager.py`)
   - Template-based service/timer generation using Jinja2
   - Automatic uv project detection and command wrapping
   - Service lifecycle management (add, remove, update)
   - Configuration persistence in `~/.config/sysd/services.json`

2. **Service Templates** (`sysd/templates/`)
   - `service.j2` - Systemd service file template with security hardening
   - `timer.j2` - Systemd timer file template with flexible scheduling

3. **CLI Interface** (`sysd/__main__.py`)
   - Fire-based CLI with comprehensive help
   - Commands: add, remove, update, list, status, logs
   - Schedule abstractions (*/15, hourly, daily, @startup, etc.)

4. **Integration**
   - Added to pyproject.toml dependencies (jinja2)
   - Shell wrapper script (`bin/sysd`) for easy execution
   - Updated justfile with new commands and HN watcher setup

### Usage Examples

```bash
# Add HN watcher service
./bin/sysd add hn-watcher "python -m hn_watcher 43858554" --schedule="*/15" --description="HN Comment Watcher"

# List all services
./bin/sysd list

# View logs
./bin/sysd logs hn-watcher --follow

# Remove service
./bin/sysd remove hn-watcher

# Using justfile shortcuts
just setup-hn-watcher 43858554
just list
just service-logs hn-watcher
```

### Generated Files Structure

Services are created with naming pattern: `sysd-{name}.service` and `sysd-{name}.timer`

Example generated service file:
```ini
[Unit]
Description=HN Comment Watcher for post 43858554
After=network.target

[Service]
Type=oneshot
User=evan
Group=evan
WorkingDirectory=/home/evan/dev/hn-watcher
ExecStart=/home/evan/.local/bin/uv run python -m hn_watcher 43858554

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sysd-hn-watcher

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/evan/dev/hn-watcher
```

### Schedule Format Support
- `*/15` - Every 15 minutes (converts to `OnCalendar=*:0/15`)
- `hourly`, `daily`, `weekly`, `monthly` - Standard intervals
- `@startup` - On system startup
- `@boot` - On system boot  
- Direct systemd calendar syntax

## Current Status

### ✅ Completed
- All core functionality implemented
- Templates working correctly
- CLI interface complete
- uv integration working
- Schedule parsing complete
- Justfile integration added

### ⚠️ Known Issues
- Requires sudo access for systemd file operations (expected behavior)
- Virtual environment warning from uv (harmless)

### 🔄 Testing Status
Template generation tested and working correctly. The tool generates proper systemd service and timer files with:
- Correct uv command wrapping: `/home/evan/.local/bin/uv run python -m hn_watcher 43858554`
- Proper scheduling: `OnCalendar=*:0/15` for `*/15` schedule
- Security hardening enabled
- Centralized logging to journald

## Next Steps for Continuation

### For Testing/Deployment
1. **Test with sudo access**: Run `./bin/sysd add hn-watcher "python -m hn_watcher 43858554" --schedule="*/15"`
2. **Verify service creation**: Check `/etc/systemd/system/sysd-hn-watcher.*` files
3. **Test logs**: `./bin/sysd logs hn-watcher`
4. **Test removal**: `./bin/sysd remove hn-watcher`

### Potential Enhancements (Future)
1. **Non-sudo mode**: Option to generate files without installing them
2. **User systemd services**: Support for `~/.config/systemd/user/` services
3. **Service dependencies**: Better handling of service dependencies
4. **Validation**: Pre-flight checks for commands and schedules
5. **Import/Export**: Backup/restore service configurations
6. **Monitoring**: Health checks and alerting integration

### File Structure
```
sysd/
├── __init__.py
├── __main__.py          # CLI interface with Fire
├── manager.py           # Core SystemdManager class
└── templates/
    ├── service.j2       # Service file template
    └── timer.j2         # Timer file template

bin/
└── sysd                 # Shell wrapper script

justfile                 # Updated with sysd commands
pyproject.toml           # Added jinja2 dependency
```

## Key Design Decisions

1. **Template-based**: Uses Jinja2 for flexible service generation
2. **Security-first**: Services run with security hardening enabled
3. **uv-aware**: Automatically detects and wraps uv projects
4. **Non-destructive**: Maintains separate service prefix (`sysd-`) to avoid conflicts
5. **Stateful**: Tracks managed services in JSON config for easy management
6. **Centralized logging**: All services log to journald with consistent identifiers

The tool successfully replaces the original systemd setup script with a much more flexible and maintainable solution that meets all the original requirements.