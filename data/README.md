# Automatic profile data

The [update workflow](https://github.com/nisconder/nisconder/actions/workflows/update-profile.yml)
reads public GitHub data every six hours, at 02:17, 08:17, 14:17 and 20:17 in
Asia/Shanghai. GitHub may delay scheduled jobs. It also supports **Run workflow**
and runs when its scripts or tests change.

- `github-profile.json`: public owner repositories, descriptions, primary
  languages, Stars, Forks, push dates, pinned repositories and follower counts.
  The profile repository's own push date is omitted from comparisons so generated
  commits do not cause a new update by themselves.
- `contributedRepositories` contains public upstream repositories with verified
  merged PRs authored by this user. Search only discovers candidates: every PR is
  checked again through the PR API for its author, merged state and target repo.
  Bot-authored PRs, private targets, unmerged PRs and duplicate PRs are excluded.
  The scan checks at most 300 recent search candidates and 20 valid upstream
  repositories; `contributionSearch` records these limits and any truncation.
  Card counts say "已核验 N 个合并 PR", describing verified records rather than an
  uncapped lifetime total. Stars and Forks alone are not contribution evidence.
- `contributions.json`: GitHub's daily contribution counts and levels for a
  rolling year, with the API's actual `periodStart` and `periodEnd`. Calendar days
  follow GitHub's API; the refresh date uses Asia/Shanghai. No repository names
  or private contribution details are stored in this calendar.
- `projects[]` follows `featured-projects.json`: a curated mix of useful owned
  tools and verified upstream work, not a ranking by repository size or recency.
  Every selection must still pass eligibility checks on each refresh. If an
  entry is removed or archived, or no longer has public contribution evidence,
  it is replaced using eligible pinned/recent repositories. Owned Forks and the
  profile repository are not selected. Upstreams use their actual owner URL,
  contributor labels and links to the verified merged PRs.

The public repository count includes Forks. Stars and Forks in the statistics
strip count the user's own **non-Fork public repositories**, including archived
repositories and this profile repository. Project cards show each repository's
individual values. Upstream Stars/Forks are not added to personal totals. Counts
are fetched, never inferred from animation.

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

`featured-projects.json` uses canonical `owner/repository` identities. Editing
the featured list triggers regeneration too. A contributed repository never
becomes eligible merely because its name was added to that list.
