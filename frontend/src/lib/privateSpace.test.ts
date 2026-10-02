import { afterEach, describe, expect, it } from "vitest";

import { getPrivateOrgId, setPrivateOrgId, withPrivateOwner } from "./privateSpace";

describe("privateSpace (Report 9 #39-#47)", () => {
  afterEach(() => setPrivateOrgId(null));

  it("leaves payloads alone when no organization was picked", () => {
    expect(getPrivateOrgId()).toBeNull();
    expect(withPrivateOwner({ title: "A" })).toEqual({ title: "A" });
  });

  it("adds the picked organization to new content", () => {
    setPrivateOrgId(7);
    expect(getPrivateOrgId()).toBe(7);
    expect(withPrivateOwner({ title: "A" })).toEqual({ title: "A", owner_organization: 7 });
  });
});
