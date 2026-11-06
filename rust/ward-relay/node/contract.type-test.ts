import { WardAdapter, type WardDevice } from "./index.js";

const device: WardDevice = async (request) => ({
  name: "Success",
  message: request.message,
});
const check = async () => {
  const adapter = await WardAdapter.connect({ token: "local-token" });
  await adapter.call("sync", {}, device);
  const step = await adapter.start("status");
  if (step.deviceCall) {
    const name: string = step.deviceCall.name;
    void name;
  }
  await adapter.close();
};
void check;

// @ts-expect-error The token is required for the wardd handshake.
void WardAdapter.connect({});
