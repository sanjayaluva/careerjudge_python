/**
 * MediaPlayer — one player for course media, whatever the source (SRS §2.3.1).
 *
 * Uploaded files and direct media URLs play in a native <video>/<audio>
 * element. YouTube links cannot play in a native element (the browser gets
 * an HTML page, not a media stream — the player just sits at 0:00), so they
 * are rendered through the YouTube IFrame Player API instead.
 *
 * Both paths expose the same imperative handle (current time, duration,
 * seek, play, pause) and the same callbacks, so the Timeliner editor and the
 * interactive player work identically for uploads and YouTube links.
 */
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export interface MediaPlayerHandle {
  getCurrentTime(): number;
  getDuration(): number;
  seekTo(seconds: number): void;
  play(): void;
  pause(): void;
}

interface MediaPlayerProps {
  src: string;
  kind: "video" | "audio";
  onTimeUpdate?: (seconds: number) => void;
  onDurationChange?: (seconds: number) => void;
  onEnded?: () => void;
  className?: string;
}

const YT_ID = /^[A-Za-z0-9_-]{11}$/;

/** Extract the 11-char video id from any common YouTube URL form, else null. */
export function parseYouTubeId(url: string): string | null {
  let u: URL;
  try {
    u = new URL(url.trim());
  } catch {
    return null;
  }
  const host = u.hostname.replace(/^(www|m|music)\./, "");
  let id: string | null = null;
  if (host === "youtu.be") {
    id = u.pathname.split("/")[1] ?? null;
  } else if (host === "youtube.com" || host === "youtube-nocookie.com") {
    if (u.pathname === "/watch") {
      id = u.searchParams.get("v");
    } else {
      const m = u.pathname.match(/^\/(embed|shorts|live|v)\/([^/?#]+)/);
      id = m ? m[2] : null;
    }
  }
  return id && YT_ID.test(id) ? id : null;
}

// --- YouTube IFrame API (loaded once, on first use) --------------------------

interface YTPlayer {
  getCurrentTime(): number;
  getDuration(): number;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  playVideo(): void;
  pauseVideo(): void;
  destroy(): void;
}

interface YTNamespace {
  Player: new (
    el: HTMLElement,
    opts: {
      videoId: string;
      width?: string;
      height?: string;
      playerVars?: Record<string, number | string>;
      events?: {
        onReady?: () => void;
        onStateChange?: (e: { data: number }) => void;
      };
    },
  ) => YTPlayer;
}

declare global {
  interface Window {
    YT?: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let ytApiPromise: Promise<YTNamespace> | null = null;

function loadYouTubeApi(): Promise<YTNamespace> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (!ytApiPromise) {
    ytApiPromise = new Promise((resolve) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prev?.();
        resolve(window.YT as YTNamespace);
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    });
  }
  return ytApiPromise;
}

const YT_ENDED = 0;

// -----------------------------------------------------------------------------

export const MediaPlayer = forwardRef<MediaPlayerHandle, MediaPlayerProps>(function MediaPlayer(
  { src, kind, onTimeUpdate, onDurationChange, onEnded, className },
  ref,
) {
  const youTubeId = parseYouTubeId(src);
  const nativeRef = useRef<HTMLVideoElement & HTMLAudioElement>(null);
  const ytHostRef = useRef<HTMLDivElement>(null);
  const ytPlayerRef = useRef<YTPlayer | null>(null);

  // Keep the latest callbacks without re-creating the YouTube player.
  const cb = useRef({ onTimeUpdate, onDurationChange, onEnded });
  cb.current = { onTimeUpdate, onDurationChange, onEnded };

  useImperativeHandle(
    ref,
    () => ({
      getCurrentTime: () =>
        youTubeId
          ? (ytPlayerRef.current?.getCurrentTime() ?? 0)
          : (nativeRef.current?.currentTime ?? 0),
      getDuration: () =>
        youTubeId ? (ytPlayerRef.current?.getDuration() ?? 0) : (nativeRef.current?.duration ?? 0),
      seekTo: (s) => {
        if (youTubeId) ytPlayerRef.current?.seekTo(s, true);
        else if (nativeRef.current) nativeRef.current.currentTime = s;
        cb.current.onTimeUpdate?.(s);
      },
      play: () => {
        if (youTubeId) ytPlayerRef.current?.playVideo();
        else void nativeRef.current?.play();
      },
      pause: () => {
        if (youTubeId) ytPlayerRef.current?.pauseVideo();
        else nativeRef.current?.pause();
      },
    }),
    [youTubeId],
  );

  useEffect(() => {
    if (!youTubeId || !ytHostRef.current) return;
    let cancelled = false;
    let poll: number | undefined;
    const mount = document.createElement("div");
    ytHostRef.current.appendChild(mount);

    void loadYouTubeApi().then((YT) => {
      if (cancelled) return;
      ytPlayerRef.current = new YT.Player(mount, {
        videoId: youTubeId,
        width: "100%",
        height: "100%",
        playerVars: { rel: 0, modestbranding: 1, playsinline: 1 },
        events: {
          onReady: () => {
            let lastDuration = 0;
            // The IFrame API has no timeupdate event — poll instead.
            poll = window.setInterval(() => {
              const p = ytPlayerRef.current;
              if (!p) return;
              const d = p.getDuration();
              if (d && d !== lastDuration) {
                lastDuration = d;
                cb.current.onDurationChange?.(d);
              }
              cb.current.onTimeUpdate?.(p.getCurrentTime());
            }, 250);
          },
          onStateChange: (e) => {
            if (e.data === YT_ENDED) cb.current.onEnded?.();
          },
        },
      });
    });

    return () => {
      cancelled = true;
      if (poll) window.clearInterval(poll);
      ytPlayerRef.current?.destroy();
      ytPlayerRef.current = null;
      mount.remove();
    };
  }, [youTubeId]);

  if (youTubeId) {
    return (
      <div
        ref={ytHostRef}
        className={`aspect-video w-full overflow-hidden rounded-md border border-slate-200 bg-black ${className ?? ""}`}
        data-testid="youtube-player"
      />
    );
  }

  const common = {
    ref: nativeRef,
    src,
    controls: true,
    onTimeUpdate: (e: React.SyntheticEvent<HTMLMediaElement>) =>
      onTimeUpdate?.(e.currentTarget.currentTime),
    onLoadedMetadata: (e: React.SyntheticEvent<HTMLMediaElement>) =>
      onDurationChange?.(e.currentTarget.duration),
    onEnded: () => onEnded?.(),
  };

  return kind === "audio" ? (
    <audio {...common} className={`w-full ${className ?? ""}`}>
      Your browser does not support audio playback.
    </audio>
  ) : (
    <video {...common} className={`w-full rounded-md border border-slate-200 ${className ?? ""}`} />
  );
});
