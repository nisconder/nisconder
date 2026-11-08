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
from urllib.parse import parse_qs, urlparse

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


def external_repository(owner="upstream", name="tool", **overrides):
    value = repository(name, owner={"login": owner}, full_name=f"{owner}/{name}", html_url=f"https://github.com/{owner}/{name}", stargazers_count=1000, forks_count=100)
    value.update(overrides)
    return value


def search_item(full_name="upstream/tool", number=1):
    return {"number": number, "pull_request": {"url": f"https://api.github.com/repos/{full_name}/pulls/{number}"}}


def pull_request(full_name="upstream/tool", number=1, **overrides):
    owner, name = full_name.split("/")
    value = {
        "number": number, "merged": True, "merged_at": "2026-11-07T22:00:00Z",
        "user": {"login": "nisconder"}, "title": "A verified contribution",
        "html_url": f"https://github.com/{full_name}/pull/{number}",
        "base": {"repo": {"full_name": full_name, "name": name, "owner": {"login": owner}, "private": False, "visibility": "public"}},
    }
    value.update(overrides)
    return value


def search_results(items=None, **overrides):
    items = items if items is not None else []
    result = {"total_count": len(items), "incomplete_results": False, "items": items}
    result.update(overrides)
    return result


class FixtureAPI:
    def __init__(self, pages=None, contributions=None, fail=False, search_pages=None, external=None):
        self.calls = []
        self.pages = pages if pages is not None else [[repository()]]
        self.calendar = contributions if contributions is not None else calendar()
        self.fail = fail
        self.search_pages = search_pages if search_pages is not None else [search_results()]
        self.external = external or {}

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
        if endpoint.startswith("search/issues?"):
            page = int(parse_qs(urlparse(endpoint).query)["page"][0])
            return self.search_pages[page - 1]
        if endpoint in self.external:
            value = self.external[endpoint]
            if isinstance(value, Exception):
                raise value
            return value
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
        _, payload = next(call for call in api.calls if call[0] == "graphql")
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

    def test_external_project_requires_verified_merged_pr_and_does_not_inflate_owned_stars(self):
        api = FixtureAPI(
            search_pages=[search_results([search_item()])],
            external={"repos/upstream/tool": external_repository(), "repos/upstream/tool/pulls/1": pull_request()},
        )
        profile, _ = fetch.fetch_snapshots("nisconder", SNAPSHOT, api)
        self.assertEqual(profile["stats"]["originalStars"], 3)
        self.assertEqual(profile["stats"]["originalForks"], 1)
        self.assertEqual(profile["stats"]["publicRepositories"], 1)
        project, = profile["contributedRepositories"]
        self.assertEqual(project["fullName"], "upstream/tool")
        self.assertEqual(project["owner"], "upstream")
        self.assertEqual(project["relationship"], "contributor")
        self.assertFalse(project["isProfile"])
        self.assertEqual(project["stars"], 1000)
        self.assertEqual(project["contribution"]["mergedPullRequests"], 1)
        self.assertEqual(project["contribution"]["countScope"], "verified search sample")
        self.assertEqual(project["contribution"]["pullRequests"][0]["url"], "https://github.com/upstream/tool/pull/1")
        self.assertEqual(profile["contributionSearch"]["checkedPullRequests"], 1)
        self.assertFalse(profile["contributionSearch"]["truncated"])
        self.assertIn("is:public", profile["contributionSearch"]["query"])

    def test_search_candidates_with_wrong_author_unmerged_or_private_target_are_not_contributions(self):
        bad_pulls = [
            pull_request(merged=False, merged_at=None),
            pull_request(user={"login": "app/copilot-swe-agent"}),
            pull_request(user=None),
            pull_request(base={"repo": {"full_name": "elsewhere/tool", "name": "tool", "owner": {"login": "elsewhere"}, "private": False}}),
            pull_request(base={"repo": {"full_name": "upstream/tool", "name": "tool", "owner": {"login": "upstream"}, "private": True}}),
        ]
        for value in bad_pulls:
            with self.subTest(value=value):
                api = FixtureAPI(search_pages=[search_results([search_item()])], external={"repos/upstream/tool": external_repository(), "repos/upstream/tool/pulls/1": value})
                repositories, _ = fetch.fetch_contributed_repositories("nisconder", api)
                self.assertEqual(repositories, [])
        api = FixtureAPI(search_pages=[search_results([search_item()])], external={"repos/upstream/tool": external_repository(private=True, visibility="private")})
        self.assertEqual(fetch.fetch_contributed_repositories("nisconder", api)[0], [])
        self.assertNotIn("repos/upstream/tool/pulls/1", [endpoint for endpoint, _ in api.calls])

    def test_full_names_and_pull_numbers_are_case_insensitively_deduplicated(self):
        api = FixtureAPI(
            search_pages=[search_results([search_item(), search_item("Upstream/Tool", 1), search_item(number=2), search_item("nisconder/alpha", 7)])],
            external={"repos/upstream/tool": external_repository(), "repos/upstream/tool/pulls/1": pull_request(), "repos/upstream/tool/pulls/2": pull_request(number=2)},
        )
        repositories, _ = fetch.fetch_contributed_repositories("nisconder", api)
        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0]["contribution"]["mergedPullRequests"], 2)
        self.assertEqual([item["number"] for item in repositories[0]["contribution"]["pullRequests"]], [1, 2])
        self.assertEqual([endpoint for endpoint, _ in api.calls].count("repos/upstream/tool"), 1)
        self.assertNotIn("repos/nisconder/alpha", [endpoint for endpoint, _ in api.calls])

    def test_not_found_candidates_are_dropped_but_other_api_failures_preserve_snapshot(self):
        unavailable = FixtureAPI(search_pages=[search_results([search_item()])], external={"repos/upstream/tool": fetch.NotFound("Deleted")})
        self.assertEqual(fetch.fetch_contributed_repositories("nisconder", unavailable)[0], [])
        missing_pull = FixtureAPI(search_pages=[search_results([search_item()])], external={"repos/upstream/tool": external_repository(), "repos/upstream/tool/pulls/1": fetch.NotFound("Deleted")})
        self.assertEqual(fetch.fetch_contributed_repositories("nisconder", missing_pull)[0], [])
        failed = FixtureAPI(search_pages=[search_results([search_item()])], external={"repos/upstream/tool": external_repository(), "repos/upstream/tool/pulls/1": fetch.DataError("Simulated API failure")})
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            for filename in ["github-profile.json", "contributions.json"]:
                (root / filename).write_text("unchanged " + filename, encoding="utf-8")
            original = {item.name: item.read_bytes() for item in root.iterdir()}
            with patch.object(fetch, "GitHubCLI", return_value=failed), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                fetch.main(["--date", SNAPSHOT.isoformat(), "--output-dir", directory])
            self.assertEqual({item.name: item.read_bytes() for item in root.iterdir()}, original)

    def test_external_repository_cap_marks_verified_counts_as_a_truncated_sample(self):
        candidates = [search_item(f"upstream/tool-{number}") for number in range(21)]
        external = {}
        for number in range(21):
            full_name = f"upstream/tool-{number}"
            external[f"repos/{full_name}"] = external_repository(name=f"tool-{number}")
            external[f"repos/{full_name}/pulls/1"] = pull_request(full_name)
        api = FixtureAPI(search_pages=[search_results(candidates)], external=external)
        repositories, scope = fetch.fetch_contributed_repositories("nisconder", api)
        self.assertEqual(len(repositories), 20)
        self.assertTrue(scope["truncated"])
        self.assertEqual(scope["repositoryLimit"], 20)
        self.assertEqual(scope["checkedPullRequests"], 20)
        self.assertNotIn("repos/upstream/tool-20", [endpoint for endpoint, _ in api.calls])

    def test_incomplete_search_fails_and_cli_404_is_distinguishable(self):
        api = FixtureAPI(search_pages=[search_results(incomplete_results=True)])
        with self.assertRaises(fetch.DataError):
            fetch.fetch_contributed_repositories("nisconder", api)
        not_found = subprocess.CompletedProcess([], 1, stdout=json.dumps({"message": "Not Found", "status": "404"}), stderr="")
        with patch.object(fetch.subprocess, "run", return_value=not_found), self.assertRaises(fetch.NotFound):
            fetch.GitHubCLI().request("repos/missing/project")

    def test_external_search_stops_after_three_pages_and_does_not_claim_total_count(self):
        pages = [search_results([search_item(number=number) for number in range(start, start + 100)], total_count=301) for start in [1, 101, 201]]
        external = {"repos/upstream/tool": external_repository()}
        external.update({f"repos/upstream/tool/pulls/{number}": pull_request(number=number) for number in range(1, 301)})
        api = FixtureAPI(search_pages=pages, external=external)
        repositories, scope = fetch.fetch_contributed_repositories("nisconder", api)
        self.assertEqual(repositories[0]["contribution"]["mergedPullRequests"], 300)
        self.assertEqual(scope["totalMatches"], 301)
        self.assertEqual(scope["pullRequestLimit"], 300)
        self.assertEqual(scope["checkedPullRequests"], 300)
        self.assertTrue(scope["truncated"])
        self.assertEqual(len([endpoint for endpoint, _ in api.calls if endpoint.startswith("search/issues?")]), 3)


if __name__ == "__main__":
    unittest.main()
