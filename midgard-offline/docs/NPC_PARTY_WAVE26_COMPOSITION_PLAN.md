# NPC Party — Wave 26: true composed Cole/Haneul source-frame QA (DRAFT ONLY)

Base: Wave 25 / PR #15. No Town/production changes. Status: composition evidence pending.

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
- Build #342 succeeded and supplied API metadata. The first Wave 11 composed-image build still requires its own runtime/visual QA.
