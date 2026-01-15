from __future__ import annotations

from hub_api.repo.common import _key
from hub_api.repo.orgs import get_org_role, is_user_in_org
from hub_api.repo.packages import get_package_record, list_package_permissions
from hub_api.repo.workflows import get_workflow_record, list_workflow_permissions


def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None
    if role == "reader":
        return "read"
    if role == "maintainer":
        return "write"
    return role


def _role_rank(role: str | None) -> int:
    ranks = {
        "read": 1,
        "reader": 1,
        "write": 2,
        "maintainer": 2,
        "owner": 3,
    }
    return ranks.get(role or "", 0)


def _org_owner_role(org_id: str, user_id: str) -> str | None:
    role = get_org_role(org_id, user_id)
    if role in ("owner", "admin"):
        return "owner"
    return None


def get_package_role_for_user(
    owner_id: str,
    package_name: str,
    user_id: str,
) -> str | None:
    record = get_package_record(owner_id, package_name)
    if record and _key(record.get("ownerId", "")) == _key(user_id):
        return "owner"
    if record and (org_role := _org_owner_role(record.get("ownerId", ""), user_id)):
        return org_role
    best_role = None
    permissions = list_package_permissions(owner_id, package_name)
    for perm in permissions:
        subject_type = perm["subjectType"]
        subject_id = perm["subjectId"]
        if subject_type == "user" and subject_id == user_id:
            candidate = perm["role"]
        elif subject_type == "org" and is_user_in_org(user_id, subject_id):
            candidate = perm["role"]
        else:
            continue
        candidate_role = _normalize_role(candidate)
        if best_role is None or _role_rank(candidate_role) > _role_rank(best_role):
            best_role = candidate_role
    return best_role


def get_workflow_role_for_user(workflow_id: str, user_id: str) -> str | None:
    record = get_workflow_record(workflow_id)
    if record and _key(record.get("ownerId", "")) == _key(user_id):
        return "owner"
    if record and (org_role := _org_owner_role(record.get("ownerId", ""), user_id)):
        return org_role
    best_role = None
    permissions = list_workflow_permissions(workflow_id)
    for perm in permissions:
        subject_type = perm["subjectType"]
        subject_id = perm["subjectId"]
        if subject_type == "user" and subject_id == user_id:
            candidate = perm["role"]
        elif subject_type == "org" and is_user_in_org(user_id, subject_id):
            candidate = perm["role"]
        else:
            continue
        candidate_role = _normalize_role(candidate)
        if best_role is None or _role_rank(candidate_role) > _role_rank(best_role):
            best_role = candidate_role
    return best_role
