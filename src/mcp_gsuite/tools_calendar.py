from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from . import gauth
from . import calendar
import json
from . import toolhandler

CALENDAR_ID_ARG="__calendar_id__"

def get_calendar_id_arg_schema() -> dict[str, str]:
    return {
        "type": "string",
        "description": """Optional ID of the specific agenda for which you are executing this action.
                        If not provided, the default calendar is being used.
                        If not known, the specific calendar id can be retrieved with the list_calendars tool""",
        "default": "primary"
    }


class ListCalendarsToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("list_calendars")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="""Lists all calendars accessible by the user.
            Call it before any other tool whenever the user specifies a particular agenda (Family, Holidays, etc.).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                },
                "required": [toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        calendar_service = calendar.CalendarService(user_id=user_id)
        calendars = calendar_service.list_calendars()

        return [
            TextContent(
                type="text",
                text=json.dumps(calendars, indent=2)
            )
        ]

class GetCalendarEventsToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("get_calendar_events")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Retrieves calendar events from the user's Google Calendar within a specified time range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "__calendar_id__": get_calendar_id_arg_schema(),
                    "time_min": {
                        "type": "string",
                        "description": "Start time in RFC3339 format (e.g. 2024-12-01T00:00:00Z). Defaults to current time if not specified."
                    },
                    "time_max": {
                        "type": "string",
                        "description": "End time in RFC3339 format (e.g. 2024-12-31T23:59:59Z). Optional."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return (1-2500)",
                        "minimum": 1,
                        "maximum": 2500,
                        "default": 250
                    },
                    "show_deleted": {
                        "type": "boolean",
                        "description": "Whether to include deleted events",
                        "default": False
                    }
                },
                "required": [toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        calendar_service = calendar.CalendarService(user_id=user_id)
        events = calendar_service.get_events(
            time_min=args.get('time_min'),
            time_max=args.get('time_max'),
            max_results=args.get('max_results', 250),
            show_deleted=args.get('show_deleted', False),
            calendar_id=args.get(CALENDAR_ID_ARG, 'primary'),
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(events, indent=2)
            )
        ]

class CreateCalendarEventToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("create_calendar_event")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Creates a new event in a specified Google Calendar of the specified user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "__calendar_id__": get_calendar_id_arg_schema(),
                    "summary": {
                        "type": "string",
                        "description": "Title of the event"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location of the event (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description or notes for the event (optional)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in RFC3339 format (e.g. 2024-12-01T10:00:00Z)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in RFC3339 format (e.g. 2024-12-01T11:00:00Z)"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of attendee email addresses (optional)"
                    },
                    "send_notifications": {
                        "type": "boolean",
                        "description": "Whether to send notifications to attendees",
                        "default": True
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for the event (e.g. 'America/New_York'). Defaults to UTC if not specified."
                    }
                },
                "required": [toolhandler.USER_ID_ARG, "summary", "start_time", "end_time"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        # Validate required arguments
        required = ["summary", "start_time", "end_time"]
        if not all(key in args for key in required):
            raise RuntimeError(f"Missing required arguments: {', '.join(required)}")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        calendar_service = calendar.CalendarService(user_id=user_id)
        event = calendar_service.create_event(
            summary=args["summary"],
            start_time=args["start_time"],
            end_time=args["end_time"],
            location=args.get("location"),
            description=args.get("description"),
            attendees=args.get("attendees", []),
            send_notifications=args.get("send_notifications", True),
            timezone=args.get("timezone"),
            calendar_id=args.get(CALENDAR_ID_ARG, 'primary'),
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(event, indent=2)
            )
        ]

class DeleteCalendarEventToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("delete_calendar_event")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Deletes an event from the user's Google Calendar by its event ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema(),
                    "__calendar_id__": get_calendar_id_arg_schema(),
                    "event_id": {
                        "type": "string",
                        "description": "The ID of the calendar event to delete"
                    },
                    "send_notifications": {
                        "type": "boolean",
                        "description": "Whether to send cancellation notifications to attendees",
                        "default": True
                    }
                },
                "required": [toolhandler.USER_ID_ARG, "event_id"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "event_id" not in args:
            raise RuntimeError("Missing required argument: event_id")

        user_id = args.get(toolhandler.USER_ID_ARG)
        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        calendar_service = calendar.CalendarService(user_id=user_id)
        success = calendar_service.delete_event(
            event_id=args["event_id"],
            send_notifications=args.get("send_notifications", True),
            calendar_id=args.get(CALENDAR_ID_ARG, 'primary'),
        )

        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": success,
                    "message": "Event successfully deleted" if success else "Failed to delete event"
                }, indent=2)
            )
        ]

class ListCalendarEventColorToolHandler(toolhandler.ToolHandler):
    def __init__(self):
        super().__init__("list_calendar_event_color")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description="Lists available event colors from the user's Google Calendar by its event ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "__user_id__": self.get_user_id_arg_schema()
                },
                "required": [toolhandler.USER_ID_ARG]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        user_id = args.get(toolhandler.USER_ID_ARG)

        if not user_id:
            raise RuntimeError(f"Missing required argument: {toolhandler.USER_ID_ARG}")

        calendar_service = calendar.CalendarService(user_id=user_id)
        colors = calendar_service.list_colors()

        return [
            TextContent(
                type="text",
                text=json.dumps(colors, indent=2)
            )
        ]