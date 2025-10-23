export const generateIdempotencyKey = () =>
  `lunia_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
