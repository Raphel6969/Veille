import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  const setting = (name: string) => vscode.workspace.getConfiguration("veille").get<string>(name)!;
  context.subscriptions.push(vscode.commands.registerCommand("veille.preflight", async () => {
    const task = await vscode.window.showInputBox({ prompt: "Task-contract YAML path", value: "task_contract.yaml" });
    if (!task) return;
    const terminal = vscode.window.createTerminal("VEILLE");
    terminal.show();
    terminal.sendText(`${setting("cliPath")} preflight "${task}" --output "${setting("proposalPath")}"`);
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.viewProposal", async () => {
    const proposal = vscode.Uri.joinPath(vscode.workspace.workspaceFolders?.[0]?.uri ?? vscode.Uri.file("."), ...setting("proposalPath").split("/"));
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
    terminal.sendText(`${setting("cliPath")} run ${setting("defaultWorkflow")} --proposal "${setting("proposalPath")}" --approve`);
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.daemonHealth", async () => {
    try {
      const response = await fetch(`${setting("daemonUrl")}/health`);
      const health = await response.json() as { status?: string };
      vscode.window.showInformationMessage(`VEILLE daemon: ${health.status ?? "unknown"}`);
    } catch {
      vscode.window.showWarningMessage("VEILLE daemon is not reachable at 127.0.0.1:8020.");
    }
  }));
}

export function deactivate() {}
