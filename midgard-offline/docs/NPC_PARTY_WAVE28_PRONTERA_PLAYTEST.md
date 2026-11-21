# NPC Party Wave 28 — Prontera interactive QA (DRAFT / DO NOT MERGE)

Base: PR #16 at ba7b9c0. This branch does not modify main, Cloudflare, released Web, normal saves or the 11-job class catalog.

## Windows playtest mode

Download the **original-offline-windows-TEST** artifact for a successful Wave 28 Actions build and extract the nested game ZIP. Double-click `TEST-PRONTERA-NPC-QA.cmd`, not the normal EXE, to pass both `--offline-test --rare-town-qa`. This uses the existing **separate QA save profile** `profile_offline_test`; normal `profile_offline` is untouched.

- Mira (Acolyte), Alden (Swordsman), Eira (Mage), Elowen (Archer), Riku (Thief), Mino (Merchant) retain their existing quest/Friends List/Tìm party interactions. The party limit is three AI companions; no real multiplayer matching.
- Cole (Gunslinger), Haneul (Taekwon) appear ONLY under the gated QA flags in real Prontera Town, composed from ORIGINAL `RoAssets.styled_character`, at **provisional** Kafra-relative offsets. Tap/click shows a warning dialog. They **cannot be recruited** yet.
- Kira (Ninja), Lumi (unverified Doram / Summoner mapping), Nao (basic Novice sprite missing) stay blocked; their presence in Friends List, if any, must not be mistaken for verified gameplay.
- Normal EXE, Web, or Android startup does **not** spawn these two QA actors. When leaving Town, transient actors are removed. No QA actor writes to save.

## QA matrix

1. Open normal `MidgardSVVOffline.exe`: no Cole/Haneul QA actor at Prontera.
2. Open `TEST-PRONTERA-NPC-QA.cmd`: verify separate QA profile, then enter Prontera.
3. Check Mira + five classic NPCs: original sprite identity, positions, click/touch dialogue, quest progression, recruitment to Friends List, party 0/3→3/3, leaving party.
4. Check Cole/Haneul: visible composed body+head+hair, size, depth over props, nameplate, clickable position, no duplicated actor across Town re-entry, no recruitment.
5. Verify a run with 3 recruited companions, especially actual Acolyte HP recovery, and save/reload only of QA profile.
6. Compare desktop 1280×720 and phone portrait 390×844 / landscape 844×390 viewports before approval. Review original actor offsets and any click targets hidden by UI.
7. Check normal profile after returning via normal EXE. No QA unlocks, game-data changes or leaked NPCs.

## Explicitly unverified

At commit creation: **Godot build and in-game interactive QA still pending**. Python unit-test PASS by itself is not a playable client or valid art/animation signoff. Screenshots from CI, when available, are evidence, not acceptance. These NPCs remain unapproved for production, and this branch must remain Draft, unmerged and undeployed.

## Web publishing to the existing Pages URL (explicit manual action)

The user prefers to reuse their existing Cloudflare Pages project: **`rag-svv-web`**, at **https://rag-svv-web.pages.dev**. Do not create a separate project, URL or route.

- The Wave 28 Web package is built with `SVV_WEB_NPC_QA=1` in the dedicated branch and uses `application/config/svv_web_npc_qa=true` to show Cole/Haneul for visual QA. They remain **non-recruitable**; regular Windows/default builds stay gated.
- First verify **Original client - Web package QA** reaches SUCCESS. It publishes private Actions artifacts only, no site changes.
- The manual **Ragnarok SVV - publish original Web (Pages Free)** workflow has been customized **on the Wave 28 branch only** to rebuild that branch and deploy to the **existing** Pages project and its detected production branch. The main/default publish workflow still builds `feature/original-offline` and must not be used for Wave 28 testing.
- Publishing original game assets requires permission to publicly redistribute them. The publish workflow explicitly requires `redistribution_rights_confirmed=true`; the user must review and tick this only if authorized.
- In GitHub Actions: select **Ragnarok SVV - publish original Web (Pages Free)**, choose **Run workflow**, select branch `feature/offline-friends-wave12-prontera-playtest`, tick the rights confirmation if true, run it, and verify the green publish job and Cloudflare deployment. It uses the existing secrets `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`, not R2.
- Then test **https://rag-svv-web.pages.dev**; refresh stale Godot/PWA assets if necessary. Note that this overwrites the live site and could affect testers even though it does not merge `main`. Back up saves before QA.

Do not claim published or playable until both build and publish jobs complete and the browser is tested. If rights cannot be confirmed, do not publicly deploy; use a local Web package or Windows QA build instead.
