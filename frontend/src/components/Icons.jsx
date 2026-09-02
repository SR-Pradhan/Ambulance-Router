/**
 * Inline SVG icons.
 *
 * These replace the emoji that used to sit in the rail. The brand mark itself
 * lives in Logo.jsx, because it carries its own tile and colours.
 * Emoji are the single clearest sign of an unfinished interface: they render
 * differently on every platform, they cannot inherit text colour, they cannot
 * be aligned optically against text, and they carry a cartoon weight that no
 * dispatch tool would ship. A 16px stroked path solves all four.
 *
 * Inlined rather than pulled from an icon package, because three icons do not
 * justify a dependency and the bundle already carries Leaflet.
 */

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
  focusable: false,
};

export function MapIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 3 3 6v15l6-3 6 3 6-3V3l-6 3-6-3Z" />
      <path d="M9 3v15M15 6v15" />
    </svg>
  );
}

export function BoardIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3 3v18h18" />
      <path d="M7 15v3M12 10v8M17 6v12" />
    </svg>
  );
}
