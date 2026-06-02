/**
 * Emotion Agent - Content Script v4
 * 通过 script 标签注入，所有逻辑在页面主世界执行。
 */
(async function () {
  'use strict';
  if (window.__eaInjected) return;
  window.__eaInjected = true;

  const BASE = chrome.runtime.getURL('');

  function inject(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error('加载失败: ' + src.split('/').pop()));
      (document.head || document.documentElement).appendChild(s);
    });
  }

  // 注入模型路径（供 model-viewer 读取）
  const pathEl = document.createElement('meta');
  pathEl.id = 'ea-model-path';
  pathEl.dataset.path = BASE + 'models/sparkle.pmx';
  document.documentElement.appendChild(pathEl);

  try {
    // 按顺序注入：Three.js -> bundle -> model-viewer
    await inject(BASE + 'lib/three.min.js');
    await inject(BASE + 'lib/bundle.js');
    await inject(BASE + 'model-viewer.js');
    console.log('[EA] 脚本注入完成');
  } catch (e) {
    console.error('[EA] 注入失败:', e);
  }

  // 转发 popup 消息到主世界
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'ea-toggle') {
      window.postMessage({ type: 'ea-cmd', action: 'toggle' }, '*');
    }
  });
})();
