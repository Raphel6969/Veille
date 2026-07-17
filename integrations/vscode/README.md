# VEILLE VS Code extension

VEILLE Preflight is a thin VS Code client for the Runtime Supervisor. It never
implements planning, policy, routing, or storage in the extension: it invokes
the `veille` CLI and reads the daemon health endpoint.

## Build and install

From this directory, install the development dependencies, verify the command
integration tests, and create a VSIX:

```powershell
npm install
npm test
npm run package
```

Install `veille-vscode.vsix` in VS Code with **Extensions: Install from VSIX…**.
For development, run `npm run compile`, open this folder in VS Code, and launch
the **Run Extension** configuration.

The workspace must also have the VEILLE Python package installed and the
configured `veille.cliPath` available on the terminal path. Start a local daemon
with `veille daemon` when using the daemon-health command.

## Commands

- **VEILLE: Create Preflight Proposal** writes a proposal using `veille preflight`.
- **VEILLE: View Preflight Proposal** opens the generated JSON without changing it.
- **VEILLE: Approve & Run Workflow** requires a modal confirmation, then invokes
  the shared runtime with `--approve`.
- **VEILLE: Check Local Daemon** reads the daemon `/health` endpoint.

## Settings

`veille.cliPath`, `veille.daemonUrl`, `veille.proposalPath`, and
`veille.defaultWorkflow` are workspace settings. They let the integration point
at a local CLI, daemon, and proposal path without embedding runtime behavior.
