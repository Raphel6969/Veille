import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(vscode.commands.registerCommand("veille.preflight", async () => {
    const task = await vscode.window.showInputBox({ prompt: "Task-contract YAML path", value: "task_contract.yaml" });
    if (!task) return;
    const terminal = vscode.window.createTerminal("VEILLE");
    terminal.show();
    terminal.sendText(`veille preflight "${task}" --output .veille/proposal.json`);
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.viewProposal", async () => {
    const proposal = vscode.Uri.joinPath(vscode.workspace.workspaceFolders?.[0]?.uri ?? vscode.Uri.file("."), ".veille", "proposal.json");
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
    terminal.sendText("veille run cited_market_research --proposal .veille/proposal.json --approve");
  }));

  context.subscriptions.push(vscode.commands.registerCommand("veille.daemonHealth", async () => {
    try {
      const response = await fetch("http://127.0.0.1:8020/health");
      const health = await response.json() as { status?: string };
      vscode.window.showInformationMessage(`VEILLE daemon: ${health.status ?? "unknown"}`);
    } catch {
      vscode.window.showWarningMessage("VEILLE daemon is not reachable at 127.0.0.1:8020.");
    }
  }));
}

export function deactivate() {}
