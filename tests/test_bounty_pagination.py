# SPDX-License-Identifier: MIT
"""Exercise complete bounty discovery with paginated GitHub responses."""
from __future__ import annotations

import json

import requests

from concierge import bounty_index


def _issue(number: int, *, pull_request: bool = False) -> dict:
    issue = {
        "number": number,
        "title": f"Python task {number}: {number} RTC",
        "body": "",
        "html_url": f"https://github.com/example/project/issues/{number}",
        "labels": [{"name": "bounty"}],
    }
    if pull_request:
        issue["pull_request"] = {"url": "https://api.github.com/pulls/1"}
    return issue


def _response(issues: list[dict], next_page: int | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(issues).encode()
    if next_page:
        response.headers["Link"] = (
            f'<https://api.github.com/repos/example/project/issues?page={next_page}>; rel="next"'
        )
    return response


def test_aggregate_includes_later_pages_and_skips_pull_requests(monkeypatch):
    calls = []
    pages = [
        _response([_issue(n) for n in range(1, 101)], next_page=2),
        _response([_issue(101), _issue(102, pull_request=True)]),
    ]

    def get(url, **kwargs):
        calls.append((url, dict(kwargs["params"])))
        return pages[len(calls) - 1]

    monkeypatch.setattr(bounty_index.requests, "get", get)
    result = bounty_index.aggregate(repos=["example/project"], token="test-token")

    assert result["total_count"] == 101
    assert result["bounties"][0]["number"] == 101
    assert result["bounties"][0]["skills"] == ["python"]
    assert [params.get("page", 1) for _, params in calls] == [1, 2]
    assert all(params["labels"] == "bounty" and params["state"] == "open"
               for _, params in calls)


def test_later_page_failure_keeps_results_and_continues_next_repo(monkeypatch, capsys):
    calls = []

    def get(url, **kwargs):
        calls.append((url, dict(kwargs["params"])))
        if url.endswith("/example/project/issues"):
            if kwargs["params"].get("page", 1) == 1:
                return _response([_issue(1)], next_page=2)
            raise requests.Timeout("second page timed out")
        return _response([_issue(2)])

    monkeypatch.setattr(bounty_index.requests, "get", get)
    result = bounty_index.fetch_bounties(
        repos=["example/project", "example/other"], token="test-token"
    )

    assert [b["number"] for b in result] == [1, 2]
    assert len(calls) == 3
    assert "second page timed out" in capsys.readouterr().err


def test_exact_full_final_page_does_not_request_an_extra_page(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return _response([_issue(n) for n in range(1, 101)])

    monkeypatch.setattr(bounty_index.requests, "get", get)
    assert len(bounty_index.fetch_bounties(["example/project"], "test-token")) == 100
    assert len(calls) == 1
