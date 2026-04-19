import { ExtensionContext } from "@foxglove/extension";
import { initManualEngagePanel } from "./ManualEngagePanel";

export function activate(extensionContext: ExtensionContext): void {
  extensionContext.registerPanel({
    name: "manual-engage",
    initPanel: initManualEngagePanel,
  });
}
