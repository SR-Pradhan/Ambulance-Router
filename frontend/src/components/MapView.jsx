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

// What every mark on the map means.
//
// Without this a visitor sees green circles, red dashed circles, and two shades
// of ambulance with nothing explaining any of it. Each entry names the mark AND
// describes it in words, so the meaning never rests on colour alone.
function Legend({ movingCount }) {
  return (
    <div className="legend" aria-label="Map legend">
      <div className="legend-row">
        <span className="legend-mark"><span className="pin is-open">🏥</span></span>
        <span>Accepting patients</span>
      </div>
      <div className="legend-row">
        <span className="legend-mark"><span className="pin is-full">🏥</span></span>
        <span>Full, excluded from dispatch</span>
      </div>
      <div className="legend-row">
        <span className="legend-mark"><span className="pin is-active">🚑</span></span>
        <span>Ambulance en route</span>
      </div>
      <div className="legend-row">
        <span className="legend-mark"><span className="pin is-idle">🚑</span></span>
        <span>Ambulance available</span>
      </div>
      <div className="legend-row">
        <span className="legend-mark"><span className="pin is-patient">📍</span></span>
        <span>Patient</span>
      </div>
      <div className="legend-divider" />
      <div className="legend-row">
        <span className="legend-line to-patient" />
        <span>Driving to patient</span>
      </div>
      <div className="legend-row">
        <span className="legend-line to-hospital" />
        <span>Carrying to hospital</span>
      </div>
      <div className="legend-row">
        <span className="legend-line off-network" />
        <span>Last stretch, not routed</span>
      </div>
      <div className="legend-live">
        <span className={`live-dot ${movingCount > 0 ? "is-live" : ""}`} />
        {movingCount > 0
          ? `${movingCount} moving, updating every 2s`
          : "No ambulance moving"}
      </div>
    </div>
  );
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
  // Centre of the real road network (part of Gurugram).
  const center = [28.4632, 77.035];

  return (
    <div className="map-wrap">
      <div className="map-stage">
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
              {/* TWO polylines, not one.
                  The journey has two legs with different meanings: driving to
                  the patient, then carrying them to hospital. Drawing the whole
                  path in a single colour chosen by the CURRENT phase repainted
                  the pickup leg blue the moment the patient was collected,
                  contradicting the legend. Splitting at the patient keeps each
                  leg the colour the legend claims, for the whole journey. */}
              {moving && a.route?.length > 1 && (
                <>
                  {a.route.slice(0, (a.pickup_index ?? 0) + 1).length > 1 && (
                    <Polyline
                      positions={a.route
                        .slice(0, (a.pickup_index ?? 0) + 1)
                        .map((p) => [p.lat, p.lng])}
                      pathOptions={{
                        color: "#ef6c00",
                        weight: 4,
                        /* The leg not currently being driven is faded, so the
                           active one reads at a glance. */
                        opacity: a.phase === "to_patient" ? 0.85 : 0.3,
                      }}
                    />
                  )}
                  {a.route.slice(a.pickup_index ?? 0).length > 1 && (
                    <Polyline
                      positions={a.route
                        .slice(a.pickup_index ?? 0)
                        .map((p) => [p.lat, p.lng])}
                      pathOptions={{
                        color: "#1565c0",
                        weight: 4,
                        opacity: a.phase === "to_patient" ? 0.3 : 0.85,
                      }}
                    />
                  )}
                  {/* The last stretch, which the model does NOT route.
                      Patients and hospitals sit at real addresses; the graph
                      holds only road junctions, and only arterial ones, so the
                      nearest junction to a patient can be a few hundred metres
                      away. Drawing that gap dashed is the honest presentation:
                      it shows where routing stops and the unmodelled part
                      begins, instead of leaving the line to end in mid-air
                      looking like a bug. Navigation apps do the same when a
                      destination sits off the road network. */}
                  {a.patient && a.route[a.pickup_index ?? 0] && (
                    <Polyline
                      positions={[
                        [a.route[a.pickup_index ?? 0].lat,
                         a.route[a.pickup_index ?? 0].lng],
                        [a.patient.lat, a.patient.lng],
                      ]}
                      pathOptions={{
                        color: "#9ca3af", weight: 2,
                        opacity: 0.9, dashArray: "4 6",
                      }}
                    />
                  )}
                  {a.hospital && a.route.length > 0 && (
                    <Polyline
                      positions={[
                        [a.route[a.route.length - 1].lat,
                         a.route[a.route.length - 1].lng],
                        [a.hospital.lat, a.hospital.lng],
                      ]}
                      pathOptions={{
                        color: "#9ca3af", weight: 2,
                        opacity: 0.9, dashArray: "4 6",
                      }}
                    />
                  )}
                </>
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

      <Legend movingCount={live.filter((a) => a.request_id !== null).length} />
      </div>

      <p className="map-hint">
        Click anywhere on the map to place the patient. Swipe or drag to pan,
        pinch to zoom.
      </p>
    </div>
  );
}
