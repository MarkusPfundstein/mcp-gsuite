
import logging
from collections.abc import Sequence
from functools import lru_cache
import subprocess
from typing import Any
import traceback
from dotenv import load_dotenv
from mcp.server import Server
import threading
import sys
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
from . import gauth
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import (
    urlparse,
    parse_qs,
)

class OauthListener(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/code":
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(url.query)
        if "code" not in query:
            self.send_response(400)
            self.end_headers()
            return
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Auth successful! You can close the tab!".encode("utf-8"))
        self.wfile.flush()

        storage = {}
        creds = gauth.get_credentials(authorization_code=query["code"][0], state=storage)

        t = threading.Thread(target = self.server.shutdown)
        t.daemon = True
        t.start()

        

load_dotenv()

from . import tools_gmail
from . import tools_calendar
from . import toolhandler


# Load environment variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-gsuite")

def start_auth_flow(user_id: str):
    auth_url = gauth.get_authorization_url(user_id, state={})
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        subprocess.Popen(['open', auth_url])
    else:
        import webbrowser
        webbrowser.open(auth_url)

    # start server for code callback
    server_address = ('', 4100)
    server = HTTPServer(server_address, OauthListener)
    server.serve_forever()


def setup_oauth2(user_id: str):
    accounts = gauth.get_account_info()
    if len(accounts) == 0:
        raise RuntimeError("No accounts specified in .gauth.json")
    if user_id not in [a.email for a in accounts]:
        raise RuntimeError(f"Account for email: {user_id} not specified in .gauth.json")

    credentials = gauth.get_stored_credentials(user_id=user_id)
    if not credentials:
        start_auth_flow(user_id=user_id)
    else:
        if credentials.access_token_expired:
            logger.error("credentials expired. try refresh")

        # this call refreshes access token
        user_info = gauth.get_user_info(credentials=credentials)
        #logging.error(f"User info: {json.dumps(user_info)}")
        gauth.store_credentials(credentials=credentials, user_id=user_id)


app = Server("mcp-gsuite")

tool_handlers = {}
def add_tool_handler(tool_class: toolhandler.ToolHandler):
    global tool_handlers

    tool_handlers[tool_class.name] = tool_class

def get_tool_handler(name: str) -> toolhandler.ToolHandler | None:
    if name not in tool_handlers:
        return None

    return tool_handlers[name]

add_tool_handler(tools_gmail.QueryEmailsToolHandler())
add_tool_handler(tools_gmail.GetEmailByIdToolHandler())
add_tool_handler(tools_gmail.CreateDraftToolHandler())
add_tool_handler(tools_gmail.DeleteDraftToolHandler())
add_tool_handler(tools_gmail.ReplyEmailToolHandler())
add_tool_handler(tools_gmail.GetAttachmentToolHandler())
add_tool_handler(tools_gmail.BulkGetEmailsByIdsToolHandler())
add_tool_handler(tools_gmail.BulkSaveAttachmentsToolHandler())

add_tool_handler(tools_calendar.ListCalendarsToolHandler())
add_tool_handler(tools_calendar.GetCalendarEventsToolHandler())
add_tool_handler(tools_calendar.CreateCalendarEventToolHandler())
add_tool_handler(tools_calendar.DeleteCalendarEventToolHandler())
add_tool_handler(tools_calendar.ListCalendarEventColorToolHandler())

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""

    return [th.get_tool_description() for th in tool_handlers.values()]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    try:
        if not isinstance(arguments, dict):
            raise RuntimeError("arguments must be dictionary")

        if toolhandler.USER_ID_ARG not in arguments:
            raise RuntimeError("user_id argument is missing in dictionary.")

        setup_oauth2(user_id=arguments.get(toolhandler.USER_ID_ARG, ""))

        tool_handler = get_tool_handler(name)
        if not tool_handler:
            raise ValueError(f"Unknown tool: {name}")

        return tool_handler.run_tool(arguments)
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f"Error during call_tool: str(e)")
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")


async def main():
    logging.info(f"Platform: {sys.platform}")
    accounts = gauth.get_account_info()
    for account in accounts:
        creds = gauth.get_stored_credentials(user_id=account.email)
        if creds:
            logging.info(f"found credentials for {account.email}")

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )