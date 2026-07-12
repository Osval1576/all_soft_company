import axios from "axios";

// Base de la API. En dev, el backend corre aparte en :8000.
// En el build de producción (same-origin detrás de Nginx) se define
// VITE_API_BASE="" y todas las llamadas quedan relativas al mismo dominio.
const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export const http = axios.create({
  baseURL: base,
  withCredentials: true,
});
