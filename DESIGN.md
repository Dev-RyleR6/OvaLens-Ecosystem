# Dashboard design

The dashboard is an operational record system. Retain the FU identity and replace decorative styling with clear hierarchy, visible data provenance, and consistent controls.

- Use the supplied logo, maroon #800000 for primary actions and selection, #357a38 for fertile results, #DC2626 for reject/error states, and amber for review states.
- Use `ovalens_logo_final.svg` with a trimmed canvas. The navigation rail stays FU maroon in both themes, with warm white active links, tinted secondary text, and a darker connection-status footer. Keep operational content on slate and white surfaces.
- Group batch breed, incubator, and dates beneath the identifier; keep numeric columns readable and secondary row actions in a portaled floating menu that never expands table rows. Show one primary batch status, with the checkpoint as secondary text. Align the batches workspace with the main content gutter on wide screens. Batch cards adapt to available content width.
- Use self-hosted IBM Plex Sans in Latin weights 400, 500, 600, and 700, with system sans fallbacks and swap loading. Use 14px default UI text, 12px metadata, 18px section headings, and 24px page headings; mobile form controls use 16px. Use tabular numerals for measurements and amounts.
- Use shared `page-header`, `page-actions`, `primary-action`, `secondary-action`, `filter-panel`, and `status-badge` patterns. Use Lucide icons with consistent 16–18px strokes, paired with action labels where space permits; hide decorative icons from assistive technology. Do not add generic decorative icon tiles.
- Size card grids from available content width, not viewport width. Let identifiers and action groups wrap, and retain all primary tasks on narrow screens.
- Use grouped sections, bordered data tables, and a compact summary strip. Avoid gradients, glow, animated entrances, nested cards, and decorative status badges.
- Provide light and dark slate themes through shared CSS variables. Themes change neutrals and semantic state surfaces; brand colors retain their identity.
- Use at least 44px touch targets, visible keyboard focus, associated labels, live error feedback, and keyboard-contained overlays with focus restoration.
- Use the shared `CloseButton` for icon-only dismissal: 44px square, 18px Lucide X, a neutral filled background, 8px corners, and consistent hover/focus/disabled states. Keep labeled Cancel and Close footer actions as regular secondary buttons.
- Prefer explicit empty, loading, offline, and stale states over example values. Diagnostic success requires a real acknowledgement.
- Preserve table scrolling within the content region on small screens. The mobile sidebar must be dismissible and inaccessible while closed.
- Use horizontal bars with complete wrapped batch identifiers, numeric axes starting at zero, and expandable exact-count tables. Keep charts in one column until the content region can fit two readable panels.
- Treat scan events as records, not unique eggs. Show repeated scans without clamping them to the initial egg count. Classification and financial figures must use the same filter scope and persisted scan records.
- Keep stage and status badges on one line, use the same semantic styles across pages, and allow wide operational tables to scroll rather than compressing columns.
- Role badges share a neutral treatment. A routine Day 10 checkpoint is neutral; warning color belongs to due or review states. Paired operational charts use the same batch rows, zero-based scale, plot height, and aligned exact-count disclosures; preserve zero-scan batches and display numeric bar values.
