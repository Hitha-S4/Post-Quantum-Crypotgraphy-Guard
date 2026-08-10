# Development Container

This directory contains the VS Code Dev Container configuration for the NGFW PQC Detector project.

## What is a Dev Container?

A development container (or dev container for short) allows you to use a container as a full-featured development environment. It can be used to run an application, to separate tools, libraries, or runtimes needed for working with a codebase, and to aid in continuous integration and testing.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) or [Rancher Desktop](https://rancherdesktop.io/)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Getting Started

1. **Install Prerequisites**: Make sure Docker and VS Code with the Dev Containers extension are installed.

2. **Open in Container**:
   - Open this project in VS Code
   - Press `F1` or `Cmd/Ctrl+Shift+P`
   - Select "Dev Containers: Reopen in Container"
   - Wait for the container to build and start (first time may take a few minutes)

3. **Start Developing**: Once the container is ready, you'll have:
   - Python 3.11 environment
   - All project dependencies installed via UV
   - PostgreSQL database running
   - Kafka message broker running
   - All VS Code extensions configured

## Features

### Included Services

The dev container automatically starts:
- **Backend API** on port 8000
- **PostgreSQL** on port 5432
- **Kafka** on port 9092
- **Metrics** on port 9090

### VS Code Extensions

Pre-installed extensions:
- Python language support
- Pylance (type checking)
- Black formatter
- isort (import sorting)
- Ruff (fast linter)
- TOML support
- YAML support
- Docker support
- GitHub Copilot (if you have access)

### Editor Settings

Configured for:
- Auto-formatting on save with Black
- Auto-organize imports with isort
- Line length: 100 characters
- Type checking with Pylance
- Linting with Pylint

## Working in the Container

### Running the Application

```bash
# The application starts automatically, but you can restart it:
uv run python -m ngfw_pqc_detector.main
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ngfw_pqc_detector --cov-report=html

# Run specific test file
uv run pytest tests/test_pqc_detector.py
```

### Code Formatting

```bash
# Format code with Black
uv run black src/

# Sort imports
uv run isort src/

# Lint code
uv run pylint src/ngfw_pqc_detector/
```

### Database Access

```bash
# Connect to PostgreSQL
psql postgresql://ngfw_user:ngfw_password@postgres:5432/ngfw_pqc

# Or using the DATABASE_URL from .env
psql $DATABASE_URL
```

### Kafka Operations

```bash
# List topics
docker exec ngfw-kafka kafka-topics --list --bootstrap-server localhost:9092

# Consume messages
docker exec ngfw-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tls-logs \
  --from-beginning
```

## Customization

### Adding VS Code Extensions

Edit `.devcontainer/devcontainer.json` and add extension IDs to the `extensions` array:

```json
"extensions": [
  "ms-python.python",
  "your-extension-id"
]
```

### Changing Settings

Modify the `settings` section in `.devcontainer/devcontainer.json`:

```json
"settings": {
  "python.linting.enabled": true,
  "your.setting": "value"
}
```

### Adding System Packages

If you need additional system packages, modify the `Dockerfile` to include them:

```dockerfile
RUN apt-get update && apt-get install -y \
    your-package \
    && rm -rf /var/lib/apt/lists/*
```

## Troubleshooting

### Container won't start

1. Check Docker is running: `docker ps`
2. Check Docker has enough resources (4GB RAM minimum recommended)
3. Try rebuilding: `Dev Containers: Rebuild Container`

### Port conflicts

If ports 8000, 5432, or 9092 are already in use:
1. Stop conflicting services
2. Or modify port mappings in `docker-compose.yml`

### Dependencies not installing

1. Rebuild container: `Dev Containers: Rebuild Container`
2. Check `uv.lock` is present
3. Try: `uv sync --reinstall`

### Database connection issues

1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Verify DATABASE_URL in `.env`
3. Check logs: `docker-compose logs postgres`

## Tips

- Use the integrated terminal (`` Ctrl+` ``) for all commands
- The workspace folder is mounted at `/app` in the container
- Changes to files are immediately reflected (no rebuild needed)
- Use `docker-compose logs -f backend` to see application logs
- Press `F5` to start debugging with breakpoints

## Exiting the Container

To exit the dev container:
1. Close VS Code, or
2. `Dev Containers: Reopen Folder Locally`

The containers will continue running. To stop them:
```bash
docker-compose down
