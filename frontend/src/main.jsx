import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// Leaflet's own stylesheet must be imported or the map renders as a broken
// grey box with misplaced tiles. It is the single most common Leaflet setup
// mistake, so it is imported here at the entry point where it is obvious.
import "leaflet/dist/leaflet.css";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
