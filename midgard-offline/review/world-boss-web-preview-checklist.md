# World Boss — private Web preview acceptance

Baseline: Runtime QA #13, commit e6d4281: six native MVPs, three AI allies, menu combat/HUD, verified Baphomet death, persistent unique receipt, exact +100 Zeny and replay denial all passed in the isolated desktop test profile. This is NOT a browser export or production unlock.

## Pending runtime evidence
- #14: achievement summary after reload; native return contract.
- #15: pending receipt recovery; native return to Prontera and a second Osiris launch. The repeat probe is exploratory; a skipped probe is not a pass.
- Confirm native exit does not pay the same local reward twice, and preserves existing native progression. Add player-facing return action only after observing the native exit route.

## Browser-specific work
1. Keep the public branch, existing public site and normal profile untouched. A browser preview needs an explicit build-only setting, a distinct preview profile/user directory and a separate origin; do not expose desktop QA flags as a production unlock.
2. Existing MVP encounter, result and wallet gates require the test profile and CLI/environment flags. Browser exports cannot assume shell environment variables or desktop command-line flags. Design and test a narrow preview-only gate, leaving normal build behavior unchanged. Preserve native death observation only in the authorized private preview copy; do not infer death from disappearing nodes.
3. Reuse the existing Web template installation, ETC2/ASTC import configuration, localization and Web Offline preset from cloud-build-original.py. The old cloud builder is still pinned to the stale 0.2.0/0.2.7 path; do not silently switch its production pins to the review-only 0.2.11 source. Use a separately authorized local client and local preview export after version/hash verification.
4. Test the preview in an actual browser: load, map render, input (desktop and touch), party AI, native opening skill selection, boss HP, result, credited Zeny, return/repeat, page reload and persistence. Test browser storage and the pending reward recovery path. Verify normal save is untouched.
5. Do not publish recovered publisher source/assets, preview binaries or a public deployment without the necessary distribution rights. A local export for an authorized client is distinct from public redistribution.

## Scope
The +100 Zeny is a provisional QA amount. MVP marks are local achievements derived from credited receipts, not a native inventory item. Native loot design and distribution authorization remain unresolved. No production release is approved by a source-only or headless QA pass.
