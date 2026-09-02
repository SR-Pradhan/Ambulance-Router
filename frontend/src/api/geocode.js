/**
 * Address lookup, so a person can type where they are instead of typing
 * coordinates.
 *
 * Uses Nominatim, OpenStreetMap's own geocoder, for the same reason the map
 * uses OSM tiles: no key, no billing, and the addresses come from the same
 * dataset the road graph was built from, so a result is far more likely to
 * sit on a road this project actually knows about.
 *
 * Nominatim's usage policy asks for at most one request per second and a
 * genuine referrer. The caller debounces (see RequestForm) and browsers send
 * the referrer automatically. A production system would proxy this through the
 * backend so it could cache results and send a real User-Agent; that is a
 * deliberate simplification, not an oversight.
 */

const NOMINATIM = "https://nominatim.openstreetmap.org";

/**
 * The bounding box of the road network actually loaded in the database
 * (433 junctions around Gurugram). Searching outside it returns places this
 * project cannot route to, so results are biased to this box and anything
 * outside it is flagged rather than silently accepted.
 */
export const COVERAGE = {
  minLat: 28.4335,
  maxLat: 28.5101,
  minLng: 76.9898,
  maxLng: 77.0716,
};

export function isInsideCoverage(lat, lng) {
  return (
    lat >= COVERAGE.minLat &&
    lat <= COVERAGE.maxLat &&
    lng >= COVERAGE.minLng &&
    lng <= COVERAGE.maxLng
  );
}

/** Nominatim wants the box as left,top,right,bottom. */
const VIEWBOX = [
  COVERAGE.minLng,
  COVERAGE.maxLat,
  COVERAGE.maxLng,
  COVERAGE.minLat,
].join(",");

/**
 * Shorten a Nominatim display_name.
 *
 * The raw value is a long comma-separated chain ending in "Haryana, 122001,
 * India", which is the same on every result and pushes the part that actually
 * distinguishes them off the end of the line. Keeping the first few segments
 * keeps the distinguishing part visible.
 */
function shorten(displayName) {
  const seen = new Set();
  const parts = [];
  for (const raw of displayName.split(",")) {
    const part = raw.trim();
    // Nominatim repeats a name across levels ("Sector 14, IFFCO Chowk,
    // Sector 14"), which wastes the little space this label has.
    const key = part.toLowerCase();
    if (!part || seen.has(key)) continue;
    seen.add(key);
    parts.push(part);
    if (parts.length === 3) break;
  }
  return parts.join(", ");
}

export async function searchAddress(query, { signal } = {}) {
  if (!query || query.trim().length < 3) return [];

  const url =
    `${NOMINATIM}/search?format=jsonv2&limit=6&addressdetails=0` +
    `&viewbox=${VIEWBOX}&bounded=1&q=${encodeURIComponent(query)}`;

  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Address search is unavailable right now.");

  const rows = await response.json();
  return rows.map((r) => ({
    id: `${r.osm_type}-${r.osm_id}`,
    label: shorten(r.display_name),
    full: r.display_name,
    lat: Number(r.lat),
    lng: Number(r.lon),
  }));
}

/** Coordinates to a human readable place, used after a click on the map. */
export async function reverseGeocode(lat, lng, { signal } = {}) {
  const url =
    `${NOMINATIM}/reverse?format=jsonv2&zoom=17&addressdetails=0` +
    `&lat=${lat}&lon=${lng}`;

  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) return null;

  const row = await response.json();
  return row?.display_name ? shorten(row.display_name) : null;
}

/**
 * The browser's own geolocation, wrapped as a promise.
 *
 * Deliberately reports the three failure cases separately: a refused permission
 * is a different problem from a device that cannot get a fix, and telling
 * someone "allow location access" when the real issue is a timeout sends them
 * to the wrong setting.
 */
export function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("This browser cannot report your location."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => {
        if (err.code === err.PERMISSION_DENIED)
          reject(new Error("Location access was blocked. Allow it in your browser, or search for an address instead."));
        else if (err.code === err.POSITION_UNAVAILABLE)
          reject(new Error("Your device could not get a location fix. Try searching for an address."));
        else reject(new Error("Getting your location took too long. Try searching for an address."));
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
}
