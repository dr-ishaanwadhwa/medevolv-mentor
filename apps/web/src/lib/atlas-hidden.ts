/**
 * Hidden structures (hide / restore). The set holds part ids of the model in the scene, in the order they were
 * hidden. It is independent of the selection: hiding clears the selection, and a later selection of a hidden
 * structure brings it back. Pure, so Node tests can import it.
 * Idea adapted from human-atlas-enhanced (MIT, see apps/web/THIRD_PARTY_NOTICES.md).
 */
export function hideParts(hidden: readonly string[], partIds: readonly string[]): string[] {
  const known = new Set(hidden);
  const added = [...new Set(partIds)].filter((id) => !known.has(id));
  return added.length ? [...hidden, ...added] : [...hidden];
}

/** Remove the given parts from the hidden set. Returns the same contents when none of them were hidden. */
export function revealParts(hidden: readonly string[], partIds: readonly string[]): string[] {
  const drop = new Set(partIds);
  return hidden.filter((id) => !drop.has(id));
}

/** True when at least one of `partIds` is hidden. */
export function anyHidden(hidden: readonly string[], partIds: readonly string[]): boolean {
  if (!hidden.length) return false;
  const set = new Set(hidden);
  return partIds.some((id) => set.has(id));
}
