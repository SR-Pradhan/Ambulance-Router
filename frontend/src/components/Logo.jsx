/**
 * The project mark.
 *
 * A route line that spikes into a heartbeat and ends at a filled destination
 * node. It says both halves of what this project is: pathfinding across a road
 * graph, for a medical emergency. That is the whole reason it is not a generic
 * medical cross, which would describe any health app ever written, and not an
 * emoji, which renders differently on every platform and cannot take a brand
 * colour.
 *
 * Drawn at 32x32 including its own tile, rather than relying on CSS for the
 * background, so this component and the favicon in index.html are the same
 * artwork rather than two things that drift apart.
 *
 * The geometry was checked at 34px, 24px and 16px before being adopted: an
 * earlier version with a node at BOTH ends turned to mush at favicon size, and
 * a shorter spike stopped reading as a pulse.
 */

export const BRAND_TEAL = "#2dd4bf";
export const BRAND_INK = "#0f1113";

export default function BrandMark({ size = 34, title = "Ambulance Route Optimizer" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className="brand-svg"
      role="img"
      aria-label={title}
    >
      <rect width="32" height="32" rx="7" fill={BRAND_TEAL} />
      <path
        d="M4 19.5h5l3-10 4 14 3-8.5h3.4"
        fill="none"
        stroke={BRAND_INK}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="26.6" cy="15" r="2.7" fill={BRAND_INK} />
    </svg>
  );
}
