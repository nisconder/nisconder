# Profile artwork

The two SVGs are original, self-contained artwork for this GitHub profile. The
wide and compact layouts share the same palette and three real tool subjects.

- No JavaScript, `foreignObject`, external font, image or resource is used.
- CSS animates scan lines, signal dashes and inspection nodes. All visible text
  is present in the static SVG; animation never reveals essential information.
- `prefers-reduced-motion: reduce` disables all animation and exposes a stable
  readable state. The perimeter adapts to the reader's light/dark preference;
  the instrument surface keeps its own background and contrast in either theme.
- The README uses a `<picture>` source for a compact layout below 640px.
- Regenerate with `python scripts/render_profile_assets.py` (standard library).

The artwork communicates project subjects, not package safety guarantees,
uptime, usage statistics or released functionality from open pull requests.
