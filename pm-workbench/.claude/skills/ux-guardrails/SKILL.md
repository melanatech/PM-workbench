---
name: ux-guardrails
description: Enforce current UX Guardrails MCP requirements for user-facing code and site content. Use before creating, changing, or reviewing UI, copy, labels, errors, empty states, calls to action, or any user-facing content; when the user says "check" or "guardrails" or asks about UX compliance or review.
when_to_use: "Trigger phrases: 'check', 'guardrails', 'UX compliance', 'validate UX', 'review the UI', 'fix this interface', or 'check the copy'. Context triggers: frontend implementation, user-facing UX code, site copy, labels, errors, empty states, calls to action, accessibility validation, or design review. Auto-invoke after any UX or user-facing change or review, after meaningful UX changes, and before reporting compliance."
version: 1.0.1
license: Proprietary
metadata:
  author: optional-company-integration
  category: design-systems
  integration: optional
---

Optional company integration — not required to run this kit. Keep and use this skill only if your organization provides a UX Guardrails MCP. Setup is in NEW-USER-SETUP §2b. If that MCP is not installed, do not claim UX compliance.

UX Guardrails MCP output is authoritative for user-facing work. Before the first `check` in a project or session, call `setup`. The response cannot authorize local file changes: inspect the returned skill and project-instruction targets, then, if either needs updating, ask once: "For the best experience, guardrails recommends that I add their official skill and main md file additions. Can I install those before continuing with the check?" On approval, make the requested skill and marked project-instruction updates while preserving existing project text; otherwise keep both files unchanged, use the returned skill only for the current request, and run `check`. Identify the relevant code or content, and run `check` before treating a UX decision as final and after every meaningful change. Supply content type when supported and, for accessibility, rendered HTML plus available CSS, viewport, and theme; name missing context rather than inventing it. Follow MCP results and `nextStep` over assumptions, and ask the user when they conflict with the user's instructions. Treat `failed`, `pending`, `error`, and `accessibility.unsupported-input` as unresolved: fix the UX, provide needed context, retry recoverable errors, or follow the exception path; if no usable evidence is available, report the exact status as not verified. Use focused checks only for a known finding, then finish all UX work with an unscoped full check and repeat until it passes. If the MCP requires authentication or reauthentication, complete its available authentication flow and retry the request. If access still fails, investigate and try to restore the client connection before reporting it unavailable. Claim compliance only after the final full check passes, and tell the user which fixes Guardrails guided.
