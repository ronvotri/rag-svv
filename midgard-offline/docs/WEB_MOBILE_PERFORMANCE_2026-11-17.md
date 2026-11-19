# Web mobile: cache data + adaptive performance (17/11/2026)

## Goal
- Reduce repeated loading in the same browser profile after the first successful online load.
- Avoid the previous permanent 30 FPS cap on mobile.
- Preserve Ragnarok art, AI/combat rules, menus and player saves.

## Changes
1. tools/prepare-original-web-deploy.py: content-addressed <=16 MiB PCK/WASM chunks. Byte-identical chunks keep URLs across releases.
2. cloudflare/godot-split-sw.js: Cache Storage (svv-game-chunks-v1) first, network fallback, one-part-at-a-time streaming. Cache writes respect available-space estimates and reserve 64 MiB; quota errors do not block gameplay. The worker only prunes obsolete entries of its own binary cache.
3. original-addons/web_mobile_performance.gd: up to 60 FPS; base landscape raster 800x450 with adaptive quality if FPS is consistently low, recovering quality when performance improves.
4. Regression tests include cold/warm caching, range requests, cache failure fallback and cross-version chunk reuse.

## Limits
- Cached data does not eliminate WebAssembly initialization, shader compilation, PCK parsing or first map setup.
- Cache storage is best effort, and low-storage/private browsers may evict it. Zalo in-app preview and Chrome use different storage contexts; first download can happen separately on each.
- Changed assets need downloading again; unchanged chunks keep URLs.
- The game cache does not touch save files; DO NOT clear all browser site data without backing up saves first.
- WebGL on mobile is slower than native Android in many cases. Static build QA is not real-device FPS or reload QA.

## Acceptance after deployment
1. Open the production website in normal Android Chrome; record cold-load time, first map FPS and 10 minutes of combat.
2. Close, reopen in the SAME browser profile; verify Cache Storage > svv-game-chunks-v1 has the asset chunks, unchanged chunks are served without repeat network downloads.
3. Publish a code-only update; ensure unchanged chunk hashes and paths still match.
4. Exercise party, combat, leveling, UI after performance scale changes and mobile landscape.
5. Test Zalo WebView separately, and verify safe network fallback if browser cache quota is insufficient.
6. Check GitHub Web QA and actual Cloudflare publication. Publish third-party game assets publicly only if the uploader has redistribution rights.

Do not mark the user-facing problem fixed until device/browser checks pass.
