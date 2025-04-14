from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from . import gmail
import json
from . import toolhandler
import base64

def decode_base64_data(file_data):
    standard_base64_data = file_data.replace("-", "+").replace("_", "/")
    missing_padding = len(standard_base64_data) % 4
    if missing_padding:
        standard_base64_data += '=' * (4 - missing_padding)
    return base64.b64decode(standard_base64_data, validate=True)

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
            description="Retrieves a complete Gmail email message by its ID, including the full message body and attachment IDs.",
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
        email, attachments = gmail_service.get_email_by_id_with_attachments(args["email_id"])

        if email is None:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to retrieve email with ID: {args['email_id']}"
                )
            ]

        email["attachments"] = attachments

        return [
            TextContent(
                type="text",
                text=json.dumps(email, indent=2)
            )
        ]

class BulkGetEmailsByIdsToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("bulk_get_gmail_emails")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Retrieves multiple Gmail email messages by their IDs in a single request, including the full message bodies and attachment IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "email_ids": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of Gmail message IDs to retrieve"
                    }
                },
                "required": ["email_ids", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "email_ids" not in args:
            raise RuntimeError("Missing required argument: email_ids")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        
        results = []
        for email_id in args["email_ids"]:
            email, attachments = gmail_service.get_email_by_id_with_attachments(email_id)
            if email is not None:
                email["attachments"] = attachments
                results.append(email)

        if not results:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to retrieve any emails from the provided IDs"
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]

class CreateDraftToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("create_gmail_draft")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="""Creates a draft email message from scratch in Gmail with specified recipient, subject, body, and optional CC recipients.
            
            Do NOT use this tool when you want to draft or send a REPLY to an existing message. This tool does NOT include any previous message content. Use the reply_gmail_email tool
            with send=False instead."
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
            description="""Creates a reply to an existing Gmail email message and either sends it or saves as draft.

            Use this tool if you want to draft a reply. Use the 'cc' argument if you want to perform a "reply all".
            """,
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
            reply_body=args.get("reply_body", ""),
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

class GetAttachmentToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("get_gmail_attachment")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Retrieves a Gmail attachment by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "message_id": {
                        "type": "string",
                        "description": "The ID of the Gmail message containing the attachment"
                    },
                    "attachment_id": {
                        "type": "string",
                        "description": "The ID of the attachment to retrieve"
                    },
                    "mime_type": {
                        "type": "string",
                        "description": "The MIME type of the attachment"
                    },
                    "filename": {
                        "type": "string",
                        "description": "The filename of the attachment"
                    },
                    "save_to_disk": {
                        "type": "string",
                        "description": "The fullpath to save the attachment to disk. If not provided, the attachment is returned as a resource."
                    }
                },
                "required": ["message_id", "attachment_id", "mime_type", "filename", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "message_id" not in args:
            raise RuntimeError("Missing required argument: message_id")
        if "attachment_id" not in args:
            raise RuntimeError("Missing required argument: attachment_id")
        if "mime_type" not in args:
            raise RuntimeError("Missing required argument: mime_type")
        if "filename" not in args:
            raise RuntimeError("Missing required argument: filename")
        filename = args["filename"]
        mime_type = args["mime_type"]
        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")
        gmail_service = gmail.GmailService(user_id=user_id)
        attachment_data = gmail_service.get_attachment(args["message_id"], args["attachment_id"])

        if attachment_data is None:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to retrieve attachment with ID: {args['attachment_id']} from message: {args['message_id']}"
                )
            ]

        file_data = attachment_data["data"]
        attachment_url = f"attachment://gmail/{args['message_id']}/{args['attachment_id']}/{filename}"
        if args.get("save_to_disk"):
            decoded_data = decode_base64_data(file_data)
            with open(args["save_to_disk"], "wb") as f:
                f.write(decoded_data)
            return [
                TextContent(
                    type="text",
                    text=f"Attachment saved to disk: {args['save_to_disk']}"
                )
            ]
        return [
            EmbeddedResource(
                type="resource",
                resource={
                    "blob": file_data,
                    "uri": attachment_url,
                    "mimeType": mime_type,
                },
            )
        ]

class BulkSaveAttachmentsToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("bulk_save_gmail_attachments")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Saves multiple Gmail attachments to disk by their message IDs and attachment IDs in a single request.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "attachments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "message_id": {
                                    "type": "string",
                                    "description": "ID of the Gmail message containing the attachment"
                                },
                                "part_id": {
                                    "type": "string", 
                                    "description": "ID of the part containing the attachment"
                                },
                                "save_path": {
                                    "type": "string",
                                    "description": "Path where the attachment should be saved"
                                }
                            },
                            "required": ["message_id", "part_id", "save_path"]
                        }
                    }
                },
                "required": ["attachments", toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "attachments" not in args:
            raise RuntimeError("Missing required argument: attachments")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        gmail_service = gmail.GmailService(user_id=user_id)
        results = []

        for attachment_info in args["attachments"]:
            # get attachment data from message_id and part_id
            message, attachments = gmail_service.get_email_by_id_with_attachments(
                attachment_info["message_id"]
            )
            if message is None:
                results.append(
                    TextContent(
                        type="text",
                        text=f"Failed to retrieve message with ID: {attachment_info['message_id']}"
                    )
                )
                continue
            # get attachment_id from part_id
            attachment_id = attachments[attachment_info["part_id"]]["attachmentId"]
            attachment_data = gmail_service.get_attachment(
                attachment_info["message_id"], 
                attachment_id
            )
            if attachment_data is None:
                results.append(
                    TextContent(
                        type="text",
                        text=f"Failed to retrieve attachment with ID: {attachment_id} from message: {attachment_info['message_id']}"
                    )
                )
                continue

            file_data = attachment_data["data"]
            try:    
                decoded_data = decode_base64_data(file_data)
                with open(attachment_info["save_path"], "wb") as f:
                    f.write(decoded_data)
                results.append(
                    TextContent(
                        type="text",
                        text=f"Attachment saved to: {attachment_info['save_path']}"
                    )
                )
            except Exception as e:
                results.append(
                    TextContent(
                        type="text",
                        text=f"Failed to save attachment to {attachment_info['save_path']}: {str(e)}"
                    )
                )
                continue

        return results
