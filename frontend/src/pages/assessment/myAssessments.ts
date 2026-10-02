/**
 * Report 9 #72: an individual takes or resumes only the assessments he paid
 * for — or that are free, or licensed to his organization. "My Assessments"
 * holds those (and any he has already begun); the rest are only browsed, with
 * their price and "Pay to take".
 */
import type { Assessment } from "@/api/assessment";

/** True when the candidate may take / resume it now. */
export function isMine(a: Pick<Assessment, "price" | "is_unlocked">, hasSession = false): boolean {
  if (hasSession) return true; // already begun — always resumable / viewable
  if (a.is_unlocked != null) return a.is_unlocked;
  return Number(a.price) <= 0;
}
