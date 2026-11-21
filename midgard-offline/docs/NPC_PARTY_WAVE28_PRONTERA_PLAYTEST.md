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

## Web test site (separate from production)

Wave 28 Web QA uses a build-time setting `application/config/svv_web_npc_qa=true`, set exclusively in the `Original client - Web package QA` workflow for `feature/offline-friends-wave12-prontera-playtest`. This shows composed Cole/Haneul in Prontera on browser QA, without requiring Windows CLI flags. Normal non-preview builds do not enable them; they remain non-recruitable.

To publish **only if you have rights to publicly redistribute the original game assets**:

1. Wait until the Wave 28 `Original client - Web package QA` workflow is **SUCCESS**.
2. In its **Artifacts**, download `npc-party-wave28-pages-ready` and extract the ZIP. The extracted folder root must contain `index.html`, `game.html`, `godot-split-sw.js`, and split WASM/PCK parts.
3. Go to your own Cloudflare dashboard, Workers & Pages, create a **new Direct Upload Pages project for this QA only** (do not overwrite `rag-svv-web` production), and upload the extracted static folder. The dashboard returns a real `*.pages.dev` URL after successful deployment.
4. Open the new URL in a browser; test Prontera, click Cole/Haneul, and report any missing hair, incorrect depth or tap-target issues. Protect testers' saves; no gameplay acceptance is implied by package validation.

The build workflow **does not upload original assets publicly automatically**; no public URL exists merely because CI succeeded. If rights are not confirmed, keep the archive for local testing only.
