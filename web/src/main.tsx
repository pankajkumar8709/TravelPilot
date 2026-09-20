import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  * { box-sizing: border-box; }
  body { margin: 0; }
  a { color: inherit; }
  @keyframes tp-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
  @keyframes tp-pulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.08); opacity: .85; } }
  @media print {
    .tp-noprint { display: none !important; }
    body { background: #fff !important; }
    * { box-shadow: none !important; }
  }
  @media (max-width: 780px) {
    .tp-dash { grid-template-columns: 1fr !important; }
  }
  /* numbered activity markers */
  .num-tip { background: transparent !important; border: none !important; box-shadow: none !important;
             color: #0F1117 !important; font-weight: 700 !important; }
  .leaflet-popup-content-wrapper { border-radius: 10px; }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
