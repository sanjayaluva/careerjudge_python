/**
 * FlashPresentation — simulates the delivery-time flash question experience.
 *
 * Used in the QuestionDetailPage Preview tab to show how the candidate will
 * experience flash question types (1e, 1f, 2c, 2d) at assessment time:
 *
 *   Phase 1: Flash items appear one-by-one (each for flash_interval_ms)
 *   Phase 2: Question text + options appear (flash items hidden)
 *
 * Controls:
 *   - "Start flash presentation" button
 *   - "Skip" button to jump to question phase
 *   - "Replay" button after completion
 *
 * This is a SIMULATION for preview purposes only. The actual assessment
 * player (Phase 2 assessment module) will have the full delivery-time
 * experience with scoring, fullscreen lock, etc.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";

interface FlashItem {
  id: number;
  item_type: string;
  text_value: string;
  image_file: string | null;
  is_in_display_pool?: boolean;
}

interface FlashPresentationProps {
  flashItems: FlashItem[];
  flashIntervalMs: number | null;
  flashDisplayCount: number | null;
  flashOrder?: string;
  /** The question content to show after flashing completes */
  children: React.ReactNode;
}

type Phase = "idle" | "flashing" | "question";

/** Fisher-Yates shuffle for randomizing flash items. */
function shuffle<T>(array: T[]): T[] {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function FlashPresentation({
  flashItems,
  flashIntervalMs,
  flashDisplayCount,
  flashOrder = "SEQUENCE",
  children,
}: FlashPresentationProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [shuffledItems, setShuffledItems] = useState<FlashItem[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Determine which items to show (respect flashDisplayCount if set)
  const pool = flashItems.filter((fi) => fi.is_in_display_pool !== false);
  const baseItems =
    flashDisplayCount && flashDisplayCount > 0
      ? pool.slice(0, Math.min(flashDisplayCount, pool.length))
      : pool;

  // Use shuffled items if RANDOM, otherwise use baseItems
  const itemsToShow =
    flashOrder === "RANDOM" && shuffledItems.length > 0 ? shuffledItems : baseItems;

  const interval = flashIntervalMs && flashIntervalMs > 0 ? flashIntervalMs : 800;

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    // Shuffle items if flash_order is RANDOM
    if (flashOrder === "RANDOM") {
      setShuffledItems(shuffle(baseItems));
    } else {
      setShuffledItems([]);
    }
    setCurrentIndex(0);
    setPhase("flashing");
  }, [stop, flashOrder, baseItems]);

  const skip = useCallback(() => {
    stop();
    setPhase("question");
  }, [stop]);

  const replay = useCallback(() => {
    start();
  }, [start]);

  // Advance through flash items
  useEffect(() => {
    if (phase !== "flashing") return;

    if (currentIndex >= itemsToShow.length) {
      // All items flashed — show the question
      setPhase("question");
      return;
    }

    // Show current item for `interval` ms, then advance
    timerRef.current = setTimeout(() => {
      setCurrentIndex((i) => i + 1);
    }, interval);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [phase, currentIndex, itemsToShow.length, interval]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (itemsToShow.length === 0) {
    return <>{children}</>;
  }

  return (
    <div>
      {/* Controls */}
      <div className="mb-4 flex items-center gap-2">
        {phase === "idle" && (
          <Button type="button" size="sm" onClick={start}>
            ▶ Start flash presentation
          </Button>
        )}
        {phase === "flashing" && (
          <>
            <span className="text-xs text-slate-500">
              Flashing item {currentIndex + 1} of {itemsToShow.length}…
            </span>
            <Button type="button" variant="outline" size="sm" onClick={skip}>
              ⏭ Skip to question
            </Button>
          </>
        )}
        {phase === "question" && (
          <Button type="button" variant="outline" size="sm" onClick={replay}>
            ↻ Replay flash
          </Button>
        )}
      </div>

      {/* Phase 1: Flashing items */}
      {phase === "flashing" && (
        <div className="mb-4 flex min-h-[200px] items-center justify-center rounded-lg border-2 border-amber-300 bg-amber-50 p-8">
          {currentIndex < itemsToShow.length ? (
            <div key={currentIndex} className="text-center">
              {itemsToShow[currentIndex].item_type === "IMAGE" &&
              itemsToShow[currentIndex].image_file ? (
                <img
                  src={itemsToShow[currentIndex].image_file!}
                  alt={`Flash ${currentIndex + 1}`}
                  className="mx-auto max-h-40 max-w-xs"
                />
              ) : (
                <span className="text-4xl font-bold text-slate-900">
                  {itemsToShow[currentIndex].text_value || "(empty)"}
                </span>
              )}
              <p className="mt-4 text-xs text-amber-700">
                Item {currentIndex + 1} / {itemsToShow.length}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Loading question…</p>
          )}
        </div>
      )}

      {/* Phase 2: Question + options (shown after flashing completes or if idle/question) */}
      {phase === "question" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Question (shown after flash items)
          </p>
          {children}
        </div>
      )}

      {/* Idle state — show a hint */}
      {phase === "idle" && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">
            Click "Start flash presentation" to simulate the candidate experience. Items will flash
            one by one ({interval}ms each), then the question will appear.
          </p>
        </div>
      )}
    </div>
  );
}
