import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  * { box-sizing: border-box; }
  body { margin: 0; background: #F1F3F0; }
  a { color: inherit; }
  button, input, select, textarea { font-family: inherit; }

  /* Accessibility floor: visible keyboard focus, styled in Harbor, everywhere. */
  :focus-visible { outline: 2px solid #1F6F78; outline-offset: 2px; border-radius: 4px; }
  button:focus:not(:focus-visible) { outline: none; }

  /* Respect prefers-reduced-motion globally: kill non-essential CSS animation. */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
  }

  @keyframes tp-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
  @media print {
    .tp-noprint { display: none !important; }
    body { background: #fff !important; }
    * { box-shadow: none !important; }
  }
  @media (max-width: 780px) {
    .tp-dash { grid-template-columns: 1fr !important; }
  }
  /* numbered activity markers on the dark map */
  .num-tip { background: transparent !important; border: none !important; box-shadow: none !important;
             color: #F1F3F0 !important; font-weight: 600 !important; }
  .leaflet-popup-content-wrapper { border-radius: 10px; }
  .leaflet-popup-content { font-family: 'Instrument Sans', system-ui, sans-serif; }

  /* Keyless dark-basemap fallback: invert keyless OSM tiles into an Ink-like
     night style (active only when VITE_CARTO_API_KEY is not set). */
  .tp-tiles-filtered .leaflet-tile-pane {
    filter: invert(1) hue-rotate(185deg) brightness(0.92) contrast(0.9) saturate(0.72);
  }
  .tp-tiles-filtered { background: #10151F; }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
