# Original profile artwork

The profile combines standard technology badges with an identity hero,
a real contribution calendar, public statistics, up to six linked project cards,
and a notes entry. GitHub Actions refreshes the data and SVGs every six hours.
The custom artwork shares graphite / silver, ice blue and pale gold palettes.

- Each current module has wide and mobile layouts, in light and dark themes.
  The README uses four picture sources per image; the mobile breakpoint is 640px.
- All current SVGs are self-contained: no JavaScript, foreignObject, remote
  fonts, remote images, or third-party rendering services.
- The technology row uses standard Shields.io flat-square badges with Simple
  Icons brand logos. These images are loaded from img.shields.io and are not
  redrawn initials. The former custom technology strip has been removed.
- All body copy uses a shared system sans-serif stack. Project cards use
  title/body/meta sizes of 34/24/20 on desktop and 28/22/20 on a 400px mobile
  canvas. Only code
  and numeric illustrations use monospace. Repeated English headings and
  invented slogans are omitted.
- Essential words and values are present in the static image. CSS and SMIL add
  contour motion, scans, connection pulses, Unicode reveal and a calendar wash.
  Reduced-motion styling stops CSS animations and hides moving SMIL marks.
- Project language, Stars, Forks and code update dates come from GitHub. The
  footer uses official MIT-licensed GitHub Octicons for Stars and Forks; see
  [their license](OCTICONS-LICENSE.txt) and [upstream](https://github.com/primer/octicons).
- Known projects have reviewed short Chinese summaries in
  `data/project-display.json`. Each summary is bound to the SHA-256 of the
  repository description reviewed with it. If that description changes, the
  card immediately uses the new GitHub description instead; it is never hidden
  behind stale curated text. Full source metadata remains in the accessible SVG
  description. Unknown projects use the current GitHub name and description.
- Each known project has its own functional diagram: package evidence, Harness
  installation hook, archive diff, IPv4/IPv6 probes, article outline and 8086
  instruction example. `scripts/project_art.py` supplies a shared coordinate
  system and one primary motion per diagram. The effect illustrates a feature,
  not a live result, security verdict or connection status. Reduced motion keeps
  every essential label visible.
- Contribution values are derived from fetched GitHub data, with a visible
  update date. Desktop shows the full saved year; mobile shows the last 26
  calendar weeks and calculates its own total. The effect never changes values.

Regenerate using Python's standard library:

```sh
python scripts/fetch_github_data.py
python scripts/update_profile.py
```

The identity generator verifies daily contributions sum to totalContributions.
Generators render saved data without network access; the fetch step updates the
data separately. See [the data policy](../data/README.md) for metric definitions
and project selection. README links use content hashes to refresh changed images.

The earlier profile-wide.svg and profile-compact.svg remain as legacy assets
for existing links; the current README uses the theme-specific modules.
