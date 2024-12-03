from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from . import gauth
from . import gmail
import json
from . import toolhandler



class QueryEmailsToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("query_gmail_emails")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="""Query Gmail emails based on an optional search query. 
            Returns emails in reverse chronological order (newest first).
            Returns metadata such as subject and also a short summary of the content.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "query": {
                        "type": "string",
                        "description": """Gmail search query (optional). Examples:
                            - a $string: Search email body, subject, and sender information for $string
                            - 'is:unread' for unread emails
                            - 'from:example@gmail.com' for emails from a specific sender
                            - 'newer_than:2d' for emails from last 2 days
                            - 'has:attachment' for emails with attachments
                            If not provided, returns recent emails without filtering.""",
                        "required": False
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to retrieve (1-500)",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 100
                    }
                },
                "required": [toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        gmail_service = gmail.GmailService(user_id=user_id)
        query = args.get('query')
        max_results = args.get('max_results', 100)
        emails = gmail_service.query_emails(query=query, max_results=max_results)

        return [
            TextContent(
                type="text",
                text=json.dumps(emails, indent=2)
            )
        ]
    
class GetEmailByIdToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("get_gmail_email")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Retrieves a complete Gmail email message by its ID, including the full message body.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "email_id": {
                        "type": "string",
                        "description": "The ID of the Gmail message to retrieve"
                    }
                },
                "required": ["email_id", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "email_id" not in args:
            raise RuntimeError("Missing required argument: email_id")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        email = gmail_service.get_email_by_id(args["email_id"])

        if email is None:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to retrieve email with ID: {args['email_id']}"
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps(email, indent=2)
            )
        ]
    

class CreateDraftToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("create_gmail_draft")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="""Creates a draft email message from scratch in Gmail with specified recipient, subject, body, and optional CC recipients.
            
            This tool does NOT include any previous message content, so if you want to create a draft reply, use the reply_gmail_email tool
            with send=False."
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "to": {
                        "type": "string",
                        "description": "Email address of the recipient"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line of the email"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body content of the email"
                    },
                    "cc": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of email addresses to CC"
                    }
                },
                "required": ["to", "subject", "body", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        required = ["to", "subject", "body"]
        if not all(key in args for key in required):
            raise RuntimeError(f"Missing required arguments: {', '.join(required)}")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        draft = gmail_service.create_draft(
            to=args["to"],
            subject=args["subject"],
            body=args["body"],
            cc=args.get("cc")
        )

        if draft is None:
            return [
                TextContent(
                    type="text",
                    text="Failed to create draft email"
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps(draft, indent=2)
            )
        ]
    
class DeleteDraftToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("delete_gmail_draft")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Deletes a Gmail draft message by its ID. This action cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "draft_id": {
                        "type": "string",
                        "description": "The ID of the draft to delete"
                    }
                },
                "required": ["draft_id", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "draft_id" not in args:
            raise RuntimeError("Missing required argument: draft_id")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        success = gmail_service.delete_draft(args["draft_id"])

        return [
            TextContent(
                type="text",
                text="Successfully deleted draft" if success else f"Failed to delete draft with ID: {args['draft_id']}"
            )
        ]
    
class ReplyEmailToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("reply_gmail_email")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Creates a reply to an existing Gmail email message and either sends it or saves as draft.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "original_message_id": {
                        "type": "string",
                        "description": "The ID of the Gmail message to reply to"
                    },
                    "reply_body": {
                        "type": "string",
                        "description": "The body content of your reply message"
                    },
                    "send": {
                        "type": "boolean",
                        "description": "If true, sends the reply immediately. If false, saves as draft.",
                        "default": False
                                    },
                    "cc": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of email addresses to CC on the reply"
                    }
                },
                "required": ["original_message_id", "reply_body", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if not all(key in args for key in ["original_message_id", "reply_body"]):
            raise RuntimeError("Missing required arguments: original_message_id and reply_body")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        
        # First get the original message to extract necessary information
        original_message = gmail_service.get_email_by_id(args["original_message_id"])
        if original_message is None:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to retrieve original message with ID: {args['original_message_id']}"
                )
            ]

        # Create and send/draft the reply
        result = gmail_service.create_reply(
            original_message=original_message,
            reply_body=args["reply_body"],
            send=args.get("send", False),
            cc=args.get("cc")
        )

        if result is None:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to {'send' if args.get('send', True) else 'draft'} reply email"
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )
        ]