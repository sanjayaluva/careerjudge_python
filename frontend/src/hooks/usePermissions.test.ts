import { describe, expect, it } from "vitest";

import type { ModuleRightGrant } from "@/api/types";

import { canAccessModule } from "./usePermissions";

describe("canAccessModule", () => {
  it("follows the built-in role map", () => {
    expect(canAccessModule("corp_admin", "training")).toBe(true);
    expect(canAccessModule("corp_admin", "users")).toBe(false);
    expect(canAccessModule(null, "dashboard")).toBe(false);
  });

  it("refuses a module switched off for the user's organization (Report 9 #96)", () => {
    expect(canAccessModule("corp_admin", "training", undefined, ["training"])).toBe(false);
    expect(canAccessModule("corp_admin", "reports", undefined, ["reporting"])).toBe(false);
    // Other modules stay available.
    expect(canAccessModule("corp_admin", "assessments", undefined, ["training"])).toBe(true);
  });

  it("gives a custom role the modules it holds rights on", () => {
    const rights: ModuleRightGrant[] = [{ module: "training", action: "view" }];
    expect(canAccessModule("custom_role" as never, "training", rights)).toBe(true);
    expect(canAccessModule("custom_role" as never, "assessments", rights)).toBe(false);
    expect(canAccessModule("custom_role" as never, "training", rights, ["training"])).toBe(false);
  });
});
