/* Force direct /game.html links and refreshes through the Pages bootstrap.
 * A shared Zalo/Chrome URL must install the game's split-asset Service Worker
 * before the Godot loader requests the large WASM/PCK files.
 */
(() => {
  'use strict';
  let handoff = false;
  let storageAvailable = false;
  try {
    storageAvailable = true;
    handoff = !!sessionStorage.getItem('svv-web-handoff');
    sessionStorage.removeItem('svv-web-handoff');
  } catch (_) {
    // Private in-app browsers can block sessionStorage; allow an active worker.
  }
  const controlled = 'serviceWorker' in navigator && !!navigator.serviceWorker.controller;
  if (!controlled || (storageAvailable && !handoff)) {
    location.replace(new URL('./?entry=game', location.href));
  }
})();
