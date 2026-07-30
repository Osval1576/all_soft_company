import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

// Estado compartido y mockeable (hoisted para poder usarlo en los factories).
const authState = vi.hoisted(() => ({ user: { username: "tech", role: "AGENT" } }));
const ws = vi.hoisted(() => ({
  status: { value: "connected" }, send: vi.fn(() => true), retry: vi.fn(), close: vi.fn(),
}));
const toast = vi.hoisted(() => vi.fn());

vi.mock("../api/tickets.api", () => ({
  getTicketMessages: vi.fn(() => Promise.resolve([])),
  getTicketEvents: vi.fn(() => Promise.resolve([])),
  uploadAttachment: vi.fn(),
}));
vi.mock("../api/ai.api", () => ({
  draftReply: vi.fn(),
  summarizeTicket: vi.fn(),
  translate: vi.fn(),
}));
vi.mock("../api/http", () => ({ wsHost: () => "localhost:8000" }));
vi.mock("../stores/auth.store", () => ({ useAuthStore: () => authState }));
vi.mock("../stores/notifications.store", () => ({
  useNotificationsStore: () => ({ pushToast: toast, setActiveTicket: vi.fn() }),
}));
vi.mock("../composables/useWsConnection", () => ({ useWsConnection: () => ws }));

import ChatPanel from "./ChatPanel.vue";
import * as ai from "../api/ai.api";

const stubs = {
  TicketEventTimeline: true, MessageAttachment: true, CsatPrompt: true, CsatDisplay: true,
};
const SUGGEST = '[aria-label="Sugerir respuesta con IA"]';

const mountPanel = () => mount(ChatPanel, { props: { ticketId: 1 }, global: { stubs } });

describe("ChatPanel — features de IA", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = { username: "tech", role: "AGENT" };
  });

  it("el agente ve el botón de sugerir respuesta", async () => {
    const w = mountPanel();
    await flushPromises();
    expect(w.find(SUGGEST).exists()).toBe(true);
    w.unmount();
  });

  it("el cliente NO ve los botones de IA", async () => {
    authState.user = { username: "cli", role: "CUSTOMER" };
    const w = mountPanel();
    await flushPromises();
    expect(w.find(SUGGEST).exists()).toBe(false);
    w.unmount();
  });

  it("sugerir inserta el borrador de la IA en el composer", async () => {
    ai.draftReply.mockResolvedValue({ draft: "Hola, probá reiniciar el equipo." });
    const w = mountPanel();
    await flushPromises();
    await w.find(SUGGEST).trigger("click");
    await flushPromises();
    expect(ai.draftReply).toHaveBeenCalledWith(1);
    expect(w.find(".composer-input").element.value).toBe("Hola, probá reiniciar el equipo.");
    w.unmount();
  });

  it("resumir muestra el resumen de la IA", async () => {
    ai.summarizeTicket.mockResolvedValue({ summary: "El cliente no puede entrar; se reseteó la clave." });
    const w = mountPanel();
    await flushPromises();
    await w.find('[aria-label="Resumir el hilo con IA"]').trigger("click");
    await flushPromises();
    expect(w.find(".ai-summary-body").text()).toBe("El cliente no puede entrar; se reseteó la clave.");
    w.unmount();
  });

  it("traducir reemplaza el texto del composer", async () => {
    ai.translate.mockResolvedValue({ translated: "Hello, please restart." });
    const w = mountPanel();
    await flushPromises();
    await w.find(".composer-input").setValue("Hola, reiniciá.");
    await w.find('[aria-label="Traducir el mensaje"]').trigger("click");
    await flushPromises();
    expect(ai.translate).toHaveBeenCalledWith("Hola, reiniciá.", "en");
    expect(w.find(".composer-input").element.value).toBe("Hello, please restart.");
    w.unmount();
  });

  it("si el plan no incluye IA, muestra un aviso (upsell) y no rompe", async () => {
    ai.draftReply.mockRejectedValue({ response: { data: { upsell: true } } });
    const w = mountPanel();
    await flushPromises();
    await w.find(SUGGEST).trigger("click");
    await flushPromises();
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ tone: "info" }));
    expect(w.find(".composer-input").element.value).toBe("");
    w.unmount();
  });
});
