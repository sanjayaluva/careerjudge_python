/**
 * D3/audit — Assessment navigation-rule enforcement, shared by
 * SessionPlayerPage's "Previous" button and its section/question sidebar.
 *
 * Rules per specs/03_assessment_configuration.json §5.4.1:
 *   - FREE:                 no restriction — candidate can revisit any
 *                            already-delivered question in any direction.
 *   - PREV_SECTION:         backward navigation may reach the section
 *                            immediately preceding the candidate's current
 *                            section, but no further back than that.
 *   - NO_BACKWARD_SECTION:  backward navigation may not cross a section
 *                            boundary at all (within-section backward is
 *                            still allowed).
 *   - NO_BACKWARD_QUESTION: no backward navigation whatsoever.
 *
 * Forward navigation is never restricted by this helper — none of the four
 * modes limit moving on to an already-delivered question ahead of the
 * candidate's current position.
 *
 * Kept as a pure function (no React/DOM) so it can be unit tested directly
 * instead of only indirectly through the full player component.
 */

export type NavigationRule =
  "FREE" | "PREV_SECTION" | "NO_BACKWARD_SECTION" | "NO_BACKWARD_QUESTION" | string;

/** Section ids in delivery order, first occurrence wins (matches the order
 * questions are delivered in — see SessionPlayerPage's `sectionEntries`). */
export function sectionDeliveryOrder(sections: (number | null)[]): (number | null)[] {
  const order: (number | null)[] = [];
  for (const s of sections) {
    if (!order.includes(s)) order.push(s);
  }
  return order;
}

/**
 * Whether the candidate may navigate backward from `currentSection` to
 * `targetSection`, given the assessment's navigation rule and the
 * section delivery order.
 */
export function canNavigateBackToSection(
  navigationRule: NavigationRule | null | undefined,
  sectionOrder: (number | null)[],
  currentSection: number | null,
  targetSection: number | null,
): boolean {
  const rule = navigationRule ?? "FREE";

  if (rule === "NO_BACKWARD_QUESTION") return false; // no backward movement at all

  if (targetSection === currentSection) return true; // same section, always allowed

  if (rule === "NO_BACKWARD_SECTION") return false;

  if (rule === "PREV_SECTION") {
    const currentPos = sectionOrder.indexOf(currentSection);
    const targetPos = sectionOrder.indexOf(targetSection);
    if (currentPos === -1 || targetPos === -1) return false;
    // Only the immediately preceding section is reachable.
    return currentPos - targetPos === 1;
  }

  return true; // FREE (and any unrecognized rule defaults to unrestricted)
}
