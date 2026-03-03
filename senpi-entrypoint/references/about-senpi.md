# About Senpi

Senpi is an agent-first trading platform on Hyperliquid that lets users discover
opportunities, automate strategies, and manage risk from one MCP-connected workflow.

## Summary Response Contract

Use this section only for explicit summary questions such as:
- "What is Senpi?"
- "Summarize Senpi"
- "Summarize skills/capabilities"
- "How do I install skills?"
- "What's new?"

Do not auto-insert this summary during normal onboarding.

Default response order (compact + actionable):
1. What Senpi is (one short definition)
2. Core capabilities
3. Full skill catalog (bullet list)
4. Install guidance
5. What's new (only if updates exist)
6. Closing question

Behavior rules:
- Use queued startup `UPDATE_OUTPUT` for "what's new" when available.
- Do not force a live update check in summary responses.
- If no updates are queued, do not mention "what's new" at all.
- Do not mention CLI/commands in user-facing summary replies.
- If user wants install/setup help, offer to handle it for them directly.
- Present the entire skill catalog as bullet points (no tables).
- End with: "Want me to recommend which skills to install next and set them up for you?"

## Core Capabilities

- Discover high-performing traders and market opportunities (Discovery + market tools)
- Copy top traders or run autonomous/custom strategy workflows
- Apply risk controls such as dynamic stop-loss and budget-aware orchestration
- Trade broad markets through Senpi's Hyperliquid-based stack (crypto perps and more)

## Full Skill Catalog (Telegram-Friendly)

- `senpi-entrypoint`: onboarding flow for Senpi setup, discovery, and first-trade guidance.
- `senpi-onboard`: account + API key + MCP setup workflow.
- `senpi-getting-started-guide`: interactive first-trade walkthrough.
- `dsl-dynamic-stop-loss`: two-phase trailing stop-loss with tiered locking.
- `dsl-tight`: tighter DSL defaults for faster profit protection.
- `opportunity-scanner`: market-wide scoring and setup discovery.
- `emerging-movers`: smart-money rotation detection.
- `autonomous-trading`: orchestrates DSL + scanner + movers.
- `wolf-strategy`: full autonomous trading stack.
- `wolf-howl`: nightly review and self-improvement loop.
- `whale-index`: mirrors top-performing traders.

## Install Skills

Keep this user-facing and non-technical:
- Offer to install and set up selected skills for the user.
- Confirm which skill(s) they want and their goal/budget before setup.
- After setup, summarize what is ready and suggest the next best action.

## What's New

Use queued updates from the entrypoint startup pending file
(`$SENPI_STATE_DIR/pending-skill-updates.json` when present). Do not force a
live check in summary responses.

If no updates are queued, skip this section in the reply.

## Platform Reference

After MCP is active, call
`read_senpi_guide(uri="senpi://guides/senpi-overview")` for full platform details
(wallets, strategies, tool categories, fees, workflows).
