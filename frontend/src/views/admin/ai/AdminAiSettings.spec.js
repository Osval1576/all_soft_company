import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

vi.mock("../../../api/ai.api", () => ({
  getAiSettings: vi.fn(),
  updateAiSettings: vi.fn(),
}));

const pushToast = vi.fn();
vi.mock("../../../stores/notifications.store", () => ({
  useNotificationsStore: () => ({ pushToast }),
}));

import AdminAiSettings from "./AdminAiSettings.vue";
import * as api from "../../../api/ai.api";

const SETTINGS = {
  enabled: true,
  rate_limit_per_min: 30,
  public_rate_limit_per_hour: 60,
  monthly_budget_usd: "5.00",
  current_month_cost_usd: "1.25",
};

const mountPage = () =>
  mount(AdminAiSettings, { attachTo: document.body, global: { stubs: { AppTopBar: true } } });

describe("AdminAiSettings", () => {
  beforeEach(() => vi.clearAllMocks());

  it("carga la config desde GET y la refleja en el form", async () => {
    api.getAiSettings.mockResolvedValue({ ...SETTINGS });
    const w = mountPage();
    await flushPromises();
    expect(w.find('input[type="checkbox"]').element.checked).toBe(true);
    const nums = w.findAll('input[type="number"]').map((i) => i.element.value);
    expect(nums).toEqual(["30", "60", "5.00"]);
    expect(w.find(".spend strong").text()).toBe("$1.25");
    w.unmount();
  });

  it("muestra el medidor con el % gastado cuando hay presupuesto", async () => {
    api.getAiSettings.mockResolvedValue({ ...SETTINGS }); // 1.25 / 5.00 = 25%
    const w = mountPage();
    await flushPromises();
    const fill = w.find(".meter-fill");
    expect(fill.exists()).toBe(true);
    expect(fill.attributes("style")).toContain("width: 25%");
    expect(fill.classes()).not.toContain("over");
    w.unmount();
  });

  it("marca el medidor 'over' y lo tope a 100% cuando se pasó del presupuesto", async () => {
    api.getAiSettings.mockResolvedValue({
      ...SETTINGS, monthly_budget_usd: "5.00", current_month_cost_usd: "10.00",
    });
    const w = mountPage();
    await flushPromises();
    const fill = w.find(".meter-fill");
    expect(fill.classes()).toContain("over");
    expect(fill.attributes("style")).toContain("width: 100%");
    w.unmount();
  });

  it("sin presupuesto (0) no muestra medidor", async () => {
    api.getAiSettings.mockResolvedValue({ ...SETTINGS, monthly_budget_usd: "0" });
    const w = mountPage();
    await flushPromises();
    expect(w.find(".meter").exists()).toBe(false);
    w.unmount();
  });

  it("guardar envía los cuatro campos y muestra confirmación", async () => {
    api.getAiSettings.mockResolvedValue({ ...SETTINGS });
    api.updateAiSettings.mockResolvedValue({ ...SETTINGS, monthly_budget_usd: "8.00" });
    const w = mountPage();
    await flushPromises();

    const budgetInput = w.findAll('input[type="number"]')[2];
    await budgetInput.setValue("8");
    await w.find(".btn").trigger("click");
    await flushPromises();

    expect(api.updateAiSettings).toHaveBeenCalledWith({
      enabled: true,
      rate_limit_per_min: 30,
      public_rate_limit_per_hour: 60,
      monthly_budget_usd: 8,
    });
    expect(w.find(".saved").exists()).toBe(true);
    w.unmount();
  });
});
