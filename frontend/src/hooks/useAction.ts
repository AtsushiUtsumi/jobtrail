import { useMutation } from "@tanstack/react-query";

/** 更新系の操作。成功時の再取得と失敗時の通知は QueryClient 側でまとめて行う。 */
export function useAction<T>(action: (input: T) => Promise<unknown>) {
  return useMutation({ mutationFn: action });
}
