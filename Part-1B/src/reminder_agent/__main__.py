"""Command line: python -m reminder_agent "MESSAGE" [--now YYYY-MM-DDTHH:MM]."""

import argparse
import json
import sys
from datetime import datetime

from reminder_agent import schema
from reminder_agent.agent import ReminderAgent
from reminder_agent.llm import GeminiClient, ServiceError


def _fail(category: str, message: str, code: int) -> int:
    print(json.dumps({"error": {"category": category, "message": message}}), file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    """Run the agent on one message and print the result as one line of JSON."""
    parser = argparse.ArgumentParser(prog="reminder_agent")
    parser.add_argument("message")
    parser.add_argument("--now", help="reference moment, YYYY-MM-DDTHH:MM (default: now)")
    args = parser.parse_args(argv)
    try:
        now = (
            datetime.strptime(args.now, schema.DATETIME_FORMAT)
            if args.now
            else datetime.now().replace(second=0, microsecond=0)
        )
    except ValueError:
        return _fail("usage", "--now must look like 2026-11-16T09:00", 2)
    try:
        client = GeminiClient.from_config()
    except ServiceError as error:
        return _fail("usage", str(error), 2)
    try:
        outcome = ReminderAgent(client).parse(args.message, now)
    except ServiceError as error:
        return _fail("service", str(error), 3)
    print(json.dumps(outcome.result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
