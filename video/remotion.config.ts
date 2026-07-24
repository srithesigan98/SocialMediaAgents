/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import { existsSync } from "node:fs";
import { Config } from "@remotion/cli/config";
import { enableTailwind } from '@remotion/tailwind-v4';

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.overrideWebpackConfig(enableTailwind);

// Claude Code web/remote sessions can't download Remotion's own headless
// Chrome (network egress is restricted), but they ship a pre-installed one.
// Use it when present; local dev machines fall through to Remotion's default.
const remoteHeadlessShell =
  "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
if (existsSync(remoteHeadlessShell)) {
  Config.setBrowserExecutable(remoteHeadlessShell);
}
