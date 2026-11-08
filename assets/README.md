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
  title/body/meta sizes of 32/22/18 on desktop and 26/20/18 on mobile. Only code
  and numeric illustrations use monospace. Repeated English headings and
  invented slogans are omitted.
- Essential words and values are present in the static image. CSS and SMIL add
  contour motion, scans, connection pulses, Unicode reveal and a calendar wash.
  Reduced-motion styling stops CSS animations and hides moving SMIL marks.
- Project descriptions, names, language, Stars, Forks and code update dates come
  from GitHub. Descriptions wrap without reducing their font size. New projects
  receive a repository illustration; known tools retain their original artwork.
  These animations illustrate capabilities, not live execution results.
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
