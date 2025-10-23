import * as React from 'react';
import debounce from 'lodash.debounce';

export function useDebouncedPreview<TVars, TPreview>(
  previewFn: (vars: TVars) => Promise<TPreview>,
  delay = 250,
) {
  const [preview, setPreview] = React.useState<TPreview>();
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<Error>();

  const debounced = React.useMemo(
    () =>
      debounce(async (vars: TVars) => {
        setIsLoading(true);
        setError(undefined);
        try {
          setPreview(await previewFn(vars));
        } catch (err) {
          setError(err as Error);
        } finally {
          setIsLoading(false);
        }
      }, delay),
    [previewFn, delay],
  );

  React.useEffect(() => () => debounced.cancel(), [debounced]);

  return { preview, isLoading, error, triggerPreview: debounced };
}
