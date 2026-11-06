import { createRequire } from "node:module";

const native = createRequire(import.meta.url)("./native/ward-relay.node");
export const DEFAULT_URL = "ws://127.0.0.1:21329";

export class WardError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "WardError";
    this.code = code;
  }
}

export class WardAdapter {
  #native;
  #calling = false;

  constructor(client) {
    this.#native = client;
  }

  static async connect({ url = DEFAULT_URL, token }) {
    return new WardAdapter(await native.connect(url, token));
  }

  async start(method, params = {}) {
    return JSON.parse(await this.#native.start(method, JSON.stringify(params)));
  }

  async resume(name, message) {
    return JSON.parse(await this.#native.resume(name, JSON.stringify(message)));
  }

  async answerWardRequest(name, message) {
    const step = JSON.parse(
      await this.#native.answerWardRequest(name, JSON.stringify(message)),
    );
    return step.deviceCall;
  }

  async call(method, params = {}, device) {
    if (this.#calling) throw new Error("a WARD conversation is already active");
    if (["sync", "lookup", "update"].includes(method) && !device) {
      throw new Error(`${method} requires a device callback`);
    }
    this.#calling = true;
    try {
      let step = await this.start(method, params);
      while (step.deviceCall) {
        const reply = await device(step.deviceCall);
        step = await this.resume(reply.name, reply.message);
      }
      if (step.error) throw new WardError(step.error.code, step.error.message);
      if (!step.result) throw new Error("adapter returned no result");
      return step.result;
    } catch (error) {
      // A failed device callback leaves wardd awaiting a reply; abandon this endpoint.
      await this.close();
      throw error;
    } finally {
      this.#calling = false;
    }
  }

  async setLogging(enabled) {
    await this.#native.setLogging(enabled);
  }

  async close() {
    await this.#native.close();
  }
}
