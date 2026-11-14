"""Command-line interface: arguments in, one line of JSON out (FR-015, FR-017)."""

import argparse
import json
import os
import sys
from pathlib import Path

from todo.errors import TodoError, ValidationError
from todo.models import validate_id
from todo.service import TaskService

DEFAULT_FILE = "tasks.json"


class _Parser(argparse.ArgumentParser):
    """Argument parser that reports usage mistakes as validation errors."""

    def error(self, message: str) -> None:
        raise ValidationError(message)


def build_parser() -> argparse.ArgumentParser:
    """Build the parser for the six commands in the CLI contract."""
    parser = _Parser(prog="todo", description="Smart Todo & Task CLI")
    parser.add_argument("--file", help="path of the data file")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="create a task")
    add.add_argument("title")
    add.add_argument("--priority")
    add.add_argument("--tag", action="append", default=[])

    show = commands.add_parser("show", help="show one task")
    show.add_argument("id")

    listing = commands.add_parser("list", help="list tasks")
    listing.add_argument("--tag", action="append", default=[])
    listing.add_argument("--status")
    listing.add_argument("--sort", default="id")

    update = commands.add_parser("update", help="change a task")
    update.add_argument("id")
    update.add_argument("--title")
    update.add_argument("--priority")
    update.add_argument("--tag", action="append")
    update.add_argument("--clear-tags", action="store_true")

    move = commands.add_parser("move", help="change the status of a task")
    move.add_argument("id")
    move.add_argument("status")

    delete = commands.add_parser("delete", help="delete a task")
    delete.add_argument("id")
    return parser


def _update(service: TaskService, args: argparse.Namespace) -> dict:
    if args.tag and args.clear_tags:
        raise ValidationError("use either --tag or --clear-tags, not both")
    tags = [] if args.clear_tags else args.tag
    if args.title is None and args.priority is None and tags is None:
        raise ValidationError("nothing to update")
    task = service.update_task(validate_id(args.id), args.title, args.priority, tags)
    return task.to_dict()


def _dispatch(service: TaskService, args: argparse.Namespace) -> dict | list:
    if args.command == "add":
        return service.create_task(args.title, args.priority, args.tag).to_dict()
    if args.command == "show":
        return service.get_task(validate_id(args.id)).to_dict()
    if args.command == "list":
        tasks = service.list_tasks(args.tag, args.status, args.sort)
        return [task.to_dict() for task in tasks]
    if args.command == "update":
        return _update(service, args)
    if args.command == "move":
        return service.move_task(validate_id(args.id), args.status).to_dict()
    return {"deleted": service.delete_task(validate_id(args.id))}


def main(argv: list[str] | None = None) -> int:
    """Run one command and return its exit code."""
    try:
        args = build_parser().parse_args(argv)
        path = Path(args.file or os.environ.get("TODO_FILE") or DEFAULT_FILE)
        result = _dispatch(TaskService(path), args)
    except TodoError as error:
        payload = {"error": {"category": error.category, "message": str(error)}}
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return error.exit_code
    print(json.dumps(result, sort_keys=True))
    return 0
