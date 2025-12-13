import { useCallback, useState } from "react";

export const useAsyncAction = <TArgs, TResult>(
  executor: (args: TArgs) => Promise<TResult>,
) => {
  const [isPending, setPending] = useState(false);

  const mutate = useCallback(
    (args: TArgs, handlers?: { onSuccess?: (result: TResult) => void; onError?: (error: unknown) => void }) => {
      setPending(true);
      executor(args)
        .then((result) => {
          handlers?.onSuccess?.(result);
        })
        .catch((error) => {
          handlers?.onError?.(error);
        })
        .finally(() => setPending(false));
    },
    [executor],
  );

  const mutateAsync = useCallback(
    async (args: TArgs): Promise<TResult> => {
      setPending(true);
      try {
        return await executor(args);
      } finally {
        setPending(false);
      }
    },
    [executor],
  );

  return { mutate, mutateAsync, isPending };
};
