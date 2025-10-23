import * as React from 'react';

export function useOptimisticMutation<TData, TVars>(
  mutationFn: (vars: TVars) => Promise<TData>,
  optimisticUpdate: (prev: TData | undefined, vars: TVars) => TData,
) {
  const [data, setData] = React.useState<TData>();
  const [backup, setBackup] = React.useState<TData>();
  const [isLoading, setIsLoading] = React.useState(false);

  const mutate = async (vars: TVars) => {
    setIsLoading(true);
    setBackup(data);
    setData(optimisticUpdate(data, vars));

    try {
      const result = await mutationFn(vars);
      setData(result);
      return result;
    } catch (error) {
      setData(backup);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return { data, setData, mutate, isLoading };
}
