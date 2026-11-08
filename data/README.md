# Automatic profile data

The [update workflow](https://github.com/nisconder/nisconder/actions/workflows/update-profile.yml)
reads public GitHub data every six hours, at 02:17, 08:17, 14:17 and 20:17 in
Asia/Shanghai. GitHub may delay scheduled jobs. It also supports **Run workflow**
and runs when its scripts or tests change.

- `github-profile.json`: public owner repositories, descriptions, primary
  languages, Stars, Forks, push dates, pinned repositories and follower counts.
  The profile repository's own push date is omitted from comparisons so generated
  commits do not cause a new update by themselves.
- `contributions.json`: GitHub's daily contribution counts and levels for a
  rolling year, with the API's actual `periodStart` and `periodEnd`. Calendar days
  follow GitHub's API; the refresh date uses Asia/Shanghai. No repository names
  or private contribution details are stored in this calendar.
- `projects[]` is derived from the public repository list: take the user's own
  pinned repositories first, then fill up to six by latest code push. Forks,
  archived repositories and the profile repository are excluded from these cards.
  New projects enter this list automatically; changing GitHub pins changes their
  priority. A renamed or removed repository is replaced on the next refresh.

The public repository count includes Forks. Stars and Forks in the statistics
strip count the user's own **non-Fork public repositories**, including archived
repositories and this profile repository. Project cards show each repository's
individual values. Counts are fetched, never inferred from animation.

The workflow uses its built-in, short-lived `GITHUB_TOKEN`, without a personal
access token or external rendering service. Invalid or failed API responses
stop the job; previously published data and images remain available. Generated
commits only include data, SVG assets and the bounded README sections. Unchanged
results produce no commit, and the workflow never force-pushes.

Run the same pipeline locally with Python 3.13+ and an authenticated GitHub CLI:

```sh
python scripts/fetch_github_data.py --user nisconder
python scripts/update_profile.py
python -m unittest discover -s test
```

Only edit README prose outside `BEGIN` / `END` markers. Marked sections and local
SVG image versions are generated. The version is a content hash so changed
images get a new URL without changing URLs for unchanged assets.

`project-display.json` holds reviewed Chinese titles and summaries for known
projects. A summary is used only while its `descriptionSha256` matches the
current normalized GitHub description. A changed description automatically
falls back to that new text; new repositories require no configuration. Editing
this presentation file also triggers a regeneration.
