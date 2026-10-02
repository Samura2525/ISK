import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import App from "./App";

const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
