# Wave 35 — one native destination hub

User report from the published Beta: nearQ's original illustrated Destinations
panel and the green Luyen offline mini-game panel are perceived as unrelated.
Training and Festival must use real gameplay on maps, not menu counters.

Baseline: deployed release 653d950, keep production unchanged.
Goal: preserve original nearQ cards and thumbnails, make both entrypoints
invoke the very same native hub, then connect its three actions to offline
native sessions. Training uses actual target/hit/party behavior. Festival
uses native Emperium map and actual scoring; no online rankings or fabricated
opponent scores. World Boss uses the already tested isolated native MVP route.
Do not reuse official online state, rewards or fake a saved build.

First implementation: explicit --offline-test --offline-native-destinations
toolbar experiment resolves a unique native instance method discovered from
actual labels in the pinned recovered client. It invokes that method rather
than rendering the simulator, and verifies the three cards and no online run.
Ambiguous source/owner fails closed. Existing Beta and old QA paths unchanged.
No card action is rewired in this commit; native festival/training signatures,
saved-build selection and result handling still need review before launch.
The original nearQ visuals are reused only if the runtime probe passes.
