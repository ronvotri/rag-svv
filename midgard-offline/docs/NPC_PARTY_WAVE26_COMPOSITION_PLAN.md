# NPC Party — Wave 26: true composed Cole/Haneul source-frame QA (DRAFT ONLY)

Base: Wave 25 / PR #15. No Town/production changes. Status: Build #345 composed-frame evidence captured; Town acceptance still pending.

## Root cause confirmed from Build #338

The 96 PNG motion samples were captured from `RoAssets.sprite([sprite_id])` and `RoVisual.sprite.texture.get_image()`. This is the original **body source sprite**, not a guaranteed complete character.

The original recovered Town crowd calls `RoAssets.styled_character(...)` and `RoVisual.setup(...)`. The recovered `RoSprite` also exposes `compose_image(...)`. These are the **client's own** layer-composition mechanisms; no hand-drawn or substitute art should be introduced.

## Next evidence to acquire

1. Read `town-rendering-api.json` produced by Windows Build #342 (or its successful successor): require `scripts/autoload/ro_assets.gd` to expose the actual `styled_character` signature and bounded layer hints. Never guess parameters.
2. Make a dedicated off-map `styled_character` QA capture for `gunslinger`, `gunslinger_f`, `taekwon`, `taekwon_f`, using original color/head/hair defaults. Capture Idle + two Walk ticks, eight directions, preserving original pixel scale.
3. Compare the **composed** frames to the existing body-only frames. Record frame identity, layer presence and image/hash evidence in an artifact; inspect head/hair alignment, occlusion and cadence visually rather than auto-approve.
4. Only after manual image approval, separately test Prontera placement, collisions and tap/click interaction on Windows and mobile.

Required safety invariants: `approved_for_town: false`, `animation_verified: false`, `directions_verified: false` until independent review; no save edits, unlocks, merges or deployment. Cole/Haneul remain unspawned in production Town. Kira stays locked; Lumi's Summoner/Doram identification remains unverified.

This file is a **handoff**, not gameplay acceptance.

## Wave 26 implementation

- The off-map GDScript probe now invokes the exact original factory signature recovered from Build #342: `styled_character(body, weapon, weapon_fx, fx_bases, headgear, look, shield, extras)`.
- Use the un-gendered base `gunslinger` or `taekwon` and the original factory's `look.gender` to select the `_f` variant. Hair index 2, hair color 0 and clothing dye 0 are neutral QA defaults.
- Save separate `rare-composed-*.png` images and `RARE_NPC_COMPOSED.json`; compare against original body-only source evidence. PNG/hash checks do not confer visual approval.
- Build #342 succeeded and supplied API metadata. Build #345 succeeded and produced the first full composed-image evidence. Runtime image integrity passed, but in-town acceptance remains pending.

## Wave 27 checkpoint — artifact review (2026-11-21)

- Windows CI run **#345** succeeded on `8c1e7b94aeec03facc9aaa170181a8d935a5777c`: https://github.com/ronvotri/rag-svv/actions/runs/44833902742
- Reviewed nested `Rare-NPC-Sprite-QA.zip` from Actions artifact `rare-npc-source-sprite-QA` (ID `14676938810`). The archive contains **96 composed PNGs**, **96 body-only motion PNGs**, and 8 static source PNGs, plus JSON manifests.
- `RARE_NPC_COMPOSED_CHECK.json` reports `composed_samples_ready_for_manual_review`: 96/96 hash/PNG-validated composed samples and 96/96 different from body-only inputs, with 4/4 variants differing. This is **integrity evidence**, not automatic art approval.
- `RARE_NPC_MOTION_CHECK.json` reports `motion_samples_ready_for_manual_review`: 96/96 body-source motion samples, 32 observed Walk-frame changes and Idle direction variation for all four sprite variants.
- A human contact-sheet review of the composed `PC_IDLE` samples in all 8 facings for Cole (Gunslinger M/F) and Haneul (Taekwon M/F) found visible, connected-looking head/hair and body and no obvious detached layers in those samples. Walk frames at both captured ticks were also reviewed as rendered images. **This is a limited off-map visual review**, not proof of correct world scaling, depth ordering, continuous animation cadence or collision.
- The neutral demo look (`hair=2`, `hair_color=0`, `cloth=0`) is not final NPC identity art; characterization/wardrobe choice can be handled separately.
- **Decision:** Allow a *future isolated Prontera staging test*, but keep `approved_for_town: false`, `animation_verified: false`, `directions_verified: false`, and `head_hair_verified: false` in machine-readable evidence until dedicated world-space visual QA is recorded.

### Next QA gate — non-production Prontera staging

1. Spawn temporary composed models **only under an explicit QA flag + `--offline-test`**, never from normal `SVVCompanionTown.JOBS` and never from player save data.
2. Capture Town screenshots at desktop + portrait + landscape mobile aspect ratios; inspect z-order, scale and 8 facings with real scene props.
3. Verify walkable-lane clearance, Kafra/other NPC separation, projection and mouse/touch targeting against an isolated QA fixture.
4. Check cleanup after leaving Town, scene switch and retry; ensure no duplicate actors or persistent save writes.
5. Only then discuss any player-facing dialogue, recruitment or unlocking changes. Kira remains excluded; Lumi's Doram identity remains unverified.

**Safety:** This Wave 27 checkpoint is evidence/documentation only. No Town spawn, gameplay, save, merge or deploy.
