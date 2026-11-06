export const DEFAULT_URL: string;
export type WardMessage = { name: string; message: Record<string, unknown> };
export type WardDevice = (request: WardMessage) => Promise<WardMessage>;
export type WardStep =
  | { deviceCall: WardMessage; result?: never; error?: never }
  | { result: Record<string, unknown>; deviceCall?: never; error?: never }
  | {
      error: { code: string; message: string };
      deviceCall?: never;
      result?: never;
    };
export type WardConnectOptions = { url?: string; token: string };
export class WardError extends Error {
  readonly code: string;
  constructor(code: string, message: string);
}
export class WardAdapter {
  private constructor();
  static connect(options: WardConnectOptions): Promise<WardAdapter>;
  start(method: string, params?: Record<string, unknown>): Promise<WardStep>;
  resume(name: string, message: Record<string, unknown>): Promise<WardStep>;
  answerWardRequest(
    name: string,
    message: Record<string, unknown>,
  ): Promise<WardMessage>;
  call(
    method: string,
    params?: Record<string, unknown>,
    device?: WardDevice,
  ): Promise<Record<string, unknown>>;
  setLogging(enabled: boolean): Promise<void>;
  close(): Promise<void>;
}
