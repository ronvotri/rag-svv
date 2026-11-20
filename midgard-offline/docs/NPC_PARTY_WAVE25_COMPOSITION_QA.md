# NPC Party — Wave 25: character composition preflight (DRAFT / NOT FOR RELEASE)

Checkpoint: 2026-11-21 (ICT). Source branch: PR #14 at `162f2cfd181158a5427880259ff76e916c66e3f3`.

## Evidence reviewed

- [Original-client Windows Build #338](https://github.com/ronvotri/rag-svv/actions/runs/44828147528) is **completed / success**.
- Its `rare-npc-source-sprite-QA` artifact ID **14675139223** contains a nested `Rare-NPC-Sprite-QA.zip`, `RARE_NPC_MOTION.json`, `RARE_NPC_MOTION_CHECK.json` and original source-frame PNGs.
- The motion report states `motion_samples_ready_for_manual_review`: 96/96 PNG samples, 32/32 walk pairs have distinct file hashes, four variants have idle direction variation. These are data/integrity checks, not full artistic approval.
- Manually inspected 8-direction contact sheets for `gunslinger`, `gunslinger_f`, `taekwon`, `taekwon_f` (8 Idle poses and two Walk samples per direction). Body direction changes and leg motion are visible. No apparent texture-boundary clipping in the exported body images. **A complete rendered character head/hair layer is not visible in these source texture captures.**
- The current capture path is `visual.sprite.texture.get_image()` on a single `RoVisual` created from `RoAssets.sprite([sprite_id])`. A body-only source texture cannot be treated as a fully composed player/NPC appearance.
- Build #338's recovered-client metadata additionally shows a different `RoAssets.styled_character(...)` factory used by the original Town crowd. Its full signature and head/hair behavior must be inspected before modifying the rare-NPC renderer.

## Wave 25 changes

- The original-client API metadata inspector now looks at recovered `scripts/ro/ro_assets.gd` factory signatures and filtered head/hair/body/gender/appearance hints.
- The generated `town-rendering-api.json` includes explicit `rare_npc_composition_review` with `town_placement_approved: false`, even if a source body texture has eight direction hashes.
- Regression tests verify the metadata is discoverable without approving an NPC, including when the factory is absent.
- No recovered source or copyrighted game sprite is committed to Git. Contact sheets and PNG files remain QA/download artifacts, not repository assets.

## Remaining gates (mandatory)

1. Inspect the new `town-rendering-api.json` factory signature and determine how the original renderer combines job body, head, hair and equipment for both variants.
2. Capture **complete** composed Cole/Haneul characters at original pixel scale in all eight directions, then inspect Idle and Walk cycles and orientation.
3. Only after composition review, separately prototype Prontera placement, collisions, dialog, **Tìm party** and real PC/mobile taps.
4. Keep Kira blocked and Lumi's `summoner(_f)` ↔ Doram mapping unverified.

**Do not merge, deploy, unlock, amend production save data, or infer playable NPC acceptance from CI SUCCESS.** This PR only expands evidence acquisition.
