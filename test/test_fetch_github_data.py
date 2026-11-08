"""Offline regression checks for public-only, complete profile refreshes."""
from __future__ import annotations

from contextlib import redirect_stderr
from datetime import date, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("fetch_github_data", Path(__file__).resolve().parents[1] / "scripts/fetch_github_data.py")
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)
SNAPSHOT = date(2026, 11, 8)


def repository(name="alpha", **overrides):
    data = {
        "name": name, "owner": {"login": "nisconder"}, "private": False,
        "visibility": "public", "description": "A public tool", "html_url": f"https://github.com/nisconder/{name}",
        "stargazers_count": 3, "forks_count": 1, "language": "Python", "fork": False,
        "archived": False, "pushed_at": "2026-11-07T22:00:00Z",
    }
    data.update(overrides)
    return data


def calendar():
    days = [
        {"date": "2026-11-06", "contributionCount": 2, "contributionLevel": "FIRST_QUARTILE"},
        {"date": "2026-11-07", "contributionCount": 0, "contributionLevel": "NONE"},
        {"date": "2026-11-08", "contributionCount": 5, "contributionLevel": "FOURTH_QUARTILE"},
    ]
    return {"totalContributions": 7, "weeks": [{"contributionDays": days}]}


class FixtureAPI:
    def __init__(self, pages=None, contributions=None, fail=False):
        self.calls = []
        self.pages = pages if pages is not None else [[repository()]]
        self.calendar = contributions if contributions is not None else calendar()
        self.fail = fail

    def request(self, endpoint, payload=None):
        self.calls.append((endpoint, payload))
        if endpoint == "users/nisconder":
            return {"login": "nisconder", "name": None, "bio": "  tools\nand notes  ", "html_url": "https://github.com/nisconder", "followers": 5, "following": 4}
        if endpoint.startswith("users/nisconder/repos?"):
            page = int(endpoint.split("&page=")[1].split("&")[0])
            return self.pages[page - 1]
        if endpoint == "graphql":
            if self.fail:
                raise fetch.DataError("Simulated network failure")
            return {"data": {"user": {
                "login": "nisconder",
                "pinnedItems": {"nodes": [
                    {"name": "alpha", "owner": {"login": "nisconder"}, "isPrivate": False},
                    {"name": "secret", "owner": {"login": "nisconder"}, "isPrivate": True},
                    {"name": "alpha", "owner": {"login": "someone-else"}, "isPrivate": False},
                ]},
                "contributionsCollection": {"contributionCalendar": self.calendar},
            }}}
        raise AssertionError(endpoint)


class FetchTests(unittest.TestCase):
    def test_public_owner_scope_and_original_totals_are_explicit(self):
        api = FixtureAPI(pages=[[
            repository("zeta", fork=True, stargazers_count=20, forks_count=9),
            repository("secret", private=True, visibility="private", description="do not publish this"),
            repository("foreign", owner={"login": "someone-else"}),
            repository("alpha", description=None, language=None),
            repository("nisconder", stargazers_count=1, forks_count=0),
        ]])
        profile, contributions = fetch.fetch_snapshots("nisconder", SNAPSHOT, api)
        self.assertEqual([item["name"] for item in profile["repositories"]], ["alpha", "nisconder", "zeta"])
        self.assertEqual(profile["stats"], {"publicRepositories": 3, "originalRepositories": 2, "totalStars": 24, "originalStars": 4, "totalForks": 10, "originalForks": 1})
        self.assertEqual(profile["pinnedRepositories"], ["alpha"])
        self.assertEqual(profile["user"]["name"], "nisconder")
        self.assertEqual(profile["user"]["bio"], "tools and notes")
        self.assertEqual(profile["repositories"][0]["description"], "")
        self.assertIsNone(profile["repositories"][0]["language"])
        self.assertNotIn("secret", json.dumps(profile))
        self.assertEqual(contributions["totalContributions"], 7)
        self.assertEqual(contributions["periodEnd"], "2026-11-08")
        self.assertNotIn("repository", json.dumps(contributions))

    def test_profile_push_time_does_not_create_bot_commit_churn(self):
        rows = [repository("nisconder"), repository("alpha")]
        first = fetch.normalize_repositories(rows, "nisconder")
        rows[0]["pushed_at"] = "2026-11-08T03:00:00Z"
        self.assertEqual(first, fetch.normalize_repositories(rows, "nisconder"))
        self.assertEqual(first[0]["pushedAt"], "2026-11-07T22:00:00Z")
        self.assertIsNone(first[1]["pushedAt"])

    def test_pagination_and_fixed_date_query_collect_all_repository_pages(self):
        page_one = [repository(f"repo-{number:03}") for number in range(100)]
        api = FixtureAPI(pages=[page_one, [repository("alpha")]])
        profile, _ = fetch.fetch_snapshots("nisconder", SNAPSHOT, api)
        self.assertEqual(len(profile["repositories"]), 101)
        self.assertEqual(len([endpoint for endpoint, _ in api.calls if "/repos?" in endpoint]), 2)
        _, payload = api.calls[-1]
        self.assertEqual(payload["variables"], {"login": "nisconder", "from": "2025-11-09T00:00:00Z", "to": "2026-11-08T23:59:59Z"})

    def test_invalid_calendar_counts_and_dates_are_rejected(self):
        cases = []
        wrong_total = calendar(); wrong_total["totalContributions"] = 8; cases.append(wrong_total)
        duplicate = calendar(); duplicate["weeks"][0]["contributionDays"][1]["date"] = "2026-11-06"; cases.append(duplicate)
        gap = calendar(); gap["weeks"][0]["contributionDays"].pop(1); gap["totalContributions"] = 7; cases.append(gap)
        negative = calendar(); negative["weeks"][0]["contributionDays"][0]["contributionCount"] = -1; cases.append(negative)
        unknown = calendar(); unknown["weeks"][0]["contributionDays"][0]["contributionLevel"] = "NOT_A_LEVEL"; cases.append(unknown)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(fetch.DataError):
                fetch.normalize_calendar(data, SNAPSHOT)

    def test_network_or_validation_failure_keeps_both_existing_files(self):
        invalid = calendar(); invalid["totalContributions"] = 999
        for api in [FixtureAPI(fail=True), FixtureAPI(contributions=invalid)]:
            with self.subTest(api=api), tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
                root = Path(directory)
                for filename in ["github-profile.json", "contributions.json"]:
                    (root / filename).write_text("original " + filename, encoding="utf-8")
                original = {item.name: item.read_bytes() for item in root.iterdir()}
                with patch.object(fetch, "GitHubCLI", return_value=api), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    fetch.main(["--date", SNAPSHOT.isoformat(), "--output-dir", directory])
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual({item.name: item.read_bytes() for item in root.iterdir()}, original)

    def test_snapshot_writes_are_stable_and_unchanged_data_is_not_replaced(self):
        profile, contributions = fetch.fetch_snapshots("nisconder", SNAPSHOT, FixtureAPI())
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            fetch.write_snapshots(root, profile, contributions)
            original = {item.name: item.read_bytes() for item in root.iterdir()}
            with patch.object(fetch.os, "replace", wraps=fetch.os.replace) as replace:
                fetch.write_snapshots(root, profile, contributions)
                replace.assert_not_called()
            self.assertEqual({item.name: item.read_bytes() for item in root.iterdir()}, original)
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_default_snapshot_date_uses_shanghai_after_utc_day_boundary(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 7, 17, 15, tzinfo=timezone.utc).astimezone(tz)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, patch.object(fetch, "datetime", FixedDateTime), patch.object(fetch, "GitHubCLI", return_value=FixtureAPI()), patch("builtins.print"):
            self.assertEqual(fetch.main(["--output-dir", directory]), 0)
            self.assertEqual(json.loads((Path(directory) / "github-profile.json").read_text(encoding="utf-8"))["snapshotDate"], "2026-11-08")

    def test_cli_failures_never_echo_debug_credentials_and_graphql_errors_fail(self):
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="Authorization: secret-do-not-print")
        with patch.object(fetch.subprocess, "run", return_value=failed), self.assertRaises(fetch.DataError) as raised:
            fetch.GitHubCLI().request("users/nisconder")
        self.assertNotIn("secret-do-not-print", str(raised.exception))
        errors = subprocess.CompletedProcess([], 0, stdout=json.dumps({"data": {"user": None}, "errors": [{"message": "not available"}]}), stderr="")
        with patch.object(fetch.subprocess, "run", return_value=errors), self.assertRaises(fetch.DataError):
            fetch.GitHubCLI().request("graphql", {"query": "example"})

    def test_bad_repository_counts_and_duplicate_names_do_not_generate_data(self):
        for rows in [[repository(stargazers_count=-1)], [repository(stargazers_count=True)], [repository(), repository()]]:
            with self.subTest(rows=rows), self.assertRaises(fetch.DataError):
                fetch.normalize_repositories(rows, "nisconder")


if __name__ == "__main__":
    unittest.main()
