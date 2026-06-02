/**
 * Emotion Agent - Popup Script
 */
(async function () {
  const statusEl = document.getElementById('status');
  const sizeSlider = document.getElementById('size');
  const sizeVal = document.getElementById('size-val');
  const toggleBtn = document.getElementById('toggle');

  // 检查 Agent Server
  try {
    const resp = await fetch('http://127.0.0.1:8765/health', { signal: AbortSignal.timeout(3000) });
    const data = await resp.json();
    statusEl.className = 'status ok';
    statusEl.textContent = `已连接 (${data.model})`;
  } catch {
    statusEl.className = 'status err';
    statusEl.textContent = 'Agent Server 未启动';
  }

  // 模型大小滑块
  const stored = await chrome.storage.local.get('modelSize');
  const currentSize = stored.modelSize || 250;
  sizeSlider.value = currentSize;
  sizeVal.textContent = currentSize + 'px';

  sizeSlider.addEventListener('input', () => {
    const val = sizeSlider.value;
    sizeVal.textContent = val + 'px';
    chrome.storage.local.set({ modelSize: parseInt(val) });
    // 通知当前 tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'ea-resize', size: parseInt(val) });
      }
    });
  });

  // 显示/隐藏
  toggleBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'ea-toggle' });
      }
    });
  });
})();
