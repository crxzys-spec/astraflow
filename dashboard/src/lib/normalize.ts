export const normalizeList = <T, R>(
  items: T[] | null | undefined,
  normalizer: (item: T) => R,
): R[] => (items ?? []).map(normalizer);

export const toListModel = <T, R>(
  payload: { items?: T[] | null; nextCursor?: string | null },
  normalizer: (item: T) => R,
): { items: R[]; nextCursor: string | null } => ({
  items: normalizeList(payload.items, normalizer),
  nextCursor: payload.nextCursor ?? null,
});
