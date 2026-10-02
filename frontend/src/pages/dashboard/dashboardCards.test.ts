import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "@/lib/constants";

import { dashboardCardLabel, orderDashboardModules } from "./dashboardCards";

describe("dashboard cards (Report 9 #82)", () => {
  it("labels and orders the individual's cards as the client asked", () => {
    const cards = orderDashboardModules(
      "individual",
      NAV_ITEMS.filter(
        (i) => i.key !== "dashboard" && i.key !== "profile" && i.roles.includes("individual"),
      ),
    );
    expect(cards.slice(0, 5).map((c) => dashboardCardLabel("individual", c.key))).toEqual([
      "My Assessments",
      "My Profiling Solutions",
      "My Reports",
      "My Training Courses",
      "My Counselling Sessions",
    ]);
  });

  it("leaves other roles' labels and order unchanged", () => {
    expect(dashboardCardLabel("trainer", "training")).toBe("Training");
    expect(dashboardCardLabel("corp_admin", "assessments")).toBe("Assessments");
    const items = NAV_ITEMS.filter((i) => i.roles.includes("cj_admin"));
    expect(orderDashboardModules("cj_admin", items)).toBe(items);
  });
});
