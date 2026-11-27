# Web Beta — manual release from Wave 34

Build #8 (45937128577) validated 0.2.11 export + actual Pages staging,
64 files, max 16 MiB, consistent initial splash. QA #21 and #23 passed;
#24 stopped during candidate download before gameplay. This is not a browser pass.

The existing publish workflow on this branch is now MANUAL ONLY.
Use Actions > Ragnarok SVV - publish original Web (Pages Free) > Run workflow,
select feature/offline-cards-unique-npc-wave34, and confirm the redistribution
rights checkbox only if true. Main and release/ragnarok-web are unchanged.
The old release pipeline must not be triggered because it uses obsolete pins.

The job checks out the selected commit, rebuilds via the verified direct-base
0.2.11 export path, retains the staged package only in the runner, validates
manifest/splash/size, and then deploys to the existing Pages project only after
the rights gate and configured web-production environment checks. No artifact
containing game data is uploaded to GitHub.

Beta uses its own test profile and does not migrate/delete the old player
profile. Back up saves before trying it. Browser/device and Save reload QA
remain required; portrait likeness and signature NPC hats are not approved.
Do not claim a release before actual Cloudflare deployment success.
