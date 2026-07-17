export interface VeilleSettings {
  cliPath: string;
  daemonUrl: string;
  proposalPath: string;
  defaultWorkflow: string;
}

export function preflightCommand(settings: VeilleSettings, taskContractPath: string): string {
  return `${settings.cliPath} preflight "${taskContractPath}" --output "${settings.proposalPath}"`;
}

export function approvedRunCommand(settings: VeilleSettings): string {
  return `${settings.cliPath} run ${settings.defaultWorkflow} --proposal "${settings.proposalPath}" --approve`;
}

export function daemonHealthUrl(settings: VeilleSettings): string {
  return `${settings.daemonUrl.replace(/\/$/, "")}/health`;
}
