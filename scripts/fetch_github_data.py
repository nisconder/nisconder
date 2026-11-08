"""Fetch public GitHub profile inputs with GitHub CLI; no third-party packages.

The workflow authenticates gh with its short-lived GITHUB_TOKEN. A local run can
use an existing `gh auth login`; credentials never enter generated JSON or logs.
Public owner repositories, verified merged pull requests in external public
repositories, and contribution calendar counts are persisted. External project
counts cover at most 300 searched PRs and 20 repositories, not an all-time total.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote, urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
# Shanghai has used UTC+8 without daylight-saving changes since 1991. A fixed
# offset keeps this standard-library-only script portable on Windows too.
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")
LEVELS = {"NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"}
EXTERNAL_PULL_REQUEST_LIMIT = 300
EXTERNAL_REPOSITORY_LIMIT = 20
CALENDAR_QUERY = """
query ProfileCalendar($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    login
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes { ... on Repository { name isPrivate owner { login } } }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""


class DataError(RuntimeError):
    """The new snapshot is incomplete or invalid; keep the prior snapshot."""


class NotFound(DataError):
    """A previously public search candidate is deleted or no longer visible."""


class GitHubCLI:
    def __init__(self, executable: str = "gh") -> None:
        self.executable = executable

    def request(self, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
        command = [self.executable, "api", endpoint, "-H", "Accept: application/vnd.github+json"]
        if payload is not None:
            command += ["--input", "-"]
        try:
            result = subprocess.run(
                command,
                input=json.dumps(payload) if payload is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DataError("GitHub CLI could not complete the API request; existing data was kept.") from exc
        if result.returncode:
            # Never echo subprocess output: a user's GH_DEBUG can include headers.
            try:
                error = json.loads(result.stdout)
            except json.JSONDecodeError:
                error = {}
            if (isinstance(error, dict) and str(error.get("status")) == "404") or re.search(r"\bHTTP 404\b", result.stderr):
                raise NotFound("A public GitHub resource is no longer available.")
            raise DataError(f"GitHub API request failed (exit {result.returncode}); existing data was kept.")
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise DataError("GitHub returned invalid JSON; existing data was kept.") from exc
        if isinstance(response, dict) and response.get("errors"):
            raise DataError("GitHub GraphQL returned errors; existing data was kept.")
        return response


def checked_login(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", value):
        raise DataError("Invalid GitHub username.")
    return value


def natural(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise DataError(f"Invalid non-negative count: {field}.")
    return value


def public_url(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise DataError("Missing public GitHub URL.")
    url = urlparse(value)
    if (url.scheme != "https" or url.netloc != "github.com"
            or url.path.rstrip("/").casefold() != path.casefold()
            or url.params or url.query or url.fragment):
        raise DataError("Unexpected public GitHub URL.")
    return value.rstrip("/")


def plain_text(value: Any, field: str, *, nullable: bool = False) -> str:
    if value is None and nullable:
        return ""
    if not isinstance(value, str):
        raise DataError(f"Invalid text field: {field}.")
    return " ".join(value.split())


def normalize_repositories(rows: list[dict[str, Any]], login: str) -> list[dict[str, Any]]:
    repositories = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise DataError("Invalid repository response.")
        # Defense in depth: users/:login/repos only returns public repositories,
        # but never serialize private or non-owner records even in a fixture.
        if row.get("private") is not False or row.get("visibility", "public") != "public":
            continue
        if str(row.get("owner", {}).get("login", "")).casefold() != login.casefold():
            continue
        name = plain_text(row.get("name"), "repository name")
        if not name or "/" in name or name.casefold() in seen:
            raise DataError("Missing or duplicate repository name.")
        seen.add(name.casefold())
        if type(row.get("fork")) is not bool or type(row.get("archived")) is not bool:
            raise DataError("Invalid repository status.")
        language = row.get("language")
        if language is not None:
            language = plain_text(language, "repository language")
        pushed = row.get("pushed_at")
        if pushed is not None:
            try:
                parsed = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            except (ValueError, AttributeError, TypeError) as exc:
                raise DataError("Invalid repository push timestamp.") from exc
            if parsed.tzinfo is None:
                raise DataError("Repository push timestamp needs a timezone.")
        repositories.append({
            "name": name,
            "description": plain_text(row.get("description"), "repository description", nullable=True),
            "url": public_url(row.get("html_url"), f"/{login}/{name}"),
            "stars": natural(row.get("stargazers_count"), "repository stars"),
            "forks": natural(row.get("forks_count"), "repository forks"),
            "language": language,
            "isFork": row["fork"],
            "isArchived": row["archived"],
            # Generated commits update the profile repo itself. Its push time
            # must not force another generated commit on the following run.
            "pushedAt": None if name.casefold() == login.casefold() else pushed,
            "isProfile": name.casefold() == login.casefold(),
        })
    return sorted(repositories, key=lambda repository: repository["name"].casefold())


def search_pull_request(item: Any) -> tuple[str, int] | None:
    """Take only a well-formed GitHub pull endpoint; search is not proof of work."""
    if not isinstance(item, dict) or not isinstance(item.get("pull_request"), dict):
        return None
    address = item["pull_request"].get("url")
    if not isinstance(address, str):
        raise DataError("Missing pull request endpoint in search results.")
    parsed = urlparse(address)
    match = re.fullmatch(r"/repos/([^/]+)/([A-Za-z0-9_.-]{1,100})/pulls/([1-9][0-9]*)", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.params or parsed.query or parsed.fragment or not match:
        raise DataError("Unexpected pull request endpoint in search results.")
    owner, name, number = match.groups()
    checked_login(owner)
    if type(item.get("number")) is not int or item["number"] != int(number):
        raise DataError("Mismatched pull request number in search results.")
    return f"{owner}/{name}", int(number)


def normalize_external_repository(raw: Any, expected_full_name: str, login: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise DataError("Invalid external repository response.")
    if raw.get("private") is not False or raw.get("visibility", "public") != "public":
        return None
    owner = checked_login(raw.get("owner", {}).get("login"))
    if owner.casefold() == login.casefold():
        return None
    full_name = plain_text(raw.get("full_name"), "external full repository name")
    if full_name.casefold() != expected_full_name.casefold() or full_name.casefold() != f"{owner}/{raw.get('name', '')}".casefold():
        return None
    normalized = normalize_repositories([raw], owner)
    if len(normalized) != 1:
        return None
    repository = normalized[0]
    repository.update({"fullName": full_name, "owner": owner, "relationship": "contributor", "isProfile": False, "pushedAt": raw.get("pushed_at")})
    return repository


def verified_pull_request(raw: Any, full_name: str, number: int, login: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or type(raw.get("merged")) is not bool:
        raise DataError("Incomplete pull request verification response.")
    author = raw.get("user")
    if raw["merged"] is not True or not isinstance(author, dict) or str(author.get("login", "")).casefold() != login.casefold():
        return None
    base = raw.get("base", {}).get("repo")
    if not isinstance(base, dict):
        raise DataError("Missing pull request target repository.")
    if base.get("private") is not False or base.get("visibility", "public") != "public":
        return None
    owner, name = full_name.split("/", 1)
    if (str(base.get("full_name", "")).casefold() != full_name.casefold()
            or str(base.get("owner", {}).get("login", "")).casefold() != owner.casefold()
            or str(base.get("name", "")).casefold() != name.casefold()
            or type(raw.get("number")) is not int or raw["number"] != number):
        return None
    merged_at = raw.get("merged_at")
    try:
        merged = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError) as exc:
        raise DataError("Missing or invalid merged pull request timestamp.") from exc
    if merged.tzinfo is None:
        raise DataError("Merged pull request timestamp needs a timezone.")
    return {
        "number": number,
        "title": plain_text(raw.get("title"), "pull request title"),
        "url": public_url(raw.get("html_url"), f"/{full_name}/pull/{number}"),
        "mergedAt": merged_at,
    }


def fetch_contributed_repositories(login: str, api: GitHubCLI) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Find at most 300 candidates and verify at most 20 external repositories.

    Search candidates are newest-updated first. Counts only describe verified
    PRs from this capped sample. A timeout/incomplete search or non-404 API
    failure rejects the entire refresh, preserving the previous snapshot.
    """
    query = f"author:{login} type:pr is:merged is:public -user:{login}"
    candidates, total_matches = [], 0
    for page in range(1, EXTERNAL_PULL_REQUEST_LIMIT // 100 + 1):
        response = api.request("search/issues?" + urlencode({"q": query, "per_page": 100, "page": page, "sort": "updated", "order": "desc"}))
        if not isinstance(response, dict) or not isinstance(response.get("items"), list) or type(response.get("incomplete_results")) is not bool:
            raise DataError("Incomplete external pull request search response.")
        if response["incomplete_results"]:
            raise DataError("GitHub search returned incomplete results; existing data was kept.")
        total_matches = max(total_matches, natural(response.get("total_count"), "matching external pull requests"))
        items = response["items"]
        if len(items) > 100:
            raise DataError("Unexpected external pull request page length.")
        candidates.extend(items)
        if len(items) < 100 or len(candidates) >= total_matches:
            break
    repositories, metadata, seen_pulls = {}, {}, set()
    checked_pulls, repository_cap_hit = 0, False
    for item in candidates:
        candidate = search_pull_request(item)
        if candidate is None:
            continue
        full_name, number = candidate
        key = full_name.casefold()
        if full_name.split("/", 1)[0].casefold() == login.casefold() or (key, number) in seen_pulls:
            continue
        seen_pulls.add((key, number))
        if key not in repositories and len(repositories) >= EXTERNAL_REPOSITORY_LIMIT:
            repository_cap_hit = True
            continue
        if key not in metadata:
            try:
                raw_repository = api.request("repos/" + full_name)
            except NotFound:
                metadata[key] = None
            else:
                metadata[key] = normalize_external_repository(raw_repository, full_name, login)
        if metadata[key] is None:
            continue
        checked_pulls += 1
        try:
            raw_pull = api.request(f"repos/{full_name}/pulls/{number}")
        except NotFound:
            continue
        pull = verified_pull_request(raw_pull, metadata[key]["fullName"], number, login)
        if pull is None:
            continue
        if key not in repositories:
            repositories[key] = {
                **metadata[key],
                "contribution": {"mergedPullRequests": 0, "countScope": "verified search sample", "pullRequests": []},
            }
        repositories[key]["contribution"]["pullRequests"].append(pull)
    normalized = sorted(repositories.values(), key=lambda repository: repository["fullName"].casefold())
    for repository in normalized:
        pulls = repository["contribution"]["pullRequests"]
        pulls.sort(key=lambda pull: pull["number"])
        repository["contribution"]["mergedPullRequests"] = len(pulls)
    return normalized, {
        "query": query,
        "totalMatches": total_matches,
        "pullRequestLimit": EXTERNAL_PULL_REQUEST_LIMIT,
        "repositoryLimit": EXTERNAL_REPOSITORY_LIMIT,
        "checkedPullRequests": checked_pulls,
        "truncated": total_matches > len(candidates) or repository_cap_hit,
    }


def normalize_calendar(calendar: Any, snapshot: date) -> dict[str, Any]:
    if not isinstance(calendar, dict) or not isinstance(calendar.get("weeks"), list):
        raise DataError("Missing contribution calendar.")
    weeks, dates, total = [], [], 0
    for week in calendar["weeks"]:
        if not isinstance(week, dict) or not isinstance(week.get("contributionDays"), list):
            raise DataError("Invalid contribution week.")
        days = []
        for day in week["contributionDays"]:
            try:
                parsed = date.fromisoformat(day["date"])
                count = natural(day["contributionCount"], "daily contributions")
                level = day["contributionLevel"]
            except (KeyError, TypeError, ValueError) as exc:
                raise DataError("Invalid contribution day.") from exc
            if level not in LEVELS:
                raise DataError("Unknown contribution level.")
            dates.append(parsed)
            total += count
            days.append({"date": parsed.isoformat(), "contributionCount": count, "contributionLevel": level})
        if not days or len(days) > 7:
            raise DataError("Invalid number of days in contribution week.")
        weeks.append({"contributionDays": days})
    if not dates or len(dates) > 366:
        raise DataError("Invalid contribution calendar length.")
    if dates != sorted(set(dates)) or any(b - a != timedelta(days=1) for a, b in zip(dates, dates[1:])):
        raise DataError("Contribution calendar has duplicate, unsorted or missing days.")
    if dates[-1] > snapshot or dates[0] < snapshot - timedelta(days=365):
        raise DataError("Contribution calendar falls outside its requested period.")
    if natural(calendar.get("totalContributions"), "total contributions") != total:
        raise DataError("Contribution totals do not match daily counts.")
    return {
        "snapshotDate": snapshot.isoformat(),
        "timezone": "Asia/Shanghai",
        "source": "GitHub GraphQL contributionCalendar",
        "periodStart": dates[0].isoformat(),
        "periodEnd": dates[-1].isoformat(),
        "totalContributions": total,
        "weeks": weeks,
    }


def fetch_snapshots(login: str, snapshot: date, api: GitHubCLI) -> tuple[dict[str, Any], dict[str, Any]]:
    login = checked_login(login)
    raw_user = api.request(f"users/{quote(login)}")
    if not isinstance(raw_user, dict):
        raise DataError("Missing public user profile.")
    canonical = checked_login(raw_user.get("login"))
    if canonical.casefold() != login.casefold():
        raise DataError("GitHub returned a different account.")
    all_repositories = []
    for page in range(1, 1001):
        rows = api.request(f"users/{quote(canonical)}/repos?per_page=100&page={page}&type=owner&sort=full_name&direction=asc")
        if not isinstance(rows, list):
            raise DataError("Missing repository page.")
        all_repositories.extend(rows)
        if len(rows) < 100:
            break
    else:
        raise DataError("Repository pagination did not finish.")
    repositories = normalize_repositories(all_repositories, canonical)
    start = snapshot - timedelta(days=364)
    response = api.request("graphql", {
        "query": CALENDAR_QUERY,
        "variables": {"login": canonical, "from": start.isoformat() + "T00:00:00Z", "to": snapshot.isoformat() + "T23:59:59Z"},
    })
    try:
        graphql_user = response["data"]["user"]
        if not isinstance(graphql_user, dict) or graphql_user.get("login", "").casefold() != canonical.casefold():
            raise DataError("Missing GraphQL user.")
        calendar = graphql_user["contributionsCollection"]["contributionCalendar"]
        pinned = graphql_user["pinnedItems"]["nodes"]
    except (KeyError, TypeError, AttributeError) as exc:
        raise DataError("Incomplete GraphQL profile response.") from exc
    contributions = normalize_calendar(calendar, snapshot)
    originals = [repository for repository in repositories if not repository["isFork"]]
    owned = {repository["name"].casefold(): repository["name"] for repository in repositories}
    pinned_names = []
    if not isinstance(pinned, list):
        raise DataError("Invalid pinned repository response.")
    for repository in pinned:
        if not isinstance(repository, dict) or repository.get("isPrivate") is not False:
            continue
        if str(repository.get("owner", {}).get("login", "")).casefold() != canonical.casefold():
            continue
        name = str(repository.get("name", "")).casefold()
        if name in owned and owned[name] not in pinned_names:
            pinned_names.append(owned[name])
    contributed_repositories, contribution_search = fetch_contributed_repositories(canonical, api)
    profile = {
        "schemaVersion": 1,
        "snapshotDate": snapshot.isoformat(),
        "timezone": "Asia/Shanghai",
        "source": "GitHub REST and GraphQL APIs",
        "user": {
            "login": canonical,
            "name": plain_text(raw_user.get("name"), "profile name", nullable=True) or canonical,
            "bio": plain_text(raw_user.get("bio"), "profile biography", nullable=True),
            "url": public_url(raw_user.get("html_url"), f"/{canonical}"),
            "followers": natural(raw_user.get("followers"), "followers"),
            "following": natural(raw_user.get("following"), "following"),
        },
        "repositories": repositories,
        "pinnedRepositories": pinned_names,
        "contributedRepositories": contributed_repositories,
        "contributionSearch": contribution_search,
        "stats": {
            "publicRepositories": len(repositories),
            "originalRepositories": len(originals),
            "totalStars": sum(repository["stars"] for repository in repositories),
            "originalStars": sum(repository["stars"] for repository in originals),
            "totalForks": sum(repository["forks"] for repository in repositories),
            "originalForks": sum(repository["forks"] for repository in originals),
        },
    }
    return profile, contributions


def write_snapshots(directory: Path, profile: dict[str, Any], contributions: dict[str, Any]) -> None:
    """Stage both validated documents before replacing either prior snapshot."""
    directory.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for name, payload in [("github-profile.json", profile), ("contributions.json", contributions)]:
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            destination = directory / name
            if destination.exists() and destination.read_text(encoding="utf-8") == content:
                continue
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=directory, delete=False) as output:
                output.write(content)
                staged.append((Path(output.name), destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=os.environ.get("PROFILE_USER", "nisconder"))
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="Snapshot date, default: today in Asia/Shanghai")
    parser.add_argument("--gh", default="gh", help="GitHub CLI executable, useful when gh is not on PATH")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)
    snapshot = args.date or datetime.now(SHANGHAI).date()
    try:
        profile, contributions = fetch_snapshots(args.user, snapshot, GitHubCLI(args.gh))
        write_snapshots(args.output_dir, profile, contributions)
    except (DataError, OSError) as exc:
        parser.exit(1, f"Profile refresh failed: {exc}\n")
    print(f"Saved {len(profile['repositories'])} public owner repositories and {contributions['totalContributions']} calendar contributions for {snapshot}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
