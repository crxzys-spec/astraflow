"""Role helpers for enforcing RBAC within API implementations."""

from __future__ import annotations

from fastapi import HTTPException, status

from scheduler_api.auth.context import get_current_token
from scheduler_api.models.extra_models import TokenModel


WORKFLOW_VIEW_ROLES = {"admin", "workflow.viewer", "workflow.editor"}
WORKFLOW_EDIT_ROLES = {"admin", "workflow.editor"}
RUN_VIEW_ROLES = {"admin", "run.viewer"}
AUDIT_VIEW_ROLES = {"admin"}


def require_roles(*required: str) -> TokenModel:
    token = get_current_token()
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Authentication required."},
        )
    if not set(token.roles).intersection(required):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Insufficient role to perform this action."},
        )
    return token
