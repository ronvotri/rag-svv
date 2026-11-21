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
