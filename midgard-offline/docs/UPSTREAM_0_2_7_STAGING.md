# Ragnarok Web — publisher 0.2.7 staging (2026-11-21)

This is an isolated **pre-release** update. It is not deployed and must not be described as the live Web version until the Cloudflare publish job succeeds.

## Exact source
- Publisher manifest: https://github.com/Gon-Analista/midgard-survivors-updates/blob/main/manifest.json
- Publisher patch: `https://updates.midgardsurvivors.com/patches/patch_0.2.7.bin`
- Cumulative for original base **0.2.0**, version **0.2.7**, **23,049,020** bytes.
- SHA-256: `4fa81dcae4b62e0f9894286405378dad4c745d89cf7952bce7632e65ce6ce57b`.
- Binary verified by [patch workflow #44890794549](https://github.com/ronvotri/rag-svv/actions/runs/44890794549), **SUCCESS**.
- Web package QA [#44890656532](https://github.com/ronvotri/rag-svv/actions/runs/44890656532), must be inspected for a final success before promotion.
- The legacy 0.2.5 Web QA [#44884803381](https://github.com/ronvotri/rag-svv/actions/runs/44884803381) previously passed; that does **not** validate 0.2.7.
- The publisher's 0.2.7 hotfix adjusts fused-monster rewards and duplicate loot; some 0.2.6 features depend on the publisher's online relay and are not promised in this offline browser adaptation.

## Keep custom work and save
- The new publisher patch is loaded after the pinned 0.2.0 base and **before** custom Vietnamese/offline/NPC/Save Guardian modifications.
- Preserve player profile names and browser origin; never delete stored IndexedDB data as part of deployment.
- Do not unlock Cole/Haneul or other QA-gated NPCs just because the publisher patch changed.
- Keep `main` and other NPC Party PRs untouched.
- This Web version runs in the browser but is not a server-backed multiplayer port.

## Release gate
- The production release branch is `release/ragnarok-web`, targeting the existing `rag-svv-web` Cloudflare Pages project.
- **Only after** full 0.2.7 Web QA PASS and review of save/compatibility warnings, fast-forward production release branch to the tested staging HEAD (no force-push).
- On push, `.github/workflows/original-web-publish.yml` builds/tests/deploys, **only if** the repository owner has explicitly set `RAGNAROK_AUTO_DEPLOY_WEB=true` after verifying rights to redistribute the source game's assets. Never bypass this authorization.
- If publisher itch.io returns HTTP 429, fail safely rather than bypassing a rate limit.
- Confirm the deployment workflow reports SUCCESS and the correct commit before claiming `https://rag-svv-web.pages.dev` is updated.
- Web/browser Save Guardian & device transfer still need human testing; export JSON before production changes.

## Status
- Publisher update config and independent patch-pin verification are committed.
- Publisher binary verification: PASS.
- Full Godot Web QA: in progress at the time of creating this handoff.
- Production website: unchanged by this staging branch.
