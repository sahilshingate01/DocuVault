
# Nexus CLI – DocuVault

Nexus CLI is the terminal interface for the DocuVault Secure Document Management System. It communicates with the FastAPI backend to manage documents and their versions.

## Features

- Authenticate using DocuVault credentials
- Upload documents with metadata and classification
- Search accessible documents
- Upload new document versions
- View document version history
- Download document versions
- Verify document integrity using SHA-256

## Setup

From the project root:

```bash
source .venv/bin/activate
pip install requests
```

## Start the backend

```bash
uvicorn app.main:app --reload
```

## Usage

Run commands from the project root:

```bash
python -m nexus_cli.commands --help
```

### Search documents

```bash
python -m nexus_cli.commands list
```

### Upload a document

```bash
python -m nexus_cli.commands upload document.pdf \
  --title "Project Report" \
  --number "DOC-001" \
  --workspace YOUR_WORKSPACE_ID
```

### Upload a new version

```bash
python -m nexus_cli.commands upload-version DOCUMENT_ID updated.pdf \
  --summary "Updated document"
```

### View version history

```bash
python -m nexus_cli.commands versions DOCUMENT_ID
```

### Download a version

```bash
python -m nexus_cli.commands download DOCUMENT_ID \
  --version 1 --output downloaded.pdf
```

### Verify integrity

```bash
python -m nexus_cli.commands verify DOCUMENT_ID --version 1
```

## Authentication

The CLI prompts for the user's email and password. Password input is hidden, and the authentication token is used for subsequent API requests.

## Project Structure

- `client.py` – HTTP client and authentication
- `commands.py` – CLI commands and argument handling
- `__init__.py` – Python package initialization
