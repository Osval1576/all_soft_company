import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

vi.mock("../../../api/kb.api", () => ({
  listSuggestions: vi.fn(),
  updateSuggestion: vi.fn(),
  acceptSuggestion: vi.fn(),
  dismissSuggestion: vi.fn(),
}));

const pushToast = vi.fn();
vi.mock("../../../stores/notifications.store", () => ({
  useNotificationsStore: () => ({ pushToast }),
}));

import AdminKbSuggestions from "./AdminKbSuggestions.vue";
import * as api from "../../../api/kb.api";

const SUGGESTION = { id: 3, title: "Cómo reiniciar", body: "Pasos...", status: "pending",
                     source_ticket_ref: "DEMO-1", created_at: "2026-07-29T10:00:00Z" };

const mountPage = () =>
  mount(AdminKbSuggestions, { attachTo: document.body, global: { stubs: { AppTopBar: true } } });

describe("AdminKbSuggestions", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lista las sugerencias pendientes", async () => {
    api.listSuggestions.mockResolvedValue([SUGGESTION]);
    const w = mountPage();
    await flushPromises();
    expect(api.listSuggestions).toHaveBeenCalledWith("pending");
    expect(w.find(".card input").element.value).toBe("Cómo reiniciar");
    expect(w.find(".badge").text()).toBe("DEMO-1");
    w.unmount();
  });

  it("aceptar: persiste las ediciones (PATCH) y luego publica (accept)", async () => {
    api.listSuggestions.mockResolvedValue([SUGGESTION]);
    api.updateSuggestion.mockResolvedValue({});
    api.acceptSuggestion.mockResolvedValue({ article_id: 5 });
    const w = mountPage();
    await flushPromises();

    await w.find(".card input").setValue("Título editado");
    await w.find(".btn-accept").trigger("click");
    await flushPromises();

    expect(api.updateSuggestion).toHaveBeenCalledWith(3, { title: "Título editado", body: "Pasos..." });
    expect(api.acceptSuggestion).toHaveBeenCalledWith(3);
    // updateSuggestion se llamó ANTES que acceptSuggestion (publica lo editado).
    expect(api.updateSuggestion.mock.invocationCallOrder[0])
      .toBeLessThan(api.acceptSuggestion.mock.invocationCallOrder[0]);
    expect(w.findAll(".card")).toHaveLength(0);
    w.unmount();
  });

  // Regresión del mismo bug del confirm en dos pasos (el "Descartar" quedó roto
  // en #23 hasta el fix @click.stop de #24).
  it("descartar requiere dos clicks (no descarta en el primero)", async () => {
    api.listSuggestions.mockResolvedValue([SUGGESTION]);
    api.dismissSuggestion.mockResolvedValue({ status: "dismissed" });
    const w = mountPage();
    await flushPromises();

    await w.find(".btn-dismiss").trigger("click"); // arma
    expect(api.dismissSuggestion).not.toHaveBeenCalled();
    expect(w.find(".btn-dismiss").text()).toContain("¿Descartar?");

    await w.find(".btn-dismiss").trigger("click"); // confirma
    await flushPromises();
    expect(api.dismissSuggestion).toHaveBeenCalledWith(3);
    expect(w.findAll(".card")).toHaveLength(0);
    w.unmount();
  });
});
