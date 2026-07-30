import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

// Tests de componentes (Vitest + @vue/test-utils + jsdom). Corren en jsdom para
// poder simular clicks reales que burbujean al document (clave para los tests de
// confirmación en dos pasos, donde un listener global cancela el estado armado).
export default defineConfig({
  plugins: [vue()],
  test: {
    // happy-dom en vez de jsdom: jsdom es tan pesado que su inicialización en el
    // worker de Vitest no alcanza a responder el handshake sobre un FS lento
    // (Windows + sync), y el worker muere con "Timeout waiting for worker to
    // respond". happy-dom carga en una fracción del tiempo y cubre lo que
    // necesitan estos tests (mount, eventos que burbujean al document).
    environment: "happy-dom",
    globals: true,
    include: ["src/**/*.spec.js"],
    pool: "threads",
    fileParallelism: false,
    maxWorkers: 1,
    minWorkers: 1,
  },
});
