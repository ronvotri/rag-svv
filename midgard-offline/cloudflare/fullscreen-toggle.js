/* Small, accessible fullscreen control for the original Godot Web export.
 * Does not scale or replace the game canvas, alter saves, or touch gameplay.
 */
(() => {
  'use strict';
  const init = () => {
    if (document.getElementById('svv-fullscreen')) return;
    const button = document.createElement('button');
    button.id = 'svv-fullscreen';
    button.type = 'button';
    button.title = 'Phóng lớn trò chơi (toàn màn hình)';
    button.setAttribute('aria-label', 'Bật toàn màn hình');
    button.textContent = '⛶';
    Object.assign(button.style, {
      position: 'fixed', top: '12px', right: '12px', zIndex: '2147483647',
      width: '42px', height: '42px', padding: '0',
      borderRadius: '11px', border: '1px solid rgba(255,255,255,.6)',
      color: '#fff', background: 'rgba(17,32,37,.8)',
      font: 'bold 26px system-ui,sans-serif', cursor: 'pointer',
      boxShadow: '0 2px 12px rgba(0,0,0,.3)',
      touchAction: 'manipulation'
    });
    const sync = () => {
      const enabled = Boolean(document.fullscreenElement);
      button.textContent = enabled ? '⤢' : '⛶';
      button.title = enabled ? 'Thoát toàn màn hình' : 'Phóng lớn trò chơi (toàn màn hình)';
      button.setAttribute('aria-label', button.title);
    };
    button.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      try {
        if (document.fullscreenElement) {
          await document.exitFullscreen();
        } else if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
        } else {
          button.title = 'Trình duyệt không hỗ trợ toàn màn hình. Trên PC hãy thử F11.';
        }
      } catch (err) {
        console.warn('Ragnarok fullscreen unavailable:', err);
        button.title = 'Không thể phóng lớn. Trên PC hãy thử F11.';
      }
      sync();
    });
    document.addEventListener('fullscreenchange', sync);
    document.body.appendChild(button);
    sync();
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();
