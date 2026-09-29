import { describe, expect, it } from "vitest";

import { parseYouTubeId } from "./MediaPlayer";

describe("parseYouTubeId", () => {
  it.each([
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"],
    ["https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"],
    ["https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["  https://youtu.be/dQw4w9WgXcQ  ", "dQw4w9WgXcQ"],
  ])("extracts the id from %s", (url, id) => {
    expect(parseYouTubeId(url)).toBe(id);
  });

  it.each([
    "https://cdn.example.com/media/clip.mp4",
    "/media/session_media/clip.mp3",
    "data:video/mp4;base64,AAAA",
    "https://www.youtube.com/watch?v=short",
    "https://www.youtube.com/channel/UC123",
    "not a url",
  ])("returns null for non-YouTube or malformed %s", (url) => {
    expect(parseYouTubeId(url)).toBeNull();
  });
});
