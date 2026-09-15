# SPDX-License-Identifier: MIT
"""Global output and preview flags survive subcommand parsing."""
import json
import sys

import pytest

from concierge import cli


@pytest.mark.parametrize("argv", [
    ["--json", "browse"],
    ["browse", "--json"],
])
def test_browse_json_flag_works_before_or_after_command(argv, monkeypatch, capsys):
    bounty = {
        "repo": "example/project", "number": 1, "title": "Python task",
        "reward_rtc": 10, "difficulty": "standard", "skills": ["python"],
    }
    monkeypatch.setattr(cli, "fetch_bounties", lambda **kwargs: [bounty])
    monkeypatch.setattr(sys, "argv", ["concierge", *argv])
    cli.main()
    assert json.loads(capsys.readouterr().out) == [bounty]


@pytest.mark.parametrize("argv", [
    ["--dry-run", "browse"],
    ["browse", "--dry-run"],
])
def test_browse_preview_does_not_fetch_in_either_position(argv, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "fetch_bounties", lambda **kwargs: calls.append(kwargs) or [])
    monkeypatch.setattr(sys, "argv", ["concierge", *argv])
    cli.main()
    assert calls == []
    assert "[dry-run]" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    ["--json", "--dry-run", "wallet", "balance", "example"],
    ["wallet", "--json", "--dry-run", "balance", "example"],
    ["wallet", "balance", "example", "--json", "--dry-run"],
])
def test_nested_parser_preserves_flags_at_each_level(argv):
    args = cli._build_parser().parse_args(argv)
    assert args.json is True
    assert args.dry_run is True


def test_flags_default_to_false_without_leaking_between_parses():
    parser = cli._build_parser()
    parser.parse_args(["--json", "--dry-run", "browse"])
    args = parser.parse_args(["wallet", "balance", "example"])
    assert args.json is False
    assert args.dry_run is False
