from __future__ import annotations

from hub_api.repo.common import _key
from hub_api.repo.orgs import is_user_in_org
from hub_api.repo.packages import get_package_record, list_package_permissions
from hub_api.repo.teams import is_user_in_team


def get_package_role_for_user(package_name: str, user_id: str) -> str | None:
    role_rank = {"reader": 1, "maintainer": 2, "owner": 3}
    record = get_package_record(package_name)
    if record and _key(record.get("ownerId", "")) == _key(user_id):
        return "owner"
    best_role = None
    permissions = list_package_permissions(package_name)
    for perm in permissions:
        subject_type = perm["subjectType"]
        subject_id = perm["subjectId"]
        if subject_type == "user" and subject_id == user_id:
            candidate = perm["role"]
        elif subject_type == "org" and is_user_in_org(user_id, subject_id):
            candidate = perm["role"]
        elif subject_type == "team" and is_user_in_team(user_id, subject_id):
            candidate = perm["role"]
        else:
            continue
        if best_role is None or role_rank.get(candidate, 0) > role_rank.get(best_role, 0):
            best_role = candidate
    return best_role
