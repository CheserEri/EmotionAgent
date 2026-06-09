/**
 * Motion Player - WebSocket 骨骼动画驱动模块
 * 从 Motion WebSocket 服务接收骨骼数据并驱动 PMX 模型。
 */
import * as THREE from 'three';

// ============================================================
// 配置
// ============================================================
const DEFAULT_WS_URL = 'ws://127.0.0.1:8766';

// 骨骼名称映射（Python 端的骨骼名 → Three.js 骨骼名）
// 通常 PMX 骨骼名在 Three.js 中保持不变
const BONE_NAME_MAP = {
  'センター': 'センター',
  '上半身': '上半身',
  '上半身2': '上半身2',
  '首': '首',
  '頭': '頭',
  '左腕': '左腕',
  '左ひじ': '左ひじ',
  '右腕': '右腕',
  '右ひじ': '右ひじ',
  '左足': '左足',
  '左ひざ': '左ひざ',
  '右足': '右足',
  '右ひざ': '右ひざ',
};

// ============================================================
// MotionPlayer 类
// ============================================================
export class MotionPlayer {
  /**
   * @param {THREE.SkinnedMesh} model - PMX 模型（由 MMDLoader 加载）
   * @param {Object} boneDict - 骨骼字典 { name: THREE.Bone }
   * @param {Object} options - 配置选项
   */
  constructor(model, boneDict, options = {}) {
    this.model = model;
    this.boneDict = boneDict;
    this.wsUrl = options.wsUrl || DEFAULT_WS_URL;
    this.autoReconnect = options.autoReconnect !== false;

    this.ws = null;
    this.connected = false;
    this.playing = false;
    this.currentFrame = 0;
    this.frameCount = 0;
    this.source = null; // 'video' | 'camera'

    // 默认骨骼姿态（用于重置）
    this._defaultQuats = {};
    this._defaultPositions = {};
    this._saveDefaultPose();

    // 回调
    this.onConnect = options.onConnect || null;
    this.onDisconnect = options.onDisconnect || null;
    this.onFrame = options.onFrame || null;
    this.onStart = options.onStart || null;
    this.onComplete = options.onComplete || null;
    this.onError = options.onError || null;

    // 统计
    this.stats = {
      framesReceived: 0,
      lastFrameTime: 0,
      fps: 0,
      latency: 0,
    };
    this._fpsCounter = { frames: 0, lastTime: performance.now() };
  }

  /**
   * 保存默认骨骼姿态
   */
  _saveDefaultPose() {
    for (const [name, bone] of Object.entries(this.boneDict)) {
      this._defaultQuats[name] = bone.quaternion.clone();
      this._defaultPositions[name] = bone.position.clone();
    }
  }

  /**
   * 连接到 WebSocket 服务
   */
  connect(wsUrl) {
    if (wsUrl) this.wsUrl = wsUrl;

    if (this.ws) {
      this.ws.close();
    }

    console.log(`MotionPlayer: 连接 ${this.wsUrl}`);
    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      this.connected = true;
      console.log('MotionPlayer: 已连接');
      if (this.onConnect) this.onConnect();
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.playing = false;
      console.log('MotionPlayer: 已断开');
      if (this.onDisconnect) this.onDisconnect();
    };

    this.ws.onerror = (err) => {
      console.error('MotionPlayer: WebSocket 错误', err);
      if (this.onError) this.onError(err);
    };

    this.ws.onmessage = (event) => {
      this._handleMessage(event.data);
    };
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this.playing = false;
  }

  /**
   * 处理服务端消息
   */
  _handleMessage(data) {
    let msg;
    try {
      msg = JSON.parse(data);
    } catch (e) {
      console.error('MotionPlayer: 无效的 JSON', data);
      return;
    }

    switch (msg.type) {
      case 'start':
        this.playing = true;
        this.source = msg.source;
        this.frameCount = 0;
        console.log(`MotionPlayer: 开始处理 (${msg.source})`);
        if (this.onStart) this.onStart(msg);
        break;

      case 'frame':
        this._applyFrame(msg);
        this.stats.framesReceived++;
        this.currentFrame = msg.frame;
        this.frameCount++;

        // FPS 计算
        this._fpsCounter.frames++;
        const now = performance.now();
        if (now - this._fpsCounter.lastTime >= 1000) {
          this.stats.fps = this._fpsCounter.frames;
          this._fpsCounter.frames = 0;
          this._fpsCounter.lastTime = now;
        }

        if (this.onFrame) this.onFrame(msg);
        break;

      case 'complete':
        this.playing = false;
        console.log(`MotionPlayer: 处理完成 (${msg.frames} 帧, ${msg.elapsed}s, ${msg.fps} fps)`);
        if (this.onComplete) this.onComplete(msg);
        break;

      case 'stopped':
        this.playing = false;
        console.log('MotionPlayer: 已停止');
        break;

      case 'error':
        console.error('MotionPlayer: 服务端错误', msg.message);
        if (this.onError) this.onError(new Error(msg.message));
        break;

      case 'pong':
        break;

      default:
        console.warn('MotionPlayer: 未知消息类型', msg.type);
    }
  }

  /**
   * 将一帧骨骼数据应用到模型
   */
  _applyFrame(msg) {
    const bones = msg.bones;
    if (!bones) return;

    for (const [boneName, data] of Object.entries(bones)) {
      // 尝试名称映射
      const mappedName = BONE_NAME_MAP[boneName] || boneName;
      const bone = this.boneDict[mappedName];

      if (!bone) {
        // 尝试直接查找
        continue;
      }

      if ('px' in data) {
        // 位置骨骼（如 センター）
        bone.position.set(data.px * 10, data.py * 10, data.pz * 10);
      } else if ('x' in data) {
        // 旋转骨骼
        bone.quaternion.set(data.x, data.y, data.z, data.w);
      }
    }
  }

  /**
   * 发送命令到服务端
   */
  _send(command) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('MotionPlayer: 未连接');
      return false;
    }
    this.ws.send(JSON.stringify(command));
    return true;
  }

  /**
   * 请求处理视频文件
   */
  processVideo(videoPath, options = {}) {
    return this._send({
      command: 'process_video',
      path: videoPath,
      start_frame: options.startFrame || 0,
      max_frames: options.maxFrames || null,
      export_vmd: options.exportVmd || null,
    });
  }

  /**
   * 请求启动摄像头
   */
  startCamera(options = {}) {
    return this._send({
      command: 'start_camera',
      camera_id: options.cameraId || 0,
      fps: options.fps || 30.0,
    });
  }

  /**
   * 停止当前处理
   */
  stop() {
    return this._send({ command: 'stop' });
  }

  /**
   * 重置模型到默认姿态
   */
  resetPose() {
    for (const [name, bone] of Object.entries(this.boneDict)) {
      if (this._defaultQuats[name]) {
        bone.quaternion.copy(this._defaultQuats[name]);
      }
      if (this._defaultPositions[name]) {
        bone.position.copy(this._defaultPositions[name]);
      }
    }
  }

  /**
   * 获取状态
   */
  getStatus() {
    return {
      connected: this.connected,
      playing: this.playing,
      source: this.source,
      currentFrame: this.currentFrame,
      frameCount: this.frameCount,
      fps: this.stats.fps,
      framesReceived: this.stats.framesReceived,
    };
  }
}
