import * as THREE from 'three';
import { MMDLoader } from 'three/addons/loaders/MMDLoader.js';

// ============================================================
// 配置
// ============================================================
const API_BASE = '';
const MODEL_PATH = '/models/星穹铁道—火花2.pmx';

// Agent expression -> PMX morph 名称映射
// 根据实际模型 morph 名称调整
const EXPRESSION_MORPH_MAP = {
  smile:       ['笑い', '微笑', 'smile', '笑'],
  soft_smile:  ['笑い', '微笑', 'smile', '笑'],
  blink:       ['まばたき', '眨眼', 'blink', 'ウィンク'],
  surprised:   ['驚き', '惊讶', 'surprised', 'びっくり'],
  sad_eyes:    ['悲しい', '悲伤', 'sad', '困る'],
  angry_face:  ['怒り', '愤怒', 'angry'],
  thinking_face: ['思考', '想い', 'think'],
  neutral:     [],
};

const ACTION_ANIM_MAP = {
  nod:         { bone: '頭', axis: 'x', angle: 15, speed: 3 },
  shake_head:  { bone: '頭', axis: 'y', angle: 12, speed: 4 },
  wave_hand:   { bone: '右手', axis: 'z', angle: 25, speed: 4 },
  tilt_head:   { bone: '頭', axis: 'z', angle: 12, speed: 2 },
  look_down:   { bone: '頭', axis: 'x', angle: 20, speed: 2 },
  idle:        null,
};

// ============================================================
// 全局状态
// ============================================================
let scene, camera, renderer, clock;
let model = null;
let morphDict = {};
let boneDict = {};
let currentAction = null;
let currentExpression = 'neutral';
let mouseDown = false, mouseX = 0, mouseY = 0;
let cameraAngle = 0, cameraHeight = 12.0, cameraDistance = 30.0;

// ============================================================
// 初始化 Three.js 场景
// ============================================================
function initScene() {
  const container = document.getElementById('canvas-container');

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);

  camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, cameraHeight, cameraDistance);
  camera.lookAt(0, 10, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  // 灯光
  const ambient = new THREE.AmbientLight(0xffffff, 0.5);
  scene.add(ambient);

  const dirLight = new THREE.DirectionalLight(0xfff5e6, 1.0);
  dirLight.position.set(3, 5, -3);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0x99b3ff, 0.4);
  fillLight.position.set(-3, 3, 3);
  scene.add(fillLight);

  const hemiLight = new THREE.HemisphereLight(0xaaddff, 0x332211, 0.3);
  scene.add(hemiLight);

  // 地面网格
  const grid = new THREE.GridHelper(50, 50, 0x333355, 0x222244);
  scene.add(grid);

  clock = new THREE.Clock();

  // 鼠标拖拽旋转
  container.addEventListener('mousedown', e => { mouseDown = true; mouseX = e.clientX; mouseY = e.clientY; });
  container.addEventListener('mousemove', e => {
    if (!mouseDown) return;
    cameraAngle += (e.clientX - mouseX) * 0.005;
    cameraHeight = Math.max(2, Math.min(25, cameraHeight + (e.clientY - mouseY) * 0.05));
    mouseX = e.clientX; mouseY = e.clientY;
    updateCamera();
  });
  container.addEventListener('mouseup', () => { mouseDown = false; });
  container.addEventListener('wheel', e => {
    cameraDistance = Math.max(10, Math.min(80, cameraDistance + e.deltaY * 0.03));
    updateCamera();
  });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
}

function updateCamera() {
  camera.position.x = Math.sin(cameraAngle) * cameraDistance;
  camera.position.z = Math.cos(cameraAngle) * cameraDistance;
  camera.position.y = cameraHeight;
  camera.lookAt(0, 10, 0);
}

// ============================================================
// 加载 PMX 模型
// ============================================================
function loadModel() {
  return new Promise((resolve, reject) => {
    const loader = new MMDLoader();
    const progressText = document.getElementById('loading-progress');

    loader.load(MODEL_PATH, (mmd) => {
      model = mmd;
      scene.add(model);

      // 构建 morph 字典
      if (model.morphTargetDictionary) {
        morphDict = { ...model.morphTargetDictionary };
        console.log('可用 morph:', Object.keys(morphDict));
      }

      // 构建 bone 字典
      if (model.skeleton) {
        model.skeleton.bones.forEach(b => { boneDict[b.name] = b; });
        console.log('可用骨骼:', Object.keys(boneDict));
      }

      hideLoading();
      resolve(model);

    }, (progress) => {
      if (progress.total > 0) {
        const pct = Math.round(progress.loaded / progress.total * 100);
        progressText.textContent = `加载中: ${pct}% (${(progress.loaded / 1024 / 1024).toFixed(1)} MB)`;
      }
    }, (err) => {
      console.error('模型加载失败:', err);
      reject(err);
    });
  });
}

// ============================================================
// 表情驱动
// ============================================================
function setExpression(expressionName) {
  if (!model || !model.morphTargetInfluences) return;

  currentExpression = expressionName;

  // 先将所有 morph 归零
  for (let i = 0; i < model.morphTargetInfluences.length; i++) {
    model.morphTargetInfluences[i] = 0;
  }

  // 查找并设置目标 morph
  const morphNames = EXPRESSION_MORPH_MAP[expressionName] || [];
  for (const name of morphNames) {
    if (name in morphDict) {
      model.morphTargetInfluences[morphDict[name]] = 1.0;
      break;
    }
  }
}

// ============================================================
// 动作驱动（骨骼动画）
// ============================================================
function playAction(actionName, durationMs) {
  const config = ACTION_ANIM_MAP[actionName];
  if (!config) return;

  // 停止当前动作
  if (currentAction) {
    currentAction.active = false;
    resetBonePose(config.bone);
  }

  const bone = boneDict[config.bone];
  if (!bone) {
    console.warn(`骨骼 "${config.bone}" 未找到，跳过动作 ${actionName}`);
    return;
  }

  const action = {
    active: true,
    bone: bone,
    axis: config.axis,
    angle: config.angle * (Math.PI / 180),
    speed: config.speed,
    startTime: clock.getElapsedTime(),
    duration: durationMs / 1000,
    defaultRot: bone.quaternion.clone(),
  };

  currentAction = action;
}

function updateAction() {
  if (!currentAction || !currentAction.active) return;

  const elapsed = clock.getElapsedTime() - currentAction.startTime;
  if (elapsed > currentAction.duration) {
    currentAction.bone.quaternion.copy(currentAction.defaultRot);
    currentAction.active = false;
    currentAction = null;
    return;
  }

  const t = elapsed / currentAction.duration;
  const wave = Math.sin(t * Math.PI * 2 * currentAction.speed);
  const angle = wave * currentAction.angle;

  const q = currentAction.defaultRot.clone();
  const axisVec = currentAction.axis === 'x' ? new THREE.Vector3(1,0,0)
                : currentAction.axis === 'y' ? new THREE.Vector3(0,1,0)
                : new THREE.Vector3(0,0,1);

  const rotQ = new THREE.Quaternion().setFromAxisAngle(axisVec, angle);
  currentAction.bone.quaternion.copy(q.multiply(rotQ));
}

function resetBonePose(boneName) {
  const bone = boneDict[boneName];
  if (bone && currentAction && currentAction.defaultRot) {
    bone.quaternion.copy(currentAction.defaultRot);
  }
}

// ============================================================
// 动画循环
// ============================================================
function animate() {
  requestAnimationFrame(animate);
  updateAction();
  renderer.render(scene, camera);
}

// ============================================================
// 聊天 API
// ============================================================
async function sendMessage(text) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${response.status}`);
  }

  return await response.json();
}

async function resetContext() {
  await fetch(`${API_BASE}/api/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ all: false }),
  });
}

async function healthCheck() {
  const res = await fetch(`${API_BASE}/api/health`);
  return await res.json();
}

// ============================================================
// 聊天 UI
// ============================================================
const messagesDiv = document.getElementById('messages');
const msgInput = document.getElementById('msg-input');
const sendBtn = document.getElementById('send-btn');
const statusBar = document.getElementById('status-bar');

function addMessage(text, type) {
  const div = document.createElement('div');
  div.className = `msg msg-${type}`;
  div.textContent = text;
  messagesDiv.appendChild(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function setUIEnabled(enabled) {
  msgInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
  if (enabled) msgInput.focus();
}

function updateStatusBar(response) {
  statusBar.textContent =
    `表情: ${response.expression} | 动作: ${response.action} | 情绪: ${response.emotion} | 语气: ${response.voice_style}`;
}

async function handleSend() {
  const text = msgInput.value.trim();
  if (!text) return;

  msgInput.value = '';
  addMessage(text, 'user');
  setUIEnabled(false);
  statusBar.textContent = '思考中...';

  try {
    const result = await sendMessage(text);

    // 显示回复
    addMessage(result.text, 'ai');

    // 驱动表情
    setExpression(result.expression);

    // 驱动动作
    playAction(result.action, result.duration);

    // 更新状态栏
    updateStatusBar(result);

  } catch (err) {
    addMessage(`错误: ${err.message}`, 'system');
    console.error(err);
  }

  setUIEnabled(true);
}

sendBtn.addEventListener('click', handleSend);
msgInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

// ============================================================
// 启动
// ============================================================
function showError(msg) {
  const box = document.getElementById('error-box');
  box.textContent = msg;
  box.style.display = 'block';
  setTimeout(() => { box.style.display = 'none'; }, 8000);
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

async function main() {
  initScene();
  animate();

  // 加载模型
  try {
    await loadModel();
    addMessage('模型加载完成！可以开始对话了。', 'system');
  } catch (err) {
    document.getElementById('loading-text').textContent = '模型加载失败';
    document.getElementById('loading-progress').textContent = err.message;
    showError(`模型加载失败: ${err.message}。请确保 PMX 和纹理文件在 web/models/ 目录中。`);
    return;
  }

  // 检查 Agent Server
  try {
    const health = await healthCheck();
    addMessage(`Agent Server 已连接 (${health.model})`, 'system');
    statusBar.textContent = '就绪';
    setUIEnabled(true);
  } catch (err) {
    addMessage('Agent Server 未响应，请先启动: python run_agent_server.py', 'system');
    statusBar.textContent = 'Agent Server 未连接';
    showError('Agent Server 未启动。请运行: python run_agent_server.py');
  }
}

main();
