export const engineStatusAdapter = (wsData: any) =>
  Object.entries(wsData ?? {}).reduce(
    (acc: any, [key, value]) => ({
      ...acc,
      [key]: value === 'active' ? 'on' : 'off',
    }),
    {},
  );
