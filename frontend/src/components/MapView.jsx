import { Fragment, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

// Leaflet's default marker icons are loaded from relative image paths that
// break under a bundler (the classic "markers are invisible" bug). Using
// divIcon with inline HTML sidesteps the whole asset problem and makes each
// marker type instantly distinguishable on the map.
function emojiIcon(emoji, color) {
  return L.divIcon({
    className: "emoji-marker",
    html: `<div class="pin" style="border-color:${color}">${emoji}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
}

const HOSPITAL_OPEN = emojiIcon("🏥", "#2e7d32");
const HOSPITAL_FULL = emojiIcon("🏥", "#c62828");
const AMBULANCE = emojiIcon("🚑", "#1565c0");
const AMBULANCE_IDLE = emojiIcon("🚑", "#9e9e9e");
const PATIENT = emojiIcon("📍", "#ad1457");

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
              <br />
              {h.available_beds} of {h.total_beds} beds free
              <br />
              {h.accepting ? (
                <span className="ok">Accepting patients</span>
              ) : (
                <span className="bad">FULL — excluded from dispatch</span>
              )}
            </Popup>
          </Marker>
        ))}

        {/* The patient pin */}
        {patient && (
          <Marker position={[patient.lat, patient.lng]} icon={PATIENT}>
            <Popup>
              Patient
              <br />
              {patient.lat.toFixed(5)}, {patient.lng.toFixed(5)}
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
                  <br />
                  {moving ? (
                    <>
                      {a.phase.replace("_", " ")} — {a.progress_percent}%
                      <br />
                      {a.travelled_km} / {a.total_km} km
                      <br />
                      {a.remaining_minutes} min remaining
                      <br />→ {a.hospital?.name}
                    </>
                  ) : (
                    a.phase
                  )}
                </Popup>
              </Marker>
            </Fragment>
          );
        })}
      </MapContainer>

      <p className="map-hint">
        Click anywhere on the map to place the patient, then create a request.
        Two-finger swipe or drag to pan · pinch to zoom.
      </p>
    </div>
  );
}
