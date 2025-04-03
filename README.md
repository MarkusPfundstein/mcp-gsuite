# mcp-gsuite MCP server

[![smithery badge](https://smithery.ai/badge/mcp-gsuite)](https://smithery.ai/server/mcp-gsuite)
MCP server to interact with Google products.

## Example prompts

Right now, this MCP server supports Gmail and Calendar integration with the following capabilities:

1. General
* Multiple google accounts

2. Gmail
* Get your Gmail user information
* Query emails with flexible search (e.g., unread, from specific senders, date ranges, with attachments)
* Retrieve complete email content by ID
* Create new draft emails with recipients, subject, body and CC options
* Delete draft emails
* Reply to existing emails (can either send immediately or save as draft)
* Retrieve multiple emails at once by their IDs.
* Save multiple attachments from emails to your local system.

3. Calendar
* Manage multiple calendars
* Get calendar events within specified time ranges
* Create calendar events with:
  + Title, start/end times
  + Optional location and description
  + Optional attendees
  + Custom timezone support
  + Notification preferences
* Delete calendar events

Example prompts you can try:

* Retrieve my latest unread messages
* Search my emails from the Scrum Master
* Retrieve all emails from accounting
* Take the email about ABC and summarize it
* Write a nice response to Alice's last email and upload a draft.
* Reply to Bob's email with a Thank you note. Store it as draft

* What do I have on my agenda tomorrow?
* Check my private account's Family agenda for next week
* I need to plan an event with Tim for 2hrs next week. Suggest some time slots.

## Quickstart

### Install

#### Option 1: Installing via Smithery

To install mcp-gsuite for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-gsuite):

```bash
npx -y @smithery/cli install mcp-gsuite --client claude
```

#### Option 2: Manual via OAuth2

To allow MCP to access your Gmail accounts, you need to configure two things:

1. Enable the Google Workspace API on a cloud project, download the credentials, and configure the callback endpoint correctly. This is done through the `.gauth.json` file, which you can download from the Google Cloud Console (see configuration steps below).

```json
{
    "web": {
        "client_id": "$your_client_id",
        "client_secret": "$your_client_secret",
        "redirect_uris": ["http://localhost:4100/code"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}
```

* (Optional) Use the `--gauth-file` to point to your `.gauth.json` file.

Follow these steps to set up authentication:

  a. Create OAuth2 Credentials:
    - Go to the [Google Cloud Console](https://console.cloud.google.com/)
    - Create a new project or select an existing one
    - Enable the Gmail API and Google Calendar API for your project
    - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
    - Select "Desktop app" or "Web application" as the application type
    - Configure the OAuth consent screen with required information
    - Add authorized redirect URIs (include `http://localhost:4100/code` for local development)

  b. Configure required OAuth2 scopes:
    

  ```json
    [
      "openid",
      "https://mail.google.com/",
      "https://www.googleapis.com/auth/calendar",
      "https://www.googleapis.com/auth/userinfo.email"
    ]
  ```

  c. Download

  ![gauth.json](https://github.com/user-attachments/assets/5a31ef43-dea7-4f45-b4f9-fdb72471864d)

2. The second step is to specify which accounts to grant access to via browser authentication. This is configured in the `accounts.json` file, which you create manually. In this file, you specify the email addresses you want to grant access to, along with optional account types and any additional information you'd like to include.

```json
{
    "accounts": [
        {
            "email": "alice@bob.com",
            "account_type": "personal",
            "extra_info": "Additional info that you want to tell Claude: E.g. 'Contains Family Calendar'"
        }
    ]
}
```

* (Optional) Use the `--accounts-file` flag to point to your `accounts.json` file.

You can specifiy multiple accounts. Make sure they have access in your Google Auth app. The `extra_info` field is especially interesting as you can add info here that you want to tell the AI about the account (e.g. whether it has a specific agenda)

Note: When you first execute one of the tools for a specific account, a browser will open, redirect you to Google and ask for your credentials, scope, etc. After a successful login, it stores the credentials in a local file called `.oauth.{email}.json` . Once you are authorized, the refresh token will be used.

3. (Optional) You can configure a credentials directory using the following option:
* `--credentials-dir`: Specifies the directory where OAuth credentials are stored after successful authentication. The default location is the current working directory, with credentials stored in subdirectories named `.oauth.{email}.json` for each account.

Example usage:

```bash
uv run mcp-gsuite --gauth-file /path/to/custom/.gauth.json --accounts-file /path/to/custom/.accounts.json --credentials-dir /path/to/custom/credentials
```

These flags are particularly useful when you have multiple instances of the server running with different configurations or when deploying to environments where the default paths are not suitable.


#### Claude Desktop

See [this youtube link](https://www.youtube.com/watch?v=wxCCzo9dGj0&t=82s&ab_channel=WesHigbee) on how to configure Claude Desktop to use the MCP server.

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  

```json
{
  "mcpServers": {
    "mcp-gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-gsuite",
        "run",
        "mcp-gsuite"
      ]
    }
  }
}
```


Note: You can also use the `uv run mcp-gsuite --accounts-file /path/to/custom/.accounts.json` to specify a different accounts file or `--credentials-dir /path/to/custom/credentials` to specify a different credentials directory.

```json
{
  "mcpServers": {
    "mcp-gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-gsuite",
        "run",
        "mcp-gsuite",
        "--accounts-file",
        "/path/to/custom/.accounts.json",
        "--credentials-dir",
        "/path/to/custom/credentials"
      ]
    }
  }
}
```

</details>

<details>
  <summary>Published Servers Configuration</summary>
  

```json
{
  "mcpServers": {
    "mcp-gsuite": {
      "command": "uvx",
      "args": [
        "mcp-gsuite",
        "--accounts-file",
        "/path/to/custom/.accounts.json",
        "--credentials-dir",
        "/path/to/custom/credentials"
      ]
    }
  }
}
```

</details>



## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:

```bash
uv sync
```

2. Build package distributions:

```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:

```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
* Token: `--token` or `UV_PUBLISH_TOKEN`
* Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [ `npm` ](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-gsuite run mcp-gsuite
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-gsuite.log
```
