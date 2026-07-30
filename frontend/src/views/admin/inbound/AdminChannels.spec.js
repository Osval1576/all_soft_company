import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

vi.mock("../../../api/inbound.api", () => ({
  listChannelAccounts: vi.fn(),
  createChannelAccount: vi.fn(),
  updateChannelAccount: vi.fn(),
  deleteChannelAccount: vi.fn(),
}));

const pushToast = vi.fn();
vi.mock("../../../stores/notifications.store", () => ({
  useNotificationsStore: () => ({ pushToast }),
}));

import AdminChannels from "./AdminChannels.vue";
import * as api from "../../../api/inbound.api";

const mountPage = () =>
  mount(AdminChannels, { attachTo: document.body, global: { stubs: { AppTopBar: true } } });

describe("AdminChannels", () => {
  beforeEach(() => vi.clearAllMocks());

  it("muestra el estado vacío y los 5 canales", async () => {
    api.listChannelAccounts.mockResolvedValue([]);
    const w = mountPage();
    await flushPromises();
    expect(w.find(".empty").exists()).toBe(true);
    const opts = w.findAll("select option").map((o) => o.element.value);
    expect(opts).toEqual(["whatsapp", "email", "widget", "messenger", "instagram"]);
    w.unmount();
  });

  it("el label del identificador cambia según el canal", async () => {
    api.listChannelAccounts.mockResolvedValue([]);
    const w = mountPage();
    await flushPromises();
    expect(w.find(".field--grow .field-label").text().toLowerCase()).toContain("phone number");
    await w.find("select").setValue("widget");
    expect(w.find(".field--grow .field-label").text().toLowerCase()).toContain("clave");
    w.unmount();
  });

  it("crea una cuenta y recarga la lista", async () => {
    api.listChannelAccounts
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 1, channel: "whatsapp", external_id: "123", is_active: true }]);
    api.createChannelAccount.mockResolvedValue({});
    const w = mountPage();
    await flushPromises();
    await w.find(".field--grow input").setValue("123");
    await w.find("form.add").trigger("submit");
    await flushPromises();
    expect(api.createChannelAccount).toHaveBeenCalledWith({
      channel: "whatsapp", external_id: "123", is_active: true,
    });
    expect(w.findAll(".row")).toHaveLength(1);
    w.unmount();
  });

  it("togglea el estado activo con PATCH", async () => {
    api.listChannelAccounts.mockResolvedValue([
      { id: 7, channel: "whatsapp", external_id: "123", is_active: true },
    ]);
    api.updateChannelAccount.mockResolvedValue({});
    const w = mountPage();
    await flushPromises();
    await w.find(".switch input").trigger("change");
    await flushPromises();
    expect(api.updateChannelAccount).toHaveBeenCalledWith(7, { is_active: false });
    expect(w.find(".switch-label").text()).toBe("Inactivo");
    w.unmount();
  });

  // Regresión del bug encontrado en la verificación en vivo (#24): el listener
  // global de "click afuera para cancelar" se disparaba en el MISMO click que
  // armaba la confirmación (burbujeo al document), y el borrado nunca corría.
  // El fix es @click.stop; este test falla si alguien lo quita.
  it("requiere dos clicks para eliminar (no borra en el primero)", async () => {
    api.listChannelAccounts.mockResolvedValue([
      { id: 9, channel: "email", external_id: "s@e.com", is_active: true },
    ]);
    api.deleteChannelAccount.mockResolvedValue();
    const w = mountPage();
    await flushPromises();

    await w.find(".row-del").trigger("click"); // arma
    expect(api.deleteChannelAccount).not.toHaveBeenCalled();
    expect(w.find(".row-del").text()).toContain("¿Eliminar?");

    await w.find(".row-del").trigger("click"); // confirma
    await flushPromises();
    expect(api.deleteChannelAccount).toHaveBeenCalledWith(9);
    expect(w.findAll(".row")).toHaveLength(0);
    w.unmount();
  });
});
