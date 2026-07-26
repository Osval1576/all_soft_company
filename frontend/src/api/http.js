import axios from "axios";

// Base de la API. En dev, el backend corre aparte en :8000.
// En el build de producción (same-origin detrás de Nginx) se define
// VITE_API_BASE="" y todas las llamadas quedan relativas al mismo dominio.
const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export const http = axios.create({
  baseURL: base,
  withCredentials: true,
});

// Host para WebSockets, derivado del mismo origen que la API: en dev apunta al
// backend (:8000, distinto puerto que Vite), en prod (base="") queda
// same-origin detrás de Nginx. Se puede forzar con VITE_WS_HOST.
export function wsHost() {
  return import.meta.env.VITE_WS_HOST || (base ? new URL(base).host : window.location.host);
}
