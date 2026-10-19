"""Command-line interface: import, publish, and admin management.

Usage:
    python -m app.cli init-db
    python -m app.cli import  <pdf> [--year 2025/2026] [--semester 1] [--label "Semester I"]
    python -m app.cli list-issues <version_id>
    python -m app.cli publish <version_id>
    python -m app.cli create-admin <email> [--role owner] [--password ...]
    python -m app.cli create-cr <email> --cohort CODE [--cohort CODE ...] [--name "..."]
"""
from __future__ import annotations

import argparse
import getpass
import sys
import uuid

from app.core.db import SessionLocal, engine, atomic
from app.models import AdminRole, Base, Semester, TimetableVersion, ValidationIssue
from app.services import create_admin, create_cr, import_pdf, publish
from app.services.auth_service import AuthError
from app.services.cr_service import CrError
from app.services.publish_service import PublishError


def _init_db() -> None:
    Base.metadata.create_all(engine)
    print("schema ready")


def _import(args: argparse.Namespace) -> None:
    session = SessionLocal()
    try:
        summary = import_pdf(
            session, args.pdf, year_label=args.year,
            semester=Semester(args.semester), label=args.label,
        )
    finally:
        session.close()
    print(f"version_id : {summary.version_id}")
    print(f"sessions   : {summary.sessions} (with code: {summary.with_code})")
    print(f"issues     : {summary.issues} (errors: {summary.errors}, warnings: {summary.warnings})")


def _list_issues(args: argparse.Namespace) -> None:
    session = SessionLocal()
    try:
        version = session.get(TimetableVersion, uuid.UUID(args.version_id))
        if version is None:
            print("version not found", file=sys.stderr)
            raise SystemExit(1)
        rows = session.query(ValidationIssue).filter_by(version_id=version.id).all()
        for i in rows:
            print(f"[{i.severity.value:7}] p{i.page} {i.code}: {i.message}")
        print(f"total: {len(rows)}")
    finally:
        session.close()


def _publish(args: argparse.Namespace) -> None:
    session = SessionLocal()
    try:
        publish(session, args.version_id)
    except PublishError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        session.close()
    print("published")


def _create_admin(args: argparse.Namespace) -> None:
    password = args.password or getpass.getpass("Password: ")
    session = SessionLocal()
    try:
        with atomic(session):
            user = create_admin(session, args.email, password, AdminRole(args.role))
            info = (str(user.id), user.email, user.role.value)
    except AuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        session.close()
    print(f"created admin: {info[1]} ({info[2]}) id={info[0]}")


def _create_cr(args: argparse.Namespace) -> None:
    password = args.password or getpass.getpass("Password: ")
    session = SessionLocal()
    try:
        with atomic(session):
            user = create_cr(session, email=args.email, password=password,
                             cohort_codes=args.cohort, display_name=args.name)
            info = (str(user.id), user.email, sorted(args.cohort))
    except (AuthError, CrError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        session.close()
    print(f"created class representative: {info[1]} cohorts={','.join(info[2])} id={info[0]}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="timetable")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db").set_defaults(func=lambda args: _init_db())

    imp = sub.add_parser("import")
    imp.add_argument("pdf")
    imp.add_argument("--year", default="2025/2026")
    imp.add_argument("--semester", default="1")
    imp.add_argument("--label", default="Semester I")
    imp.set_defaults(func=_import)

    li = sub.add_parser("list-issues")
    li.add_argument("version_id")
    li.set_defaults(func=_list_issues)

    pub = sub.add_parser("publish")
    pub.add_argument("version_id")
    pub.set_defaults(func=_publish)

    ca = sub.add_parser("create-admin")
    ca.add_argument("email")
    ca.add_argument("--role", default="owner", choices=[r.value for r in AdminRole])
    ca.add_argument("--password", default=None)
    ca.set_defaults(func=_create_admin)

    ccr = sub.add_parser("create-cr")
    ccr.add_argument("email")
    ccr.add_argument("--cohort", action="append", required=True, help="cohort code (repeatable)")
    ccr.add_argument("--name", default=None)
    ccr.add_argument("--password", default=None)
    ccr.set_defaults(func=_create_cr)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
