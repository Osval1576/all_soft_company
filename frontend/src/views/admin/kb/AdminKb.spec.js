import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

vi.mock("../../../api/kb.api", () => ({
  listArticles: vi.fn(),
  createArticle: vi.fn(),
  updateArticle: vi.fn(),
  deleteArticle: vi.fn(),
}));

import AdminKb from "./AdminKb.vue";
import * as api from "../../../api/kb.api";

const A = { id: 1, title: "Restablecer contraseña", slug: "restablecer", body: "Pasos A", is_published: true };
const B = { id: 2, title: "Borrador interno", slug: "borrador", body: "Pasos B", is_published: false };

const mountPage = () =>
  mount(AdminKb, { global: { stubs: { AppTopBar: true, RouterLink: true } } });

describe("AdminKb", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it("lista los artículos con su badge publicado/borrador", async () => {
    api.listArticles.mockResolvedValue([A, B]);
    const w = mountPage();
    await flushPromises();
    const items = w.findAll(".list-item");
    expect(items).toHaveLength(2);
    expect(items[0].find(".li-badge").text()).toBe("Publicado");
    expect(items[1].find(".li-badge").text()).toBe("Borrador");
    w.unmount();
  });

  it("'+ Nuevo artículo' abre el editor vacío", async () => {
    api.listArticles.mockResolvedValue([A]);
    const w = mountPage();
    await flushPromises();
    expect(w.find(".editor-empty").exists()).toBe(true);
    await w.find(".btn-new").trigger("click");
    expect(w.find(".editor-empty").exists()).toBe(false);
    expect(w.find("form.form input").element.value).toBe("");
    expect(w.find(".btn-submit").text()).toBe("Crear artículo");
    w.unmount();
  });

  it("seleccionar un artículo llena el editor", async () => {
    api.listArticles.mockResolvedValue([A, B]);
    const w = mountPage();
    await flushPromises();
    await w.findAll(".list-item")[0].trigger("click");
    expect(w.find("form.form input").element.value).toBe("Restablecer contraseña");
    expect(w.find('.field-check input[type="checkbox"]').element.checked).toBe(true);
    expect(w.find(".btn-submit").text()).toBe("Guardar cambios");
    w.unmount();
  });

  it("crea un artículo con title/body/is_published", async () => {
    api.listArticles.mockResolvedValueOnce([]).mockResolvedValueOnce([{ ...A, id: 3, title: "Nuevo" }]);
    api.createArticle.mockResolvedValue({ id: 3 });
    const w = mountPage();
    await flushPromises();
    await w.find(".btn-new").trigger("click");
    await w.find("form.form input").setValue("Nuevo");
    await w.find("form.form textarea").setValue("Cuerpo");
    await w.find("form.form").trigger("submit");
    await flushPromises();
    expect(api.createArticle).toHaveBeenCalledWith({ title: "Nuevo", body: "Cuerpo", is_published: false });
    w.unmount();
  });

  it("actualiza el artículo seleccionado", async () => {
    api.listArticles.mockResolvedValue([A]);
    api.updateArticle.mockResolvedValue({ ...A, title: "Editado" });
    const w = mountPage();
    await flushPromises();
    await w.findAll(".list-item")[0].trigger("click");
    await w.find("form.form input").setValue("Editado");
    await w.find("form.form").trigger("submit");
    await flushPromises();
    expect(api.updateArticle).toHaveBeenCalledWith(1, { title: "Editado", body: "Pasos A", is_published: true });
    w.unmount();
  });

  it("elimina el artículo tras confirmar", async () => {
    api.listArticles.mockResolvedValue([A]);
    api.deleteArticle.mockResolvedValue();
    vi.stubGlobal("confirm", vi.fn(() => true));
    const w = mountPage();
    await flushPromises();
    await w.findAll(".list-item")[0].trigger("click");
    await w.find(".btn-delete").trigger("click");
    await flushPromises();
    expect(api.deleteArticle).toHaveBeenCalledWith(1);
    w.unmount();
  });
});
