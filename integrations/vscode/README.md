# VEILLE VS Code extension

Thin client for the VEILLE Runtime Supervisor. It does not implement planning,
policy, routing, or storage. It invokes `veille preflight` and checks the local
daemon health endpoint.

Commands: create/view `.veille/proposal.json`, explicitly approve and run the
safe cited-market-research workflow, and check daemon health. Run `npm install`,
then `npm run compile`; launch it through VS Code's extension development host.
