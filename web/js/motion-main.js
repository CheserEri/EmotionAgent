/**
 * Motion Capture 主入口
 * 三维场景 + MotionPlayer + UI 控制
 */
import * as THREE from 'three';
import { MMDLoader } from 'three/addons/loaders/MMDLoader.js';
import { MotionPlayer } from './motion-player.js';

// ============================================================
// 配置
// ============================================================
const MODEL_PATH = '/models/星穹铁道—火花2.pmx';
const WS_URL = 'ws://127.0.0.1:8766';

// ============================================================
// 全局状态
// ============================================================
let scene, camera, renderer, clock;
let model = null;
let boneDict = {};
let motionPlayer = null;

// 鼠标控制
let mouseDown = false, mouseX = 0, mouseY = 0;
let cameraAngle = 0, cameraHeight = 12.0, cameraDistance = 30.0;

// UI 元素
const elements = {};

// ============================================================
// Three.js 场景
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
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));

  const dirLight = new THREE.DirectionalLight(0xfff5e6, 1.0);
  dirLight.position.set(3, 5, -3);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0x99b3ff, 0.4);
  fillLight.position.set(-3, 3, 3);
  scene.add(fillLight);

  scene.add(new THREE.HemisphereLight(0xaaddff, 0x332211, 0.3));

  // 地面
  scene.add(new THREE.GridHelper(50, 50, 0x333355, 0x222244));

  clock = new THREE.Clock();

  // 鼠标控制
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
// 模型加载
// ============================================================
function loadModel() {
  return new Promise((resolve, reject) => {
    const loader = new MMDLoader();
    const progressText = document.getElementById('loading-progress');

    loader.load(MODEL_PATH, (mmd) => {
      model = mmd;
      scene.add(model);

      // 构建骨骼字典
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
// MotionPlayer 初始化
// ============================================================
function initMotionPlayer() {
  motionPlayer = new MotionPlayer(model, boneDict, {
    wsUrl: WS_URL,
    onConnect: () => {
      setWsStatus('connected', '已连接');
      addLog('已连接到 Motion Server', 'success');
      updateButtons();
    },
    onDisconnect: () => {
      setWsStatus('disconnected', '未连接');
      addLog('与 Motion Server 断开', 'warn');
      updateButtons();
    },
    onStart: (msg) => {
      addLog(`开始处理: ${msg.source}`, 'info');
      elements.progressContainer.classList.add('active');
      elements.statSource.textContent = msg.source === 'video' ? '视频' : '摄像头';
      updateButtons();
    },
    onFrame: (msg) => {
      updateStats(msg);
    },
    onComplete: (msg) => {
      addLog(`处理完成: ${msg.frames} 帧, ${msg.elapsed}s, ${msg.fps} fps`, 'success');
      elements.progressContainer.classList.remove('active');
      updateButtons();
    },
    onError: (err) => {
      addLog(`错误: ${err.message}`, 'error');
    },
  });
}

// ============================================================
// UI 控制
// ============================================================
function initUI() {
  // 缓存 UI 元素
  elements.wsDot = document.getElementById('ws-dot');
  elements.wsText = document.getElementById('ws-text');
  elements.fpsDisplay = document.getElementById('fps-display');
  elements.videoFileInput = document.getElementById('video-file-input');
  elements.videoPreview = document.getElementById('video-preview');
  elements.videoPathInput = document.getElementById('video-path-input');
  elements.startFrame = document.getElementById('start-frame');
  elements.maxFrames = document.getElementById('max-frames');
  elements.btnProcessVideo = document.getElementById('btn-process-video');
  elements.btnStop = document.getElementById('btn-stop');
  elements.cameraId = document.getElementById('camera-id');
  elements.cameraFps = document.getElementById('camera-fps');
  elements.btnStartCamera = document.getElementById('btn-start-camera');
  elements.progressContainer = document.getElementById('progress-container');
  elements.progressFill = document.getElementById('progress-fill');
  elements.progressText = document.getElementById('progress-text');
  elements.statFrames = document.getElementById('stat-frames');
  elements.statFps = document.getElementById('stat-fps');
  elements.statCurrent = document.getElementById('stat-current');
  elements.statSource = document.getElementById('stat-source');
  elements.btnResetPose = document.getElementById('btn-reset-pose');
  elements.btnReconnect = document.getElementById('btn-reconnect');
  elements.logArea = document.getElementById('log-area');

  // 视频文件选择
  elements.videoFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // 显示预览
    const url = URL.createObjectURL(file);
    elements.videoPreview.src = url;
    elements.videoPreview.classList.add('active');

    // 注意：浏览器端无法直接访问本地文件路径
    // 需要用户手动输入服务器端路径，或通过上传机制
    elements.videoPathInput.placeholder = `已选择: ${file.name} (请在服务器端输入完整路径)`;
    addLog(`已选择文件: ${file.name}`, 'info');
    addLog('注意：请在下方输入该文件在服务器上的完整路径', 'warn');
  });

  // 处理视频
  elements.btnProcessVideo.addEventListener('click', () => {
    const path = elements.videoPathInput.value.trim();
    if (!path) {
      addLog('请输入视频文件路径', 'error');
      return;
    }

    const startFrame = parseInt(elements.startFrame.value) || 0;
    const maxFrames = parseInt(elements.maxFrames.value) || null;

    addLog(`请求处理视频: ${path}`, 'info');
    motionPlayer.processVideo(path, { startFrame, maxFrames });
    setWsStatus('playing', '处理中...');
  });

  // 停止
  elements.btnStop.addEventListener('click', () => {
    motionPlayer.stop();
    addLog('已发送停止命令', 'warn');
  });

  // 启动摄像头
  elements.btnStartCamera.addEventListener('click', () => {
    const cameraId = parseInt(elements.cameraId.value) || 0;
    const fps = parseFloat(elements.cameraFps.value) || 30;
    addLog(`请求启动摄像头: ID=${cameraId}, FPS=${fps}`, 'info');
    motionPlayer.startCamera({ cameraId, fps });
    setWsStatus('playing', '摄像头');
  });

  // 重置姿态
  elements.btnResetPose.addEventListener('click', () => {
    motionPlayer.resetPose();
    addLog('已重置模型姿态', 'info');
  });

  // 重连
  elements.btnReconnect.addEventListener('click', () => {
    addLog('正在重连...', 'info');
    motionPlayer.connect();
  });
}

function setWsStatus(status, text) {
  elements.wsDot.className = 'status-dot';
  if (status === 'connected') elements.wsDot.classList.add('connected');
  if (status === 'playing') elements.wsDot.classList.add('playing');
  elements.wsText.textContent = text;
}

function updateButtons() {
  const connected = motionPlayer && motionPlayer.connected;
  const playing = motionPlayer && motionPlayer.playing;

  elements.btnProcessVideo.disabled = !connected || playing;
  elements.btnStop.disabled = !playing;
  elements.btnStartCamera.disabled = !connected || playing;
}

function updateStats(msg) {
  const status = motionPlayer.getStatus();
  elements.statFrames.textContent = status.framesReceived;
  elements.statFps.textContent = status.fps || '--';
  elements.statCurrent.textContent = msg.frame;
  elements.fpsDisplay.textContent = `${status.fps || '--'} FPS`;
}

function addLog(text, type = 'info') {
  const line = document.createElement('div');
  line.className = `log-${type}`;
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${text}`;
  elements.logArea.appendChild(line);
  elements.logArea.scrollTop = elements.logArea.scrollHeight;

  // 限制日志行数
  while (elements.logArea.children.length > 100) {
    elements.logArea.removeChild(elements.logArea.firstChild);
  }
}

// ============================================================
// 动画循环
// ============================================================
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}

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
  } catch (err) {
    document.getElementById('loading-text').textContent = '模型加载失败';
    document.getElementById('loading-progress').textContent = err.message;
    showError(`模型加载失败: ${err.message}`);
    return;
  }

  // 初始化 MotionPlayer
  initMotionPlayer();

  // 初始化 UI
  initUI();

  // 自动连接
  addLog('正在连接 Motion Server...', 'info');
  motionPlayer.connect();
}

main();
