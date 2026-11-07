# Original profile artwork

The profile combines standard technology badges with an identity hero,
a real contribution calendar, five linked project cards, and a notes entry.
The custom artwork shares graphite / silver, ice blue and pale gold palettes.

- Each current module has wide and mobile layouts, in light and dark themes.
  The README uses four picture sources per image; the mobile breakpoint is 640px.
- Thirty-six current SVGs are self-contained: no JavaScript, foreignObject, remote
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
- Project illustrations describe capabilities and examples, not usage counts,
  safety guarantees, service availability, or live execution results.
- Contribution values are derived from the saved GitHub data, with a visible
  snapshot date. Desktop shows the full saved year; mobile shows the last 26
  calendar weeks and calculates its own total. The effect never changes values.

Regenerate using Python's standard library:

```sh
python scripts/generate_identity.py
python scripts/generate_cards.py
```

The identity generator reads data/contributions.json and verifies that the sum
of daily counts equals totalContributions. Generating SVGs does not fetch data.

The earlier profile-wide.svg and profile-compact.svg remain as legacy assets
for existing links; the current README uses the theme-specific modules.
