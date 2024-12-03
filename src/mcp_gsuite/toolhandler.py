from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

import os

USER_ID_ARG = "__user_id__"

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_supported_emails(self) -> list[str]:
        return os.getenv("GOOGLE_EMAILS").split(":")
    
    def get_supported_emails_tool_text(self) -> str:
        return f"""This tool requires a authorized google email for {USER_ID_ARG} argument. You can choose one of: {', '.join(self.get_supported_emails())}"""

    def get_user_id_arg_schema(self) -> dict:
        return {
            "type": "string",
            "description": f"The EMAIL of the google account for which you are executing this action. Can be one of: {', '.join(self.get_supported_emails())}"
        }

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()