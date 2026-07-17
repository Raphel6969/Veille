import assert from "node:assert/strict";
import test from "node:test";

import { approvedRunCommand, daemonHealthUrl, preflightCommand, VeilleSettings } from "../commands";

const settings: VeilleSettings = {
  cliPath: "veille",
  daemonUrl: "http://127.0.0.1:8020/",
  proposalPath: ".veille/proposal.json",
  defaultWorkflow: "cited_market_research",
};

test("preflight command delegates proposal creation to the configured CLI", () => {
  assert.equal(
    preflightCommand(settings, "contracts/research.yaml"),
    'veille preflight "contracts/research.yaml" --output ".veille/proposal.json"',
  );
});

test("approved run command requires the runtime approval flag", () => {
  assert.equal(
    approvedRunCommand(settings),
    'veille run cited_market_research --proposal ".veille/proposal.json" --approve',
  );
});

test("daemon health URL has exactly one health suffix", () => {
  assert.equal(daemonHealthUrl(settings), "http://127.0.0.1:8020/health");
});
