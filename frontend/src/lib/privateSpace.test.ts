import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "@/stores/auth";

import { getPrivateOrgId, setPrivateOrgId, withPrivateOwner } from "./privateSpace";

function signInAs(id: number) {
  useAuthStore.getState().login({
    access: "a",
    refresh: "r",
    user: {
      id,
      email: `u${id}@example.com`,
      full_name: "U",
      role: "corp_exclusive",
      is_email_verified: true,
      is_superuser: false,
      is_staff: false,
    },
  });
}

describe("privateSpace (Report 9 #39-#47)", () => {
  beforeEach(() => signInAs(1));
  afterEach(() => {
    setPrivateOrgId(null);
    useAuthStore.getState().clear();
  });

  it("leaves payloads alone when no organization was picked", () => {
    expect(getPrivateOrgId()).toBeNull();
    expect(withPrivateOwner({ title: "A" })).toEqual({ title: "A" });
  });

  it("adds the picked organization to new content", () => {
    setPrivateOrgId(7);
    expect(getPrivateOrgId()).toBe(7);
    expect(withPrivateOwner({ title: "A" })).toEqual({ title: "A", owner_organization: 7 });
  });

  it("never sends one user's choice for another user on the same browser", () => {
    setPrivateOrgId(7);
    signInAs(2);
    expect(getPrivateOrgId()).toBeNull();
    expect(withPrivateOwner({ title: "A" })).toEqual({ title: "A" });
  });

  it("forgets the choice on logout", () => {
    setPrivateOrgId(7);
    useAuthStore.getState().clear();
    signInAs(1);
    expect(getPrivateOrgId()).toBeNull();
  });
});
