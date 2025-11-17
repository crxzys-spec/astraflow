"""Database seed helpers for development use."""

from __future__ import annotations

import json
from typing import Any, Dict

from scheduler_api.db.models import WorkflowRecord
from scheduler_api.db.session import SessionLocal


DEMO_WORKFLOW_ID = "wf-demo"

WELCOME_CONFIG_DEFAULT = '{\n  "recipient": {\n    "name": "Leslie Knope",\n    "email": "leslie@example.com"\n  },\n  "channel": "email",\n  "subject": "Welcome to AstraFlow",\n  "template": "Hello {{name}}, thank you for joining AstraFlow!",\n  "delaySeconds": 1.5,\n  "tokenDelayMs": 60\n}'

RAW_DEMO_WORKFLOW_JSON = r"""{
  "id": "wf-demo",
  "schemaVersion": "2025-10",
  "metadata": {
    "name": "Customer Welcome Journey",
    "description": "Streams a personalised welcome message, schedules delivery, and records the notification lifecycle.",
    "namespace": "default",
    "originId": "wf-demo"
  },
  "nodes": [
    {
      "id": "node-config",
      "type": "example.pkg.load_config",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "load_config",
      "status": "published",
      "category": "Examples",
      "label": "Load Welcome Config",
      "position": {
        "x": -900,
        "y": 0
      },
      "parameters": {
        "config": "{\n  \"recipient\": {\n    \"name\": \"Leslie Knope\",\n    \"email\": \"leslie@example.com\"\n  },\n  \"channel\": \"email\",\n  \"subject\": \"Welcome to AstraFlow\",\n  \"template\": \"Hello {{name}}, thank you for joining AstraFlow!\",\n  \"delaySeconds\": 1.5,\n  \"tokenDelayMs\": 60\n}"
      },
      "ui": {
        "outputPorts": [
          {
            "key": "config",
            "label": "Config",
            "binding": {
              "path": "/results/config",
              "mode": "read"
            }
          },
          {
            "key": "message",
            "label": "Welcome Message",
            "binding": {
              "path": "/results/config/message",
              "mode": "read"
            }
          },
          {
            "key": "recipient",
            "label": "Recipient",
            "binding": {
              "path": "/results/config/recipient",
              "mode": "read"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "binding": {
              "path": "/results/config/channel",
              "mode": "read"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "binding": {
              "path": "/results/config/subject",
              "mode": "read"
            }
          },
          {
            "key": "delaySeconds",
            "label": "Delay (s)",
            "binding": {
              "path": "/results/config/delaySeconds",
              "mode": "read"
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "binding": {
              "path": "/results/config/tokenDelayMs",
              "mode": "read"
            }
          }
        ],
        "widgets": [
          {
            "key": "config",
            "label": "Configuration JSON",
            "component": "json",
            "binding": {
              "path": "/parameters/config",
              "mode": "write"
            }
          },
          {
            "key": "messagePreview",
            "label": "Preview Message",
            "component": "textarea",
            "binding": {
              "path": "/results/config/message",
              "mode": "read"
            },
            "options": {
              "rows": 3
            }
          }
        ]
      }
    },
    {
      "id": "node-transform",
      "type": "example.pkg.transform_text",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "transform_text",
      "status": "published",
      "category": "Examples",
      "label": "Personalise Message",
      "position": {
        "x": -450,
        "y": 0
      },
      "parameters": {
        "text": "",
        "mode": "title",
        "recipient": {},
        "channel": "email",
        "subject": "Welcome to AstraFlow",
        "delaySeconds": 1.5,
        "tokenDelayMs": 60
      },
      "ui": {
        "inputPorts": [
          {
            "key": "input",
            "label": "Message",
            "binding": {
              "path": "/parameters/text",
              "mode": "write"
            }
          },
          {
            "key": "recipient",
            "label": "Recipient",
            "binding": {
              "path": "/parameters/recipient",
              "mode": "write"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "binding": {
              "path": "/parameters/channel",
              "mode": "write"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "binding": {
              "path": "/parameters/subject",
              "mode": "write"
            }
          },
          {
            "key": "delaySeconds",
            "label": "Delay (s)",
            "binding": {
              "path": "/parameters/delaySeconds",
              "mode": "write"
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "binding": {
              "path": "/parameters/tokenDelayMs",
              "mode": "write"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "message",
            "label": "Message",
            "binding": {
              "path": "/results/message",
              "mode": "read"
            }
          },
          {
            "key": "recipient",
            "label": "Recipient",
            "binding": {
              "path": "/results/recipient",
              "mode": "read"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "binding": {
              "path": "/results/channel",
              "mode": "read"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "binding": {
              "path": "/results/subject",
              "mode": "read"
            }
          },
          {
            "key": "delaySeconds",
            "label": "Delay (s)",
            "binding": {
              "path": "/results/delaySeconds",
              "mode": "read"
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "binding": {
              "path": "/results/tokenDelayMs",
              "mode": "read"
            }
          }
        ],
        "widgets": [
          {
            "key": "text",
            "label": "Message",
            "component": "textarea",
            "binding": {
              "path": "/parameters/text",
              "mode": "write"
            },
            "options": {
              "rows": 3
            }
          },
          {
            "key": "mode",
            "label": "Mode",
            "component": "text",
            "binding": {
              "path": "/parameters/mode",
              "mode": "write"
            }
          },
          {
            "key": "recipient",
            "label": "Recipient",
            "component": "json",
            "binding": {
              "path": "/parameters/recipient",
              "mode": "write"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "component": "text",
            "binding": {
              "path": "/parameters/channel",
              "mode": "write"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "component": "text",
            "binding": {
              "path": "/parameters/subject",
              "mode": "write"
            }
          },
          {
            "key": "delaySeconds",
            "label": "Delay (s)",
            "component": "number",
            "binding": {
              "path": "/parameters/delaySeconds",
              "mode": "write"
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "component": "number",
            "binding": {
              "path": "/parameters/tokenDelayMs",
              "mode": "write"
            }
          },
          {
            "key": "messagePreview",
            "label": "Formatted Message",
            "component": "textarea",
            "binding": {
              "path": "/results/message",
              "mode": "read"
            },
            "options": {
              "rows": 3
            }
          }
        ]
      }
    },
    {
      "id": "node-feedback",
      "type": "example.pkg.feedback_demo",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "feedback_showcase",
      "status": "published",
      "category": "Examples",
      "label": "Stream Feedback",
      "position": {
        "x": 0,
        "y": 0
      },
      "parameters": {
        "prompt": "",
        "tokenDelayMs": 60
      },
      "ui": {
        "inputPorts": [
          {
            "key": "prompt",
            "label": "Prompt",
            "binding": {
              "path": "/parameters/prompt",
              "mode": "write"
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "binding": {
              "path": "/parameters/tokenDelayMs",
              "mode": "write"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "summary",
            "label": "Summary",
            "binding": {
              "path": "/results/summary",
              "mode": "read"
            }
          }
        ],
        "widgets": [
          {
            "key": "prompt",
            "label": "Prompt",
            "component": "textarea",
            "binding": {
              "path": "/parameters/prompt",
              "mode": "write"
            },
            "options": {
              "rows": 3
            }
          },
          {
            "key": "tokenDelayMs",
            "label": "Token Delay (ms)",
            "component": "number",
            "binding": {
              "path": "/parameters/tokenDelayMs",
              "mode": "write"
            }
          },
          {
            "key": "summaryPreview",
            "label": "Streamed Summary",
            "component": "textarea",
            "binding": {
              "path": "/results/summary",
              "mode": "read"
            },
            "options": {
              "rows": 4
            }
          }
        ]
      }
    },
    {
      "id": "node-delay",
      "type": "example.pkg.delay",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "delay",
      "status": "published",
      "category": "Examples",
      "label": "Schedule Delivery",
      "position": {
        "x": 0,
        "y": 550
      },
      "parameters": {
        "durationSeconds": 1.5
      },
      "ui": {
        "inputPorts": [
          {
            "key": "input",
            "label": "Delay",
            "binding": {
              "path": "/parameters/durationSeconds",
              "mode": "write"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "output",
            "label": "Done",
            "binding": {
              "path": "/results/durationSeconds",
              "mode": "read"
            }
          }
        ],
        "widgets": [
          {
            "key": "durationSeconds",
            "label": "Delay (seconds)",
            "component": "number",
            "binding": {
              "path": "/parameters/durationSeconds",
              "mode": "write"
            }
          },
          {
            "key": "actualDuration",
            "label": "Actual Duration",
            "component": "number",
            "binding": {
              "path": "/results/durationSeconds",
              "mode": "read"
            }
          }
        ]
      }
    },
    {
      "id": "node-notify",
      "type": "example.pkg.send_notification",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "send_notification",
      "status": "published",
      "category": "Examples",
      "label": "Send Welcome Notification",
      "position": {
        "x": 450,
        "y": 0
      },
      "parameters": {
        "recipient": {},
        "channel": "email",
        "subject": "Welcome to AstraFlow",
        "message": "",
        "ready": null
      },
      "ui": {
        "inputPorts": [
          {
            "key": "message",
            "label": "Message",
            "binding": {
              "path": "/parameters/message",
              "mode": "write"
            }
          },
          {
            "key": "recipient",
            "label": "Recipient",
            "binding": {
              "path": "/parameters/recipient",
              "mode": "write"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "binding": {
              "path": "/parameters/channel",
              "mode": "write"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "binding": {
              "path": "/parameters/subject",
              "mode": "write"
            }
          },
          {
            "key": "handoff",
            "label": "Ready",
            "binding": {
              "path": "/parameters/ready",
              "mode": "write"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "notificationId",
            "label": "Notification",
            "binding": {
              "path": "/results/notificationId",
              "mode": "read"
            }
          },
          {
            "key": "summary",
            "label": "Summary",
            "binding": {
              "path": "/results/summary",
              "mode": "read"
            }
          }
        ],
        "widgets": [
          {
            "key": "recipient",
            "label": "Recipient",
            "component": "json",
            "binding": {
              "path": "/parameters/recipient",
              "mode": "write"
            }
          },
          {
            "key": "channel",
            "label": "Channel",
            "component": "text",
            "binding": {
              "path": "/parameters/channel",
              "mode": "write"
            }
          },
          {
            "key": "subject",
            "label": "Subject",
            "component": "text",
            "binding": {
              "path": "/parameters/subject",
              "mode": "write"
            }
          },
          {
            "key": "message",
            "label": "Message",
            "component": "textarea",
            "binding": {
              "path": "/parameters/message",
              "mode": "write"
            },
            "options": {
              "rows": 3
            }
          },
          {
            "key": "summaryPreview",
            "label": "Notification Summary",
            "component": "textarea",
            "binding": {
              "path": "/results/summary",
              "mode": "read"
            },
            "options": {
              "rows": 3
            }
          },
          {
            "key": "notificationId",
            "label": "Notification ID",
            "component": "text",
            "binding": {
              "path": "/results/notificationId",
              "mode": "read"
            }
          }
        ]
      }
    },
    {
      "id": "node-audit",
      "type": "example.pkg.audit_log",
      "package": {
        "name": "example.pkg",
        "version": "1.0.0"
      },
      "adapter": "demo",
      "handler": "audit_log",
      "status": "published",
      "category": "Examples",
      "label": "Audit Delivery",
      "position": {
        "x": 900,
        "y": 0
      },
      "parameters": {
        "level": "info",
        "message": "",
        "notificationId": ""
      },
      "ui": {
        "inputPorts": [
          {
            "key": "input",
            "label": "Summary",
            "binding": {
              "path": "/parameters/message",
              "mode": "write"
            }
          },
          {
            "key": "notificationId",
            "label": "Notification",
            "binding": {
              "path": "/parameters/notificationId",
              "mode": "write"
            }
          }
        ],
        "widgets": [
          {
            "key": "level",
            "label": "Level",
            "component": "text",
            "binding": {
              "path": "/parameters/level",
              "mode": "write"
            }
          },
          {
            "key": "message",
            "label": "Summary",
            "component": "textarea",
            "binding": {
              "path": "/parameters/message",
              "mode": "write"
            },
            "options": {
              "rows": 3
            }
          },
          {
            "key": "entryPreview",
            "label": "Audit Entry",
            "component": "json",
            "binding": {
              "path": "/results/entry",
              "mode": "read"
            }
          }
        ],
        "outputPorts": [
          {
            "key": "entry",
            "label": "Entry",
            "binding": {
              "path": "/results/entry",
              "mode": "read"
            }
          }
        ]
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": {
        "node": "node-config",
        "port": "message"
      },
      "target": {
        "node": "node-transform",
        "port": "input"
      }
    },
    {
      "id": "edge-2",
      "source": {
        "node": "node-config",
        "port": "recipient"
      },
      "target": {
        "node": "node-transform",
        "port": "recipient"
      }
    },
    {
      "id": "edge-3",
      "source": {
        "node": "node-config",
        "port": "channel"
      },
      "target": {
        "node": "node-transform",
        "port": "channel"
      }
    },
    {
      "id": "edge-4",
      "source": {
        "node": "node-config",
        "port": "subject"
      },
      "target": {
        "node": "node-transform",
        "port": "subject"
      }
    },
    {
      "id": "edge-5",
      "source": {
        "node": "node-config",
        "port": "tokenDelayMs"
      },
      "target": {
        "node": "node-transform",
        "port": "tokenDelayMs"
      }
    },
    {
      "id": "edge-6",
      "source": {
        "node": "node-config",
        "port": "delaySeconds"
      },
      "target": {
        "node": "node-transform",
        "port": "delaySeconds"
      }
    },
    {
      "id": "edge-7",
      "source": {
        "node": "node-transform",
        "port": "message"
      },
      "target": {
        "node": "node-feedback",
        "port": "prompt"
      }
    },
    {
      "id": "edge-8",
      "source": {
        "node": "node-transform",
        "port": "tokenDelayMs"
      },
      "target": {
        "node": "node-feedback",
        "port": "tokenDelayMs"
      }
    },
    {
      "id": "edge-9",
      "source": {
        "node": "node-transform",
        "port": "delaySeconds"
      },
      "target": {
        "node": "node-delay",
        "port": "input"
      }
    },
    {
      "id": "edge-10",
      "source": {
        "node": "node-transform",
        "port": "message"
      },
      "target": {
        "node": "node-notify",
        "port": "message"
      }
    },
    {
      "id": "edge-11",
      "source": {
        "node": "node-transform",
        "port": "recipient"
      },
      "target": {
        "node": "node-notify",
        "port": "recipient"
      }
    },
    {
      "id": "edge-12",
      "source": {
        "node": "node-transform",
        "port": "channel"
      },
      "target": {
        "node": "node-notify",
        "port": "channel"
      }
    },
    {
      "id": "edge-13",
      "source": {
        "node": "node-transform",
        "port": "subject"
      },
      "target": {
        "node": "node-notify",
        "port": "subject"
      }
    },
    {
      "id": "edge-14",
      "source": {
        "node": "node-delay",
        "port": "output"
      },
      "target": {
        "node": "node-notify",
        "port": "handoff"
      }
    },
    {
      "id": "edge-15",
      "source": {
        "node": "node-notify",
        "port": "summary"
      },
      "target": {
        "node": "node-audit",
        "port": "input"
      }
    },
    {
      "id": "edge-16",
      "source": {
        "node": "node-notify",
        "port": "notificationId"
      },
      "target": {
        "node": "node-audit",
        "port": "notificationId"
      }
    }
  ]
}"""

DEMO_WORKFLOW_DEFINITION: Dict[str, Any] = json.loads(RAW_DEMO_WORKFLOW_JSON)
DEMO_WORKFLOW_DEFINITION["id"] = DEMO_WORKFLOW_ID


def seed_demo_workflow() -> None:
    """Insert the demo workflow if it is missing."""

    with SessionLocal() as session:
        existing = session.get(WorkflowRecord, DEMO_WORKFLOW_ID)
        metadata = DEMO_WORKFLOW_DEFINITION["metadata"]
        structure = {
            key: value
            for key, value in DEMO_WORKFLOW_DEFINITION.items()
            if key not in {"id", "schemaVersion", "metadata"}
        }
        definition = json.dumps(structure, ensure_ascii=False, indent=2, sort_keys=True)
        name = metadata["name"]
        schema_version = DEMO_WORKFLOW_DEFINITION["schemaVersion"]
        namespace = metadata.get("namespace") or "default"
        origin_id = metadata.get("originId") or DEMO_WORKFLOW_ID
        description = metadata.get("description")

        if existing is None:
            record = WorkflowRecord(
                id=DEMO_WORKFLOW_ID,
                name=name,
                definition=definition,
                schema_version=schema_version,
                namespace=namespace,
                origin_id=origin_id,
                description=description,
                environment=metadata.get("environment"),
                tags=json.dumps(metadata.get("tags")) if metadata.get("tags") else None,
            )
            session.add(record)
            session.commit()
            return

        has_changes = (
            existing.definition != definition
            or existing.name != name
            or existing.schema_version != schema_version
            or existing.namespace != namespace
            or existing.origin_id != origin_id
        )
        if has_changes:
            existing.name = name
            existing.definition = definition
            existing.schema_version = schema_version
            existing.namespace = namespace
            existing.origin_id = origin_id
            existing.description = description
            existing.environment = metadata.get("environment")
            existing.tags = json.dumps(metadata.get("tags")) if metadata.get("tags") else None
        session.commit()


__all__ = ["seed_demo_workflow", "DEMO_WORKFLOW_ID", "DEMO_WORKFLOW_DEFINITION"]
