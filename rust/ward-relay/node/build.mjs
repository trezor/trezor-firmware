import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
const crate = resolve(directory, "..");
const cargo = ["--manifest-path", join(crate, "Cargo.toml")];
execFileSync(
  "cargo",
  ["build", ...cargo, "--locked", "--release", "--features", "node"],
  {
    stdio: "inherit",
  },
);
const metadata = JSON.parse(
  execFileSync(
    "cargo",
    ["metadata", ...cargo, "--no-deps", "--format-version", "1"],
    {
      encoding: "utf8",
    },
  ),
);
const library =
  process.platform === "win32"
    ? "ward_relay.dll"
    : process.platform === "darwin"
      ? "libward_relay.dylib"
      : "libward_relay.so";
mkdirSync(join(directory, "native"), { recursive: true });
copyFileSync(
  join(metadata.target_directory, "release", library),
  join(directory, "native/ward-relay.node"),
);
console.log("Built @trezor/ward-relay for", process.platform, process.arch);
