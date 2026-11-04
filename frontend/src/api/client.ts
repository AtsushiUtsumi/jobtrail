import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

export const api = createClient<paths>({ baseUrl: "/" });

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly hint: string;

  constructor(status: number, body: unknown) {
    const error = (body ?? {}) as Partial<Schemas["ErrorOutput"]>;
    super(error.message ?? `通信に失敗しました（${status}）`);
    this.status = status;
    this.code = error.code ?? "UNKNOWN";
    this.hint = error.hint ?? "";
  }
}

interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

export async function unwrap<T>(request: Promise<ApiResult<T>>): Promise<NonNullable<T>> {
  const { data, error, response } = await request;
  if (!response.ok || data === undefined || data === null) {
    throw new ApiError(response.status, error);
  }
  return data;
}
