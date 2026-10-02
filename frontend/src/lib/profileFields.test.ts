import { describe, expect, it } from "vitest";

import { expertiseList, getRoleSpecificFields, nameWithExpertise } from "./profileFields";

describe("domains of expertise (Report 9 #66-#69)", () => {
  it("is a profile field for SMEs and Reviewers only", () => {
    const has = (role: Parameters<typeof getRoleSpecificFields>[0]) =>
      getRoleSpecificFields(role).some((f) => f.name === "domains_of_expertise");
    expect(has("sme")).toBe(true);
    expect(has("reviewer")).toBe(true);
    expect(has("psychometrician")).toBe(false);
    expect(has("trainer")).toBe(false);
  });

  it("reads a list or comma-separated text", () => {
    expect(expertiseList(["Quant", "", "Verbal"])).toEqual(["Quant", "Verbal"]);
    expect(expertiseList(" Quant , Verbal,")).toEqual(["Quant", "Verbal"]);
    expect(expertiseList(null)).toEqual([]);
  });

  it("labels picker options with the domains", () => {
    expect(nameWithExpertise("Asha", ["Quant", "Verbal"])).toBe("Asha — Quant, Verbal");
    expect(nameWithExpertise("Asha", [])).toBe("Asha");
  });
});
