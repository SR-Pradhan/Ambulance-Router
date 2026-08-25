import { Fragment, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

// Leaflet's default marker icons are loaded from relative image paths that
// break under a bundler (the classic "markers are invisible" bug). Using
// divIcon with inline HTML sidesteps the whole asset problem and makes each
// marker type instantly distinguishable on the map.
function emojiIcon(emoji, stateClass) {
  return L.divIcon({
    className: "emoji-marker",
    html: `<div class="pin ${stateClass}">${emoji}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

// A full hospital gets a DASHED ring as well as a red one, so its state is not
// carried by colour alone. The popup states it in words too.
const HOSPITAL_OPEN = emojiIcon("🏥", "is-open");
const HOSPITAL_FULL = emojiIcon("🏥", "is-full");
const AMBULANCE = emojiIcon("🚑", "is-active");
const AMBULANCE_IDLE = emojiIcon("🚑", "is-idle");
const PATIENT = emojiIcon("📍", "is-patient");

const PHASE_LABEL = {
  to_patient: "Travelling to patient",
  to_hospital: "Transporting to hospital",
  arrived: "Arrived at hospital",
  idle: "Available",
  busy_unassigned: "Busy, no active request",
};

// Make the map behave the way a Mac trackpad expects.
//
// Leaflet maps ALL wheel events to zoom. On a trackpad a two-finger swipe IS a
// wheel event, so the map could only be panned by click-and-holding -- swiping
// just zoomed in and out. That is how Leaflet has always behaved, but it is not
// how any native map app behaves.
//
// Browsers report a pinch gesture as a wheel event with ctrlKey set, which is
// what lets us tell the two apart:
//   two-finger swipe (ctrlKey false) -> pan, like Google/Apple Maps
//   pinch            (ctrlKey true)  -> zoom, centred on the pointer
//
// Leaflet's own scrollWheelZoom is turned off on the MapContainer so it does
// not fight this handler.
function TrackpadGestures() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();

    const onWheel = (e) => {
      e.preventDefault(); // stop the page itself from scrolling

      if (e.ctrlKey) {
        const zoom = map.getZoom() - e.deltaY * 0.01;
        map.setZoomAround(map.mouseEventToContainerPoint(e), zoom, { animate: false });
      } else {
        map.panBy([e.deltaX, e.deltaY], { animate: false });
      }
    };

    // passive: false is required or preventDefault() is ignored.
    container.addEventListener("wheel", onWheel, { passive: false });

    // Leaflet writes the character U+2212 into its zoom-out button. Hiding it
    // with CSS would leave the character in the DOM (and in the accessibility
    // tree), so remove the text node and label the button properly instead.
    // The bar itself is drawn as a shape in styles.css.
    const zoomOut = container.querySelector(".leaflet-control-zoom-out");
    if (zoomOut) {
      zoomOut.textContent = "";
      zoomOut.setAttribute("aria-label", "Zoom out");
      zoomOut.setAttribute("title", "Zoom out");
    }
    const zoomIn = container.querySelector(".leaflet-control-zoom-in");
    if (zoomIn) {
      zoomIn.setAttribute("aria-label", "Zoom in");
      zoomIn.setAttribute("title", "Zoom in");
    }

    return () => container.removeEventListener("wheel", onWheel);
  }, [map]);

  return null;
}

// Click anywhere to set the patient's location. This is the interaction that
// makes the whole thing feel like a real dispatch tool.
function ClickToSetPatient({ onPick }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function MapView({ hospitals, live, patient, onPickPatient }) {
  // Centre of the seeded 4x4 road grid.
  const center = [28.47, 77.03];

  return (
    <div className="map-wrap">
      <MapContainer
        center={center}
        zoom={13}
        className="map"
        scrollWheelZoom={false}
        zoomSnap={0}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <TrackpadGestures />
        <ClickToSetPatient onPick={onPickPatient} />

        {/* Hospitals - red pin means full, so it is visibly out of service */}
        {hospitals.map((h) => (
          <Marker
            key={`h-${h.id}`}
            position={[h.latitude, h.longitude]}
            icon={h.accepting ? HOSPITAL_OPEN : HOSPITAL_FULL}
          >
            <Popup>
              <strong>{h.name}</strong>
              <div className="popup-row">
                {h.available_beds} of {h.total_beds} beds free
              </div>
              <span className={h.accepting ? "chip chip-good" : "chip chip-critical"}>
                {h.accepting ? "Accepting patients" : "Full, excluded from dispatch"}
              </span>
            </Popup>
          </Marker>
        ))}

        {/* The patient pin */}
        {patient && (
          <Marker position={[patient.lat, patient.lng]} icon={PATIENT}>
            <Popup>
              <strong>Patient</strong>
              <div className="popup-row">
                {patient.lat.toFixed(5)}, {patient.lng.toFixed(5)}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Each moving ambulance, with the route it is driving */}
        {live.map((a) => {
          const moving = a.request_id !== null;
          return (
            // Fragment, not a div: react-leaflet layers attach themselves to
            // the map imperatively, so a wrapper element would inject a stray
            // DOM node into the map pane.
            <Fragment key={`a-${a.ambulance_id}`}>
              {moving && a.route?.length > 1 && (
                <Polyline
                  positions={a.route.map((p) => [p.lat, p.lng])}
                  pathOptions={{
                    color: a.phase === "to_patient" ? "#ef6c00" : "#1565c0",
                    weight: 4,
                    opacity: 0.7,
                  }}
                />
              )}
              <Marker
                position={[a.lat, a.lng]}
                icon={moving ? AMBULANCE : AMBULANCE_IDLE}
              >
                <Popup>
                  <strong>Ambulance {a.ambulance_id}</strong>
                  {moving ? (
                    <div className="popup-row">
                      <div>{PHASE_LABEL[a.phase] || a.phase}</div>
                      <div>
                        {a.progress_percent}% complete, {a.travelled_km} of{" "}
                        {a.total_km} km
                      </div>
                      <div>{a.remaining_minutes} min remaining</div>
                      <div>Destination: {a.hospital?.name}</div>
                    </div>
                  ) : (
                    <div className="popup-row">{PHASE_LABEL[a.phase] || a.phase}</div>
                  )}
                </Popup>
              </Marker>
            </Fragment>
          );
        })}
      </MapContainer>

      <p className="map-hint">
        Click anywhere on the map to place the patient. Swipe or drag to pan,
        pinch to zoom.
      </p>
    </div>
  );
}
