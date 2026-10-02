import { describe, expect, it } from "vitest";

import { fromEditorHtml, hasRichContent, looksLikeHtml, toEditorHtml } from "./richDefinition";

describe("richDefinition", () => {
  it("detects editor HTML vs plain text", () => {
    expect(looksLikeHtml("<p>Hi</p>")).toBe(true);
    expect(looksLikeHtml("Score > 5 wins")).toBe(false);
    expect(looksLikeHtml("")).toBe(false);
  });

  it("treats an emptied editor as no content, but keeps an image-only body", () => {
    expect(hasRichContent("<p></p>")).toBe(false);
    expect(hasRichContent("   ")).toBe(false);
    expect(hasRichContent('<p><img src="https://x/y.png"></p>')).toBe(true);
    expect(hasRichContent("Plain instructions")).toBe(true);
  });

  it("turns plain-text lines into paragraphs for the editor, escaping markup", () => {
    expect(toEditorHtml("Read all\nA < B")).toBe("<p>Read all</p><p>A &lt; B</p>");
    expect(toEditorHtml("<p>Already HTML</p>")).toBe("<p>Already HTML</p>");
    expect(toEditorHtml(null)).toBe("");
  });

  it("saves an empty editor as an empty string", () => {
    expect(fromEditorHtml("<p></p>")).toBe("");
    expect(fromEditorHtml("<p>Text</p>")).toBe("<p>Text</p>");
  });
});
