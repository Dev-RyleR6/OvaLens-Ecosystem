# Dashboard design

The dashboard is an operational record system. Retain the FU identity and replace decorative styling with clear hierarchy, visible data provenance, and consistent controls.

- Use the supplied logo, maroon #800000 for primary actions and selection, #357a38 for fertile results, #DC2626 for reject/error states, and amber for review states.
- Use a single readable sans family, 14px default UI text, 12px metadata, and 24px page headings. Use tabular numerals for measurements and amounts.
- Use grouped sections, bordered data tables, and a compact summary strip. Avoid gradients, glow, animated entrances, nested cards, and decorative status badges.
- Provide light and dark slate themes through shared CSS variables. Themes change neutrals and semantic state surfaces; brand colors retain their identity.
- Use at least 44px touch targets, visible keyboard focus, associated labels, live error feedback, and keyboard-contained overlays with focus restoration.
- Prefer explicit empty, loading, offline, and stale states over example values. Diagnostic success requires a real acknowledgement.
- Preserve table scrolling within the content region on small screens. The mobile sidebar must be dismissible and inaccessible while closed.
- Use horizontal bars with complete wrapped batch identifiers, numeric axes starting at zero, and expandable exact-count tables. Keep charts in one column until the content region can fit two readable panels.
- Treat scan events as records, not unique eggs. Show repeated scans without clamping them to the initial egg count. Classification and financial figures must use the same filter scope and persisted scan records.
- Keep stage and status badges on one line, use the same semantic styles across pages, and allow wide operational tables to scroll rather than compressing columns.
