"""Database seed helpers for development use."""

from __future__ import annotations

import json
from typing import Any, Dict

from scheduler_api.db.models import WorkflowRecord
from scheduler_api.db.session import SessionLocal


DEMO_WORKFLOW_ID = "wf-demo"

DEMO_WORKFLOW_DEFINITION: Dict[str, Any] = {
    "id": DEMO_WORKFLOW_ID,
    "schemaVersion": "2025-10",
    "metadata": {"name": "Demo Workflow"},
    "nodes": [
        {
            "id": "node-config",
            "type": "example.pkg.load_config",
            "package": {"name": "example.pkg", "version": "1.0.0"},
            "adapter": "demo",
            "handler": "load_config",
            "status": "published",
            "category": "Examples",
            "label": "Load Configuration",
            "position": {"x": -900, "y": 0},
            "parameters": {
                "config": "{\n  \"recipient\": \"demo@example.com\",\n  \"channel\": \"email\",\n  \"message\": \"Hello from AstraFlow!\"\n}"
            },
            "ui": {
                "outputPorts": [
                    {
                        "key": "output",
                        "label": "Config",
                        "binding": {"path": "/results/config", "mode": "write"}
                    }
                ],
                "widgets": [
                    {
                        "key": "config",
                        "label": "Configuration JSON",
                        "component": "json",
                        "binding": {"path": "/parameters/config", "mode": "write"}
                    }
                ]
            },
        },
        {
            "id": "node-transform",
            "type": "example.pkg.transform_text",
            "package": {"name": "example.pkg", "version": "1.0.0"},
            "adapter": "demo",
            "handler": "transform_text",
            "status": "published",
            "category": "Examples",
            "label": "Transform Text",
            "position": {"x": -450, "y": 0},
            "parameters": {"text": "Hello from AstraFlow!", "mode": "uppercase"},
            "ui": {
                "inputPorts": [
                    {
                        "key": "input",
                        "label": "Text",
                        "binding": {"path": "/parameters/text", "mode": "write"}
                    }
                ],
                "outputPorts": [
                    {
                        "key": "output",
                        "label": "Transformed",
                        "binding": {"path": "/results/output", "mode": "write"}
                    }
                ],
                "widgets": [
                    {
                        "key": "text",
                        "label": "Text",
                        "component": "text",
                        "binding": {"path": "/parameters/text", "mode": "write"}
                    },
                    {
                        "key": "mode",
                        "label": "Mode",
                        "component": "text",
                        "binding": {"path": "/parameters/mode", "mode": "write"},
                        "options": {"helperText": "Choose between uppercase, lowercase, title, or reverse."}
                    }
                ]
            },
        },
        {
            "id": "node-delay",
            "type": "example.pkg.delay",
            "package": {"name": "example.pkg", "version": "1.0.0"},
            "adapter": "demo",
            "handler": "delay",
            "status": "published",
            "category": "Examples",
            "label": "Delay",
            "position": {"x": 0, "y": 0},
            "parameters": {"durationSeconds": 1.5},
            "ui": {
                "inputPorts": [
                    {
                        "key": "input",
                        "label": "Start",
                        "binding": {"path": "/parameters/durationSeconds", "mode": "write"}
                    }
                ],
                "outputPorts": [
                    {
                        "key": "output",
                        "label": "Done",
                        "binding": {"path": "/results/durationSeconds", "mode": "write"}
                    }
                ],
                "widgets": [
                    {
                        "key": "durationSeconds",
                        "label": "Duration (seconds)",
                        "component": "number",
                        "binding": {"path": "/parameters/durationSeconds", "mode": "write"}
                    }
                ]
            },
        },
        {
            "id": "node-notify",
            "type": "example.pkg.send_notification",
            "package": {"name": "example.pkg", "version": "1.0.0"},
            "adapter": "demo",
            "handler": "send_notification",
            "status": "published",
            "category": "Examples",
            "label": "Send Notification",
            "position": {"x": 450, "y": 0},
            "parameters": {
                "recipient": "demo@example.com",
                "channel": "email",
                "message": "Hello from AstraFlow!",
            },
            "ui": {
                "inputPorts": [
                    {
                        "key": "input",
                        "label": "Payload",
                        "binding": {"path": "/parameters/message", "mode": "write"}
                    }
                ],
                "outputPorts": [
                    {
                        "key": "output",
                        "label": "Notification",
                        "binding": {"path": "/results/notificationId", "mode": "write"}
                    }
                ],
                "widgets": [
                    {
                        "key": "recipient",
                        "label": "Recipient",
                        "component": "text",
                        "binding": {"path": "/parameters/recipient", "mode": "write"}
                    },
                    {
                        "key": "channel",
                        "label": "Channel",
                        "component": "text",
                        "binding": {"path": "/parameters/channel", "mode": "write"}
                    },
                    {
                        "key": "message",
                        "label": "Message",
                        "component": "textarea",
                        "binding": {"path": "/parameters/message", "mode": "write"}
                    }
                ]
            },
        },
        {
            "id": "node-audit",
            "type": "example.pkg.audit_log",
            "package": {"name": "example.pkg", "version": "1.0.0"},
            "adapter": "demo",
            "handler": "audit_log",
            "status": "published",
            "category": "Examples",
            "label": "Audit Log",
            "position": {"x": 900, "y": 0},
            "parameters": {"level": "info", "message": "Demo workflow completed."},
            "ui": {
                "inputPorts": [
                    {
                        "key": "input",
                        "label": "Event",
                        "binding": {"path": "/parameters/message", "mode": "write"}
                    }
                ],
                "widgets": [
                    {
                        "key": "level",
                        "label": "Level",
                        "component": "text",
                        "binding": {"path": "/parameters/level", "mode": "write"}
                    },
                    {
                        "key": "message",
                        "label": "Message",
                        "component": "textarea",
                        "binding": {"path": "/parameters/message", "mode": "write"}
                    }
                ]
            },
        },
    ],
    "edges": [
        {"id": "edge-1", "source": {"node": "node-config", "port": "output"}, "target": {"node": "node-transform", "port": "input"}},
        {"id": "edge-2", "source": {"node": "node-transform", "port": "output"}, "target": {"node": "node-delay", "port": "input"}},
        {"id": "edge-3", "source": {"node": "node-delay", "port": "output"}, "target": {"node": "node-notify", "port": "input"}},
        {"id": "edge-4", "source": {"node": "node-notify", "port": "output"}, "target": {"node": "node-audit", "port": "input"}},
    ],
}


def seed_demo_workflow() -> None:
    """Insert the demo workflow if it is missing."""

    with SessionLocal() as session:
        existing = session.get(WorkflowRecord, DEMO_WORKFLOW_ID)
        # Output sorted keys and pretty formatting so JSON is readable and consistent.
        definition = json.dumps(DEMO_WORKFLOW_DEFINITION, ensure_ascii=False, indent=2, sort_keys=True)
        name = DEMO_WORKFLOW_DEFINITION["metadata"]["name"]

        if existing is None:
            record = WorkflowRecord(
                id=DEMO_WORKFLOW_ID,
                name=name,
                definition=definition,
            )
            session.add(record)
            session.commit()
            return

        has_changes = existing.definition != definition or existing.name != name
        if has_changes:
            existing.name = name
            existing.definition = definition
            session.commit()


__all__ = ["seed_demo_workflow", "DEMO_WORKFLOW_ID", "DEMO_WORKFLOW_DEFINITION"]
