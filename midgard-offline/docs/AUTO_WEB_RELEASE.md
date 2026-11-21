# Ragnarok Web — one-time auto publish setup

## Source, destination and protection

- Release branch: `release/ragnarok-web`. This is NOT `main`, the rare-NPC draft branch, or a replacement for either.
- Production Cloudflare Pages project: `rag-svv-web`, https://rag-svv-web.pages.dev.
- The dedicated release workflow is `.github/workflows/original-web-publish.yml`. It uses the triggering release commit (`github.sha`), not a hard-coded older build.
- A normal push to the release branch triggers the workflow, but **the publish job stays skipped until one-time explicit opt-in**.
- The workflow checks the source branch, runs authored tests, reconstructs and tests the client, prepares a Pages Free compatible static site, verifies Cloudflare account/project metadata, then deploys to the existing Pages project's production branch.
- The `web-production` GitHub environment and existing `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` secrets are retained. No secrets are copied to the repository.
- Do not publish an upstream author's game assets unless permission to host and redistribute them has been confirmed. The fact that the original game is freely downloadable is not permission to republish it.

## Enable automatic deployment once (repository owner)

After confirming rights to redistribute the original game assets, go to
**GitHub repository → Settings → Secrets and variables → Actions → Variables** and add
a repository variable `RAGNAROK_AUTO_DEPLOY_WEB` with value `true`.

Do not set the variable before confirming authorization. Leaving it absent or set to anything other than `true` means that ordinary release-branch pushes cannot publish. You can pause all automatic release deployments by changing it to `false`.

To run a one-time manually authorized deployment without enabling auto-release, choose
**Actions → Ragnarok SVV - publish original Web (Pages Free) → Run workflow** on `release/ragnarok-web` and confirm the permission checkbox.

## Workflow for the assistant on future updates

1. Work in a development/Draft branch; leave `main`, NPC work and the live site alone.
2. Verify upstream source hashes, change reports and Web/client tests. Check the game/content version, save compatibility and browser behavior. Do not take a green compilation alone as full game QA.
3. Promote the tested source into `release/ragnarok-web` *without overwriting its automation workflow*. A commit to this branch triggers the rights-gated publisher. No manual branch guessing is required.
4. Confirm the GitHub Actions `publish` job conclusion, deployed commit and live URL before claiming an update is online. If CI or deployment fails, report the exact blocker and do not claim the site changed.

## Known limitations

- Official itch.io upstream client requests can return HTTP 429 (rate limit). Publisher fails closed instead of bypassing the official rate limit. A successful code/test package alone cannot guarantee a live release.
- The existing Web client still needs real-device testing (cache/IndexedDB/save import-export, mobile UI). Export a JSON backup before major updates. Keep the URL unchanged to avoid losing browser origin-local save.
- The original client is hosted as static assets for a browser game; this does not create an online multiplayer server.
