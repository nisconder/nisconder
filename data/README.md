# Contribution snapshot

`contributions.json` contains the user's own GitHub GraphQL
`contributionCalendar` response, normalized with a snapshot date. It was read
using GitHub CLI on 2026-11-07 for 2025-11-08 through 2026-11-07, with Asia/Shanghai
date bounds. It contains public-profile daily counts and contribution levels,
not repository names or private activity details.

The profile images label this date explicitly. They are a snapshot, not live
statistics. Refreshing the data is a separate read action; the SVG generator
only checks and renders the saved data. When refreshing, preserve the fields
`snapshotDate`, `totalContributions`, and `weeks` with each day's `date`,
`contributionCount`, and `contributionLevel`. Update the README image alt text
to the new snapshot date too.
