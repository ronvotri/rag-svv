/* Fullscreen and landscape control for the original Godot Web client.
 * Browser orientation locks need fullscreen and a user gesture; iOS and some
 * Zalo in-app browsers do not expose the Screen Orientation lock API.
 */
(() => {
  'use strict';

  const init = () => {
    if (document.getElementById('svv-fullscreen')) return;
    const button = document.createElement('button');
    button.id = 'svv-fullscreen';
    button.type = 'button';
    button.textContent = '⛶';
    Object.assign(button.style, {
      position: 'fixed', top: '12px', right: '12px', zIndex: '2147483647',
      width: '46px', height: '46px', padding: '0',
      borderRadius: '11px', border: '1px solid rgba(255,255,255,.6)',
      color: '#fff', background: 'rgba(17,32,37,.86)',
      font: 'bold 26px system-ui,sans-serif', cursor: 'pointer',
      boxShadow: '0 2px 12px rgba(0,0,0,.3)',
      touchAction: 'manipulation'
    });

    const hint = document.createElement('div');
    hint.id = 'svv-landscape-hint';
    hint.setAttribute('role', 'status');
    hint.setAttribute('aria-live', 'polite');
    hint.textContent = 'Hãy xoay ngang điện thoại để chơi. Nếu máy không tự xoay, bật Tự động xoay trong cài đặt nhanh hoặc mở bằng Chrome.';
    Object.assign(hint.style, {
      position: 'fixed', left: '12px', right: '12px', bottom: '24px',
      zIndex: '2147483646', padding: '12px 18px', borderRadius: '10px',
      background: 'rgba(12,28,32,.93)', border: '1px solid rgba(255,255,255,.6)',
      color: '#fff', font: '500 15px/1.5 system-ui,sans-serif',
      textAlign: 'center', pointerEvents: 'none', display: 'none'
    });
    // Keep the top-right minimap completely visible in landscape mobile.
    // Use responsive horizontal clearance rather than screen-height offsets,
    // so the control does not obstruct the movement/attack joysticks below.
    const positionButton = () => {
      const touch = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
      button.style.right = touch ? 'max(168px, 19vw)' : '12px';
      button.style.top = touch ? 'max(6px, env(safe-area-inset-top, 0px))' : '12px';
      button.style.width = touch ? '44px' : '46px';
      button.style.height = touch ? '44px' : '46px';
    };

    let attemptedLandscape = false;
    const mobile = () => window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    const portrait = () => window.innerHeight > window.innerWidth;
    const sync = () => {
      positionButton();
      const enabled = !!document.fullscreenElement;
      // The exit control belongs to Options (or browser Esc), not a
      // floating button over the minimap while the game is fullscreen.
      button.hidden = enabled;
      button.style.display = enabled ? 'none' : 'block';
      button.textContent = '⛶';
      button.title = 'Toàn màn hình và xoay ngang';
      button.setAttribute('aria-label', button.title);
      hint.style.display = attemptedLandscape && mobile() && portrait() ? 'block' : 'none';
    };

    // Called by the native Godot Options overlay (and browser Esc remains
    // available as a fallback). No permanent full-screen HUD button.
    window.__svvExitFullscreen = async () => {
      if (!document.fullscreenElement) return false;
      if (screen.orientation && typeof screen.orientation.unlock === 'function') {
        try { screen.orientation.unlock(); } catch (_) { /* optional */ }
      }
      try { await document.exitFullscreen(); } catch (_) { return false; }
      sync();
      return true;
    };

    button.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      try {
        if (document.fullscreenElement) {
          if (screen.orientation && typeof screen.orientation.unlock === 'function') {
            try { screen.orientation.unlock(); } catch (_) { /* Browser may reject. */ }
          }
          await document.exitFullscreen();
          attemptedLandscape = false;
        } else if (document.documentElement.requestFullscreen) {
          // A real tap supplies the user activation required by Android Chrome.
          await document.documentElement.requestFullscreen();
          attemptedLandscape = mobile();
          if (mobile() && screen.orientation &&
              typeof screen.orientation.lock === 'function') {
            try {
              await screen.orientation.lock('landscape');
            } catch (error) {
              console.info('Ragnarok: landscape lock unavailable; rotate manually.', error);
            }
          }
        } else {
          attemptedLandscape = mobile();
          console.info('Ragnarok: fullscreen is unavailable in this browser.');
        }
      } catch (error) {
        attemptedLandscape = mobile();
        console.warn('Ragnarok fullscreen unavailable:', error);
      }
      sync();
    });
    document.addEventListener('fullscreenchange', () => {
      if (!document.fullscreenElement) attemptedLandscape = false;
      sync();
    });
    window.addEventListener('resize', sync, { passive: true });
    if (screen.orientation && screen.orientation.addEventListener) {
      screen.orientation.addEventListener('change', sync);
    }
    document.body.appendChild(hint);
    document.body.appendChild(button);
    sync();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
