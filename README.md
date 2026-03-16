# Gmail MCP Server

A **Model Context Protocol (MCP)** server that provides Gmail integration tools for sending and searching emails, built with [FastMCP](https://github.com/jlowin/fastmcp) and served over HTTP. This server enables AI agents (such as Claude) to send emails and search through a Gmail inbox in real time.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Google OAuth2 Authentication](#google-oauth2-authentication)
- [Running the Server](#running-the-server)
- [MCP Tools Reference](#mcp-tools-reference)
  - [sendEmail](#sendemail)
  - [searchMessages](#searchmessages)
- [Diagnostic Utility](#diagnostic-utility)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)

---

## Overview

This server exposes **2 Gmail tools** over an HTTP MCP endpoint. It is designed to be consumed by AI agent frameworks (e.g., Claude Agent SDK, LangChain, or any MCP-compatible client). It uses the Gmail API v1 and authenticates with OAuth2 credentials, supporting both **JSON** and **Pickle** token formats.

- **Protocol:** Model Context Protocol (MCP) over HTTP
- **Transport:** HTTP (Streamable HTTP via FastMCP)
- **Default Port:** `10000`
- **Google API:** Gmail API v1
- **OAuth2 Scope:** `https://www.googleapis.com/auth/gmail.modify`
- **Python Version:** 3.10+

---

## Features

- **Send emails** — compose and send emails via the Gmail API using the standard `EmailMessage` format with Base64 URL-safe encoding
- **Search emails** — full-text and label-based Gmail search with configurable result limits and multi-label filtering
- **Dual token format support** — reads OAuth2 tokens stored as either **JSON** (`Credentials.from_authorized_user_info`) or **binary Pickle** (`pickle.load`) formats
- **Auto token refresh** — expired OAuth2 credentials are automatically refreshed using the stored `refresh_token`
- **CORS enabled** — accepts cross-origin requests from any origin
- **Configurable port** — reads `PORT` from environment variables for deployment flexibility

---

## Project Structure

```
gmailMcpServer/
├── gmailMcpServer.py    # Main server file — all MCP tools and server startup
├── config.py            # Pydantic settings — loads and validates environment variables
├── test_gmail.py        # Diagnostic utility for testing connectivity and token validity
├── pyproject.toml       # Project metadata and dependencies (uv/pip)
├── uv.lock              # Locked dependency versions
├── .python-version      # Specifies Python 3.10
├── .env                 # Environment variables (not committed to git)
└── token.json           # OAuth2 access/refresh token (not committed — binary pickle format)
```

---

## Prerequisites

- Python **3.10** or higher
- A Google Cloud project with the **Gmail API** enabled
- OAuth2 **Desktop App** credentials downloaded from Google Cloud Console
- A pre-generated `token.json` OAuth2 token file (JSON or Pickle format)
- [`uv`](https://github.com/astral-sh/uv) package manager (recommended) or `pip`

---

## Installation

### Using `uv` (recommended)

```bash
# Clone the repository
git clone https://github.com/moksh555/GmailMcpServer.git
cd GmailMcpServer

# Install dependencies
uv sync
```

### Using `pip`

```bash
pip install fastmcp>=3.1.1 \
            fastapi>=0.135.1 \
            google-api-python-client>=2.192.0 \
            google-auth-httplib2>=0.3.0 \
            google-auth-oauthlib>=1.3.0 \
            pathlib>=1.0.1 \
            pydantic>=2.12.5 \
            pydantic-settings
```

---

## Configuration

Create a `.env` file in the project root with the following variable:

```env
GMAIL_TOKEN_PATH=/path/to/token.json
```

| Variable           | Required | Description                                                   |
|--------------------|----------|---------------------------------------------------------------|
| `GMAIL_TOKEN_PATH` | Yes      | Absolute path to the `token.json` OAuth2 token file           |

The `config.py` file uses **Pydantic Settings** to load this value:

```python
class Settings(BaseSettings):
    GMAIL_TOKEN_PATH: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
```

> **Note:** Unlike the Calendar server, the Gmail server does **not** require a separate `credentials.json` path in production. Token generation must be done locally, and the resulting `token.json` is uploaded as a secret file for deployment.

---

## Google OAuth2 Authentication

This server uses the `https://www.googleapis.com/auth/gmail.modify` OAuth2 scope, which grants read/write/send access to Gmail (but not account deletion).

### Step-by-step Setup

1. **Enable the Gmail API** in your [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services → Credentials**.
3. Create **OAuth 2.0 Client ID** credentials of type **Desktop App**.
4. Download the credentials JSON file.
5. **Generate the token locally** using a standard Google OAuth2 flow (e.g., using `google-auth-oauthlib`). This produces a `token.json` file containing both an `access_token` and a `refresh_token`.
6. Upload `token.json` as a **secret file** on your deployment platform (e.g., Render) at the path specified by `GMAIL_TOKEN_PATH`.

### Token Loading Flow (inside `getGmailServices()`)

The server reads the token file in **binary mode** (`'rb'`) and attempts two formats in order:

```python
def getGmailServices():
    creds = None
    token_path = settings.GMAIL_TOKEN_PATH or "token.json"

    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            try:
                creds = pickle.load(f)           # Attempt 1: binary Pickle format
            except Exception:
                creds = Credentials.from_authorized_user_info(json.load(f))  # Attempt 2: JSON format

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())             # Auto-refresh if expired
        else:
            raise Exception(
                "No valid credentials found. Upload token.json as a secret file on Render."
            )

    return build('gmail', 'v1', credentials=creds)
```

| Format   | Detection                        | How It's Loaded                                           |
|----------|----------------------------------|-----------------------------------------------------------|
| Pickle   | Binary file (non-`{` first byte) | `pickle.load(f)` → `google.oauth2.credentials.Credentials` |
| JSON     | Text file starting with `{`      | `json.load(f)` → `Credentials.from_authorized_user_info()` |

> If neither format works and no valid credentials can be constructed, the server raises an exception instead of attempting a browser-based OAuth flow (since there is no browser in a production environment).

---

## Running the Server

```bash
# Using uv
uv run python gmailMcpServer.py

# Using python directly
python gmailMcpServer.py
```

The server starts on `http://0.0.0.0:10000` by default. To run on a different port:

```bash
PORT=8080 python gmailMcpServer.py
```

The MCP endpoint will be available at:
```
http://localhost:10000/mcp
```

---

## MCP Tools Reference

The server registers the following 2 tools with the MCP framework under the name `"Gmail"`.

---

### `sendEmail`

Composes and sends an email via the Gmail API. Uses Python's standard `email.message.EmailMessage` for message construction and Base64 URL-safe encoding for the Gmail API's `raw` message format.

**Parameters:**

| Parameter        | Type  | Required | Description                          |
|------------------|-------|----------|--------------------------------------|
| `messageBody`    | `str` | Yes      | The main text content of the email   |
| `messageTo`      | `str` | Yes      | Recipient's email address            |
| `messageFrom`    | `str` | Yes      | Sender's email address               |
| `messageSubject` | `str` | Yes      | Subject line of the email            |

**Returns:**
- On success: `"Email sent successfully! Message ID: <gmail_message_id>"`
- On failure: `"An error occurred: <HttpError details>"`

**Internal Flow:**
1. Builds an `EmailMessage` object with `set_content()`, `To`, `From`, and `Subject` headers
2. Encodes the message bytes using `base64.urlsafe_b64encode`
3. Calls `gmail.users().messages().send(userId="me", body={"raw": encoded_message})`

**Example:**
```json
{
  "messageBody": "Hi Alice,\n\nJust a reminder about tomorrow's meeting at 10 AM.\n\nBest,\nMoksh",
  "messageTo": "alice@example.com",
  "messageFrom": "moksh@example.com",
  "messageSubject": "Meeting Reminder"
}
```

**Example Response:**
```
Email sent successfully! Message ID: 18f4a3b2c1d0e9f8
```

---

### `searchMessages`

Searches Gmail for messages matching a query and optional label filters. Returns a formatted summary of each matching message including its metadata, labels, and snippet.

**Parameters:**

| Parameter    | Type         | Required | Default        | Description                                                         |
|--------------|--------------|----------|----------------|---------------------------------------------------------------------|
| `query`      | `str`        | Yes      | —              | Gmail search query (supports all Gmail search operators)            |
| `category`   | `list[str]`  | No       | `["INBOX"]`    | List of Gmail label IDs to filter by (can include multiple labels)  |
| `maxResults` | `int`        | No       | `5`            | Maximum number of messages to return                                |

**Supported Gmail Search Query Operators:**

| Operator              | Example                  | Description                          |
|-----------------------|--------------------------|--------------------------------------|
| `from:`               | `from:boss@company.com`  | Filter by sender                     |
| `to:`                 | `to:me`                  | Filter by recipient                  |
| `subject:`            | `subject:Invoice`        | Filter by subject line               |
| `label:`              | `label:unread`           | Filter by label                      |
| `is:`                 | `is:starred`             | Filter by message state              |
| `has:`                | `has:attachment`         | Filter by attachment presence        |
| `after:` / `before:`  | `after:2026/01/01`       | Filter by date range                 |
| Plain text            | `Uber receipt`           | Full-text search across all fields   |

**Common `category` Label Values:**

| Label ID               | Description            |
|------------------------|------------------------|
| `INBOX`                | Messages in the inbox  |
| `UNREAD`               | Unread messages        |
| `SENT`                 | Sent messages          |
| `STARRED`              | Starred messages       |
| `CATEGORY_SOCIAL`      | Social category        |
| `CATEGORY_UPDATES`     | Updates category       |
| `CATEGORY_FORUMS`      | Forums category        |
| `CATEGORY_PROMOTIONS`  | Promotions category    |

**Returns:**
A `str` with each message separated by `---`, formatted as:
```
ID: <message_id>
/* Metadata: { Category: <CATEGORY_label>, Labels: [<all_labels>] } */
Snippet: <preview_text>

---

ID: <message_id>
/* Metadata: { Category: NO_CATEGORY, Labels: [INBOX, UNREAD] } */
Snippet: <preview_text>
```

Returns `"No messages found for that query."` if there are no matches.

**Example — Search for Uber receipts in inbox:**
```json
{
  "query": "from:Uber",
  "category": ["INBOX"],
  "maxResults": 3
}
```

**Example — Search for unread messages:**
```json
{
  "query": "is:unread",
  "category": ["INBOX", "UNREAD"],
  "maxResults": 10
}
```

---

## Diagnostic Utility

The `test_gmail.py` file is a standalone diagnostic script for debugging credential and connectivity issues. It is **not part of the MCP server** and does not need to be run in production.

### What It Tests

```
[1/4] Testing Google Cloud Client initialization...
      Checks if google-cloud-secret-manager client can be initialized.

[2/4] Attempting to pull secret from Secret Manager...
      Tests Secret Manager access and validates if the payload is JSON or binary.

[3/4] Checking local 'token.json'...
      Checks if token.json exists, reports its size, reads the first byte,
      and detects whether it is a TEXT/JSON file or BINARY/PICKLE file.

[4/4] Checking if current identity has access...
      Runs `gcloud auth application-default print-access-token` to verify ADC identity.
```

### How to Run

```bash
# First, configure SECRET_NAME in test_gmail.py
python test_gmail.py
```

> **Configuration required:** Before running, update the `SECRET_NAME` constant at the top of `test_gmail.py` with your actual Google Cloud Secret Manager resource path:
> ```python
> SECRET_NAME = "projects/YOUR_PROJECT_ID/secrets/YOUR_SECRET_NAME/versions/latest"
> ```

---

## Dependencies

Declared in `pyproject.toml`:

| Package                      | Version     | Purpose                                           |
|------------------------------|-------------|---------------------------------------------------|
| `fastmcp`                    | `>=3.1.1`   | MCP server framework (HTTP transport, tool registry) |
| `fastapi`                    | `>=0.135.1` | ASGI web framework (used by FastMCP's HTTP transport) |
| `google-api-python-client`   | `>=2.192.0` | Gmail API v1 client                               |
| `google-auth-httplib2`       | `>=0.3.0`   | HTTP adapter for Google Auth                      |
| `google-auth-oauthlib`       | `>=1.3.0`   | OAuth2 flow for credential generation             |
| `pathlib`                    | `>=1.0.1`   | Path utilities for locating `.env` file           |
| `pydantic`                   | `>=2.12.5`  | Data validation                                   |
| `pydantic-settings`          | (transitive)| Environment variable loading via `.env`            |

**Standard library modules used:**
- `json` — Parsing JSON token files
- `pickle` — Loading binary/pickle token files
- `os` — Environment variable access, file existence checks
- `base64` — URL-safe Base64 encoding for Gmail API raw messages
- `email.message` — `EmailMessage` construction

---

## Environment Variables

| Variable           | Source      | Description                                               |
|--------------------|-------------|-----------------------------------------------------------|
| `GMAIL_TOKEN_PATH` | `.env` file | Path to `token.json` (OAuth2 access + refresh token)      |
| `PORT`             | System env  | HTTP port the server listens on (default: `10000`)         |

---

## Deployment

This server is designed for deployment on platforms like **Render**, **Railway**, or **Fly.io**.

### Render Deployment

1. Push this repository to GitHub.
2. Create a new **Web Service** on Render pointing to this repo.
3. Set the **Start Command** to:
   ```bash
   python gmailMcpServer.py
   ```
4. Add the following **Secret File** in Render's environment settings:
   - `token.json` at path `/etc/secrets/token.json`
5. Add the following **Environment Variable**:
   ```
   GMAIL_TOKEN_PATH=/etc/secrets/token.json
   ```

> **Important:** Generate `token.json` locally first by completing the OAuth2 browser flow, then upload it as a secret file. There is no browser available on the production server to complete the OAuth2 flow.

### MCP Client Configuration

To connect an MCP client (e.g., Claude Agent SDK):

```python
mcpServers = {
    "Gmail": {
        "type": "http",
        "url": "https://your-render-service.onrender.com/mcp",
    }
}
```

### CloseBot Integration Example

This server is used in the CloseBot AI agent project:

```python
# mcpConfig.py
mcpServers = {
    "Gmail": {
        "type": "http",
        "url": settings.GMAIL_MCP_SERVER,  # e.g., https://gmailmcpserver.onrender.com/mcp
    },
}
```
