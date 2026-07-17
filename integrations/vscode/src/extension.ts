import * as vscode from "vscode";
import { approvedRunCommand, daemonHealthUrl, preflightCommand, VeilleSettings } from "./commands";

export function activate(context: vscode.ExtensionContext) {
  const settings = (): VeilleSettings => {
    const configuration = vscode.workspace.getConfiguration("veille");
    return {
      cliPath: configuration.get<string>("cliPath")!,
      daemonUrl: configuration.get<string>("daemonUrl")!,
      proposalPath: configuration.get<string>("proposalPath")!,
      defaultWorkflow: configuration.get<string>("defaultWorkflow")!,
    };
  };
  context.subscriptions.push(vscode.commands.registerCommand("veille.preflight", async () => {
    const task = await vscode.window.showInputBox({ prompt: "Task-contract YAML path", value: "task_contract.yaml" });
    if (!task) return;
    const terminal = vscode.window.createTerminal("VEILLE");
    terminal.show();
    terminal.sendText(preflightCommand(settings(), task));
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.viewProposal", async () => {
    const proposal = vscode.Uri.joinPath(vscode.workspace.workspaceFolders?.[0]?.uri ?? vscode.Uri.file("."), ...settings().proposalPath.split("/"));
    try {
      await vscode.workspace.fs.stat(proposal);
      await vscode.window.showTextDocument(proposal, { preview: true });
    } catch {
      vscode.window.showWarningMessage("No .veille/proposal.json found. Create a preflight proposal first.");
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.approveRun", async () => {
    const confirmed = await vscode.window.showWarningMessage(
      "Apply the current proposal to the cited market research workflow?",
      { modal: true }, "Approve & Run"
    );
    if (confirmed !== "Approve & Run") return;
    const terminal = vscode.window.createTerminal("VEILLE");
    terminal.show();
    terminal.sendText(approvedRunCommand(settings()));
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.daemonHealth", async () => {
    try {
      const response = await fetch(daemonHealthUrl(settings()));
      const health = await response.json() as { status?: string };
      vscode.window.showInformationMessage(`VEILLE daemon: ${health.status ?? "unknown"}`);
    } catch {
      vscode.window.showWarningMessage("VEILLE daemon is not reachable at 127.0.0.1:8020.");
    }
  }));
}

export function deactivate() {}
