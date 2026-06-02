/**
 * Emotion Agent - Model Viewer (主世界脚本)
 * 运行在页面主世界，直接访问 THREE 和 DOM。
 */
(function () {
  'use strict';

  const BASE = document.currentScript?.src?.replace(/[^/]*$/, '') || '';

  // 状态面板
  const statusBox = document.createElement('div');
  statusBox.style.cssText = `
    position:fixed;top:10px;right:10px;z-index:2147483647;
    background:rgba(0,0,0,0.85);color:#0f0;padding:12px 16px;
    border-radius:8px;font:13px/1.6 monospace;max-width:500px;
    white-space:pre-wrap;word-break:break-all;
    box-shadow:0 2px 12px rgba(0,0,0,0.5);
  `;
  statusBox.textContent = '[EA] 加载中...\n';
  document.body.appendChild(statusBox);

  function log(msg) {
    console.log('[EA]', msg);
    statusBox.textContent += msg + '\n';
  }
  function fail(msg) {
    console.error('[EA]', msg);
    statusBox.textContent += '[ERR] ' + msg + '\n';
    statusBox.style.color = '#f55';
  }

  // 检查 THREE
  if (typeof THREE === 'undefined') {
    fail('THREE 未定义');
    return;
  }
  log('THREE ' + THREE.REVISION);

  if (!THREE.MMDLoader) {
    fail('MMDLoader 未定义');
    return;
  }
  log('MMDLoader 就绪');

  // ---- 创建 DOM ----
  const box = document.createElement('div');
  box.style.cssText = `
    position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
    width:400px;height:550px;z-index:2147483644;
    border-radius:12px;overflow:hidden;
    background:transparent;
    box-shadow:0 8px 40px rgba(0,0,0,0.3);
  `;
  document.body.appendChild(box);

  const canvas = document.createElement('canvas');
  canvas.width = 400; canvas.height = 550;
  canvas.style.cssText = 'width:100%;height:100%;display:block;';
  box.appendChild(canvas);

  const hint = document.createElement('div');
  hint.style.cssText = `
    position:absolute;top:0;left:0;width:100%;height:100%;
    display:flex;align-items:center;justify-content:center;
    color:#8be9fd;font:18px "Microsoft YaHei",sans-serif;pointer-events:none;
    background:transparent;
  `;
  hint.textContent = '加载模型中...';
  box.appendChild(hint);

  // 切换按钮
  const toggle = document.createElement('div');
  toggle.textContent = '💬';
  toggle.title = '显示/隐藏';
  toggle.style.cssText = `
    position:fixed;right:20px;bottom:20px;z-index:2147483647;
    width:50px;height:50px;border-radius:50%;
    background:#8be9fd;color:#1a1a2e;font-size:26px;
    display:flex;align-items:center;justify-content:center;
    cursor:pointer;box-shadow:0 3px 15px rgba(0,0,0,0.4);
    user-select:none;transition:transform 0.15s;
  `;
  let visible = true;
  toggle.onclick = () => {
    visible = !visible;
    box.style.display = visible ? 'block' : 'none';
    chatBox.style.display = visible ? chatBox._vis : 'none';
    toggle.textContent = visible ? '💬' : '👁';
  };
  document.body.appendChild(toggle);

  // 聊天面板
  const chatBox = document.createElement('div');
  chatBox._vis = 'flex';
  chatBox.style.cssText = `
    position:fixed;top:50%;left:50%;
    transform:translate(-50%,-50%) translate(220px,0);
    width:350px;height:550px;z-index:2147483643;
    display:none;flex-direction:column;
    background:rgba(15,15,35,0.95);
    border:1px solid rgba(139,233,253,0.2);
    border-radius:12px;overflow:hidden;
    font:14px/1.5 "Microsoft YaHei",sans-serif;color:#eee;
    box-shadow:0 8px 40px rgba(0,0,0,0.6);
  `;
  chatBox.innerHTML = `
    <div style="padding:14px 16px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center">
      <b style="color:#8be9fd;font-size:15px">Emotion Agent</b>
      <span id="ea-x" style="color:#6272a4;font-size:22px;cursor:pointer">&times;</span>
    </div>
    <div id="ea-st" style="padding:5px 16px;font-size:11px;color:#bd93f9;border-bottom:1px solid rgba(255,255,255,0.05)">就绪</div>
    <div id="ea-msgs" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px"></div>
    <div style="padding:10px 12px;border-top:1px solid rgba(255,255,255,0.1);display:flex;gap:8px">
      <input id="ea-in" placeholder="输入消息..." style="flex:1;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);border-radius:6px;padding:8px 12px;color:#f8f8f2;font-size:13px;outline:none"/>
      <button id="ea-btn" style="background:#8be9fd;color:#1a1a2e;border:none;border-radius:6px;padding:8px 16px;font-weight:bold;font-size:13px;cursor:pointer">发送</button>
    </div>
  `;
  document.body.appendChild(chatBox);

  canvas.onclick = () => {
    const show = chatBox.style.display === 'none';
    chatBox.style.display = show ? 'flex' : 'none';
    chatBox._vis = show ? 'flex' : 'none';
  };
  chatBox.querySelector('#ea-x').onclick = () => {
    chatBox.style.display = 'none';
    chatBox._vis = 'none';
  };

  // ---- Three.js ----
  log('创建渲染器...');
  const scene = new THREE.Scene();
  scene.background = null; // 透明背景

  const camera = new THREE.PerspectiveCamera(40, 400 / 550, 0.1, 200);
  camera.position.set(0, 12, 30);
  camera.lookAt(0, 10, 0);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(400, 550);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.8;

  scene.add(new THREE.AmbientLight(0xffffff, 0.3));
  const dl = new THREE.DirectionalLight(0xfff5e6, 0.5);
  dl.position.set(3, 5, -3);
  scene.add(dl);
  const fl = new THREE.DirectionalLight(0x99b3ff, 0.2);
  fl.position.set(-3, 3, 3);
  scene.add(fl);
  scene.add(new THREE.HemisphereLight(0xaaddff, 0x332211, 0.15));
  log('渲染器就绪');

  // ---- 加载模型 ----
  // 从本地 Web Server 加载模型（chrome-extension:// URL 无法被 XHR 访问）
  const modelPath = 'http://127.0.0.1:8080/models/' + encodeURIComponent('星穹铁道—火花2.pmx');
  log('模型路径: ' + modelPath);

  // 超时检测
  let loadStage = 'init';
  setTimeout(() => {
    if (loadStage !== 'done') fail('加载超时，卡在: ' + loadStage);
  }, 30000);

  let model = null;
  const mmdLoader = new THREE.MMDLoader();

  // 拦截 manager 的加载错误
  const origOnError = mmdLoader.manager.onError;
  mmdLoader.manager.onError = function(url) {
    fail('纹理加载失败: ' + url.split('/').pop());
    if (origOnError) origOnError.call(this, url);
  };

  log('开始加载 PMX...');
  loadStage = 'pmx';

  mmdLoader.load(
    modelPath,
    function (mmd) {
      loadStage = 'done';
      model = mmd;
      scene.add(mmd);
      hint.style.display = 'none';
      log('模型成功! 顶点: ' + (mmd.geometry?.attributes?.position?.count || '?'));
      if (mmd.morphTargetDictionary) {
        log('Morph: ' + Object.keys(mmd.morphTargetDictionary).slice(0, 10).join(', '));
      }
      if (mmd.skeleton) {
        log('Bone: ' + mmd.skeleton.bones.slice(0, 8).map(b => b.name).join(', '));
      }
      window.postMessage({ type: 'ea-ready' }, '*');
      setTimeout(() => statusBox.style.display = 'none', 5000);
    },
    function (p) {
      loadStage = 'downloading';
      if (p.total > 0) {
        const pct = Math.round(p.loaded / p.total * 100);
        hint.textContent = '加载中 ' + pct + '%';
        log('下载: ' + pct + '% (' + Math.round(p.loaded/1024) + 'KB)');
      }
    },
    function (e) {
      fail('模型加载失败: ' + (e.message || e.statusText || JSON.stringify(e)));
    }
  );

  // ---- 表情 & 动作 ----
  const morphMap = {
    smile: ['笑い','微笑','smile','笑'],
    soft_smile: ['笑い','微笑','smile','笑'],
    blink: ['まばたき','眨眼','blink','ウィンク'],
    surprised: ['驚き','惊讶','surprised','びっくり'],
    sad_eyes: ['悲しい','悲伤','sad','困る'],
    angry_face: ['怒り','愤怒','angry'],
    thinking_face: ['思考','想い','think'],
    neutral: [],
  };

  function setExpression(name) {
    if (!model || !model.morphTargetInfluences) return;
    for (let i = 0; i < model.morphTargetInfluences.length; i++) model.morphTargetInfluences[i] = 0;
    const dict = model.morphTargetDictionary || {};
    for (const n of (morphMap[name] || [])) {
      if (n in dict) { model.morphTargetInfluences[dict[n]] = 1; break; }
    }
  }

  let curAction = null;
  function playAction(name, durMs) {
    if (!model || !model.skeleton) return;
    if (curAction) { curAction.active = false; if (curAction.bone) curAction.bone.quaternion.copy(curAction.defQ); }
    const bones = {};
    model.skeleton.bones.forEach(b => bones[b.name] = b);
    const cfg = {
      nod: { b: bones['頭'], ax: 'x', a: 15, sp: 3 },
      shake_head: { b: bones['頭'], ax: 'y', a: 12, sp: 4 },
      wave_hand: { b: bones['右手'], ax: 'z', a: 25, sp: 4 },
      tilt_head: { b: bones['頭'], ax: 'z', a: 12, sp: 2 },
      look_down: { b: bones['頭'], ax: 'x', a: 20, sp: 2 },
    }[name];
    if (!cfg || !cfg.b) return;
    curAction = {
      bone: cfg.b, ax: cfg.ax, angle: cfg.a * Math.PI / 180,
      sp: cfg.sp, t0: performance.now() / 1000, dur: durMs / 1000,
      defQ: cfg.b.quaternion.clone(), active: true,
    };
  }

  // ---- 动画循环 ----
  function animate() {
    requestAnimationFrame(animate);
    if (curAction && curAction.active) {
      const t = (performance.now() / 1000 - curAction.t0) / curAction.dur;
      if (t > 1) { curAction.bone.quaternion.copy(curAction.defQ); curAction.active = false; }
      else {
        const w = Math.sin(t * Math.PI * 2 * curAction.sp) * curAction.angle;
        const q = curAction.defQ.clone();
        const v = curAction.ax === 'x' ? new THREE.Vector3(1,0,0)
                : curAction.ax === 'y' ? new THREE.Vector3(0,1,0)
                : new THREE.Vector3(0,0,1);
        curAction.bone.quaternion.copy(q.multiply(new THREE.Quaternion().setFromAxisAngle(v, w)));
      }
    }
    renderer.render(scene, camera);
  }
  animate();

  // 鼠标旋转
  let md = false, mx = 0, my = 0, cA = 0, cH = 12, cD = 30;
  canvas.oncontextmenu = e => e.preventDefault();
  canvas.onmousedown = e => { if (e.button === 2) { md = true; mx = e.clientX; my = e.clientY; } };
  document.addEventListener('mousemove', e => {
    if (!md) return;
    cA += (e.clientX - mx) * 0.01;
    cH = Math.max(2, Math.min(25, cH + (e.clientY - my) * 0.1));
    mx = e.clientX; my = e.clientY;
    camera.position.set(Math.sin(cA) * cD, cH, Math.cos(cA) * cD);
    camera.lookAt(0, 10, 0);
  });
  document.addEventListener('mouseup', () => md = false);
  canvas.onwheel = e => {
    cD = Math.max(10, Math.min(80, cD + e.deltaY * 0.05));
    camera.position.set(Math.sin(cA) * cD, cH, Math.cos(cA) * cD);
    camera.lookAt(0, 10, 0);
    e.preventDefault();
  };

  // ---- 聊天 ----
  const msgInput = chatBox.querySelector('#ea-in');
  const sendBtn = chatBox.querySelector('#ea-btn');
  const msgsDiv = chatBox.querySelector('#ea-msgs');
  const stBar = chatBox.querySelector('#ea-st');

  function addMsg(text, type) {
    const d = document.createElement('div');
    d.style.cssText = type === 'user'
      ? 'align-self:flex-end;background:#44475a;color:#f8f8f2;padding:8px 12px;border-radius:10px;max-width:85%;font-size:13px;word-break:break-word;'
      : type === 'ai'
      ? 'align-self:flex-start;background:rgba(139,233,253,0.1);border:1px solid rgba(139,233,253,0.15);color:#f8f8f2;padding:8px 12px;border-radius:10px;max-width:85%;font-size:13px;word-break:break-word;'
      : 'align-self:center;color:#6272a4;font-size:11px;padding:2px 0;';
    d.textContent = text;
    msgsDiv.appendChild(d);
    msgsDiv.scrollTop = msgsDiv.scrollHeight;
  }

  async function doSend() {
    const text = msgInput.value.trim();
    if (!text) return;
    msgInput.value = '';
    addMsg(text, 'user');
    msgInput.disabled = sendBtn.disabled = true;
    stBar.textContent = '思考中...';
    try {
      const r = await fetch('http://127.0.0.1:8765/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.error || r.status); }
      const res = await r.json();
      addMsg(res.text, 'ai');
      setExpression(res.expression);
      playAction(res.action, res.duration);
      stBar.textContent = `表情:${res.expression} 动作:${res.action} 情绪:${res.emotion}`;
    } catch (e) {
      addMsg('错误: ' + e.message, 'sys');
      fail('聊天: ' + e.message);
    }
    msgInput.disabled = sendBtn.disabled = false;
    msgInput.focus();
  }
  sendBtn.onclick = doSend;
  msgInput.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); doSend(); } };

  // ---- 监听 content script 消息 ----
  window.addEventListener('message', e => {
    if (e.data?.type === 'ea-cmd') {
      if (e.data.action === 'toggle') {
        visible = !visible;
        box.style.display = visible ? 'block' : 'none';
        chatBox.style.display = visible ? chatBox._vis : 'none';
        toggle.textContent = visible ? '💬' : '👁';
      }
      if (e.data.action === 'setExpression') setExpression(e.data.value);
      if (e.data.action === 'playAction') playAction(e.data.name, e.data.duration);
    }
  });

  log('初始化完成 ✓');
})();
