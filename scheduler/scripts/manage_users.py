"""Utility script to manage scheduler users and roles."""

from __future__ import annotations

import argparse
import getpass
import sys

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from scheduler_api.auth.service import hash_password
from scheduler_api.db.models import RoleRecord, UserRecord, UserRoleRecord
from scheduler_api.db.session import SessionLocal


def _get_user(session, username: str) -> UserRecord | None:
    return session.query(UserRecord).filter(UserRecord.username == username).one_or_none()


def _get_role(session, role_name: str) -> RoleRecord | None:
    return session.query(RoleRecord).filter(RoleRecord.name == role_name).one_or_none()


def create_user(args: argparse.Namespace) -> None:
    password = args.password or getpass.getpass("Password: ")
    with SessionLocal() as session:
        if _get_user(session, args.username):
            print(f"User '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)
        user = UserRecord(
            username=args.username,
            display_name=args.display_name or args.username,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.commit()
        print(f"Created user '{args.username}' with id {user.id}")


def set_password(args: argparse.Namespace) -> None:
    password = args.password or getpass.getpass("New password: ")
    with SessionLocal() as session:
        user = _get_user(session, args.username)
        if not user:
            print(f"User '{args.username}' not found.", file=sys.stderr)
            sys.exit(1)
        user.password_hash = hash_password(password)
        session.commit()
        print(f"Password updated for '{args.username}'")


def add_role(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        user = _get_user(session, args.username)
        if not user:
            print(f"User '{args.username}' not found.", file=sys.stderr)
            sys.exit(1)
        role = _get_role(session, args.role)
        if not role:
            print(f"Role '{args.role}' not found.", file=sys.stderr)
            sys.exit(1)
        exists = (
            session.query(UserRoleRecord)
            .filter(UserRoleRecord.user_id == user.id, UserRoleRecord.role_id == role.id)
            .one_or_none()
        )
        if exists:
            print(f"User '{args.username}' already has role '{args.role}'.")
            return
        session.add(UserRoleRecord(user_id=user.id, role_id=role.id))
        session.commit()
        print(f"Added role '{args.role}' to '{args.username}'")


def remove_role(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        user = _get_user(session, args.username)
        if not user:
            print(f"User '{args.username}' not found.", file=sys.stderr)
            sys.exit(1)
        role = _get_role(session, args.role)
        if not role:
            print(f"Role '{args.role}' not found.", file=sys.stderr)
            sys.exit(1)
        record = (
            session.query(UserRoleRecord)
            .filter(UserRoleRecord.user_id == user.id, UserRoleRecord.role_id == role.id)
            .one_or_none()
        )
        if not record:
            print(f"User '{args.username}' does not have role '{args.role}'.")
            return
        session.delete(record)
        session.commit()
        print(f"Removed role '{args.role}' from '{args.username}'")


def _set_status(username: str, active: bool) -> None:
    with SessionLocal() as session:
        user = _get_user(session, username)
        if not user:
            print(f"User '{username}' not found.", file=sys.stderr)
            sys.exit(1)
        user.is_active = active
        session.commit()
        state = "activated" if active else "deactivated"
        print(f"User '{username}' {state}.")


def activate_user(args: argparse.Namespace) -> None:
    _set_status(args.username, True)


def deactivate_user(args: argparse.Namespace) -> None:
    _set_status(args.username, False)


def list_users(_: argparse.Namespace) -> None:
    with SessionLocal() as session:
        users = session.query(UserRecord).order_by(UserRecord.username).all()
        for user in users:
            roles = (
                session.query(RoleRecord.name)
                .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
                .filter(UserRoleRecord.user_id == user.id)
                .order_by(RoleRecord.name)
                .all()
            )
            role_list = ", ".join(name for (name,) in roles)
            print(f"{user.username} ({user.display_name}) [{ 'inactive' if not user.is_active else 'active' }] -> {role_list}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage scheduler users and roles")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="Create a new user")
    create.add_argument("username")
    create.add_argument("--display-name")
    create.add_argument("--password")
    create.set_defaults(func=create_user)

    passwd = sub.add_parser("set-password", help="Update a user's password")
    passwd.add_argument("username")
    passwd.add_argument("--password")
    passwd.set_defaults(func=set_password)

    add = sub.add_parser("add-role", help="Assign a role to a user")
    add.add_argument("username")
    add.add_argument("role")
    add.set_defaults(func=add_role)

    remove = sub.add_parser("remove-role", help="Remove a role from a user")
    remove.add_argument("username")
    remove.add_argument("role")
    remove.set_defaults(func=remove_role)

    activate = sub.add_parser("activate", help="Enable a user account")
    activate.add_argument("username")
    activate.set_defaults(func=activate_user)

    deactivate = sub.add_parser("deactivate", help="Disable a user account")
    deactivate.add_argument("username")
    deactivate.set_defaults(func=deactivate_user)

    list_cmd = sub.add_parser("list-users", help="List users and their roles")
    list_cmd.set_defaults(func=list_users)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
