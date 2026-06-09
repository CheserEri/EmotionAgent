"""
MediaPipe 姿态估计模块。
从视频文件或摄像头提取 33 个人体关键点（world landmarks）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class PoseFrame:
    """一帧的姿态估计结果。"""
    frame_index: int
    timestamp: float  # 秒
    landmarks: list[tuple[float, float, float]]  # 33 个 (x, y, z)，单位：米
    visibility: list[float]  # 33 个可见性分数


class PoseEstimator:
    """MediaPipe 姿态估计器。"""

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        smooth_landmarks: bool = True,
    ):
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.smooth_landmarks = smooth_landmarks

        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def estimate_from_video(
        self,
        video_path: str | Path,
        max_frames: int | None = None,
        start_frame: int = 0,
    ) -> Generator[PoseFrame, None, None]:
        """
        从视频文件逐帧提取姿态。

        Args:
            video_path: 视频文件路径
            max_frames: 最大处理帧数，None 表示处理全部
            start_frame: 起始帧号

        Yields:
            PoseFrame: 每帧的姿态数据
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"无法打开视频: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"视频信息: {total_frames} 帧, {fps:.1f} FPS, "
              f"时长 {total_frames / fps:.1f}s")

        # 跳到起始帧
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_idx = start_frame
        processed = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if max_frames is not None and processed >= max_frames:
                    break

                pose_frame = self._process_frame(frame, frame_idx, fps)
                if pose_frame is not None:
                    yield pose_frame

                frame_idx += 1
                processed += 1

                # 进度提示
                if processed % 100 == 0:
                    progress = frame_idx / total_frames * 100 if total_frames > 0 else 0
                    print(f"  处理进度: {processed} 帧 ({progress:.1f}%)")

        finally:
            cap.release()

        print(f"处理完成: 共 {processed} 帧")

    def estimate_from_camera(
        self,
        camera_id: int = 0,
        target_fps: float = 30.0,
    ) -> Generator[PoseFrame, None, None]:
        """
        从摄像头实时提取姿态。

        Args:
            camera_id: 摄像头 ID
            target_fps: 目标帧率

        Yields:
            PoseFrame: 每帧的姿态数据
        """
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开摄像头: {camera_id}")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        frame_idx = 0
        frame_interval = 1.0 / target_fps

        print(f"摄像头已打开 (ID: {camera_id}), 目标帧率: {target_fps} FPS")
        print("按 Ctrl+C 停止")

        try:
            while True:
                start_time = time.monotonic()

                ret, frame = cap.read()
                if not ret:
                    print("摄像头读取失败")
                    break

                pose_frame = self._process_frame(frame, frame_idx, target_fps)
                if pose_frame is not None:
                    yield pose_frame

                frame_idx += 1

                # 帧率控制
                elapsed = time.monotonic() - start_time
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n已停止")
        finally:
            cap.release()

    def estimate_single_frame(self, frame: np.ndarray, frame_index: int = 0) -> PoseFrame | None:
        """处理单帧图像。"""
        return self._process_frame(frame, frame_index, fps=30.0)

    def _process_frame(
        self, frame: np.ndarray, frame_idx: int, fps: float
    ) -> PoseFrame | None:
        """处理单帧，返回 PoseFrame 或 None（如果未检测到姿态）。"""
        # MediaPipe 要求 RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb)

        if results.pose_world_landmarks is None:
            return None

        world_lm = results.pose_world_landmarks.landmark

        landmarks = []
        visibility = []
        for lm in world_lm:
            landmarks.append((lm.x, lm.y, lm.z))
            visibility.append(lm.visibility)

        return PoseFrame(
            frame_index=frame_idx,
            timestamp=frame_idx / fps if fps > 0 else 0.0,
            landmarks=landmarks,
            visibility=visibility,
        )

    def close(self) -> None:
        """释放资源。"""
        if self._pose:
            self._pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ============================================================
# 工具函数
# ============================================================

# MediaPipe 关节点索引
LANDMARK_NAMES = [
    "NOSE",              # 0
    "LEFT_EYE_INNER",    # 1
    "LEFT_EYE",          # 2
    "LEFT_EYE_OUTER",    # 3
    "RIGHT_EYE_INNER",   # 4
    "RIGHT_EYE",         # 5
    "RIGHT_EYE_OUTER",   # 6
    "LEFT_EAR",          # 7
    "RIGHT_EAR",         # 8
    "MOUTH_LEFT",        # 9
    "MOUTH_RIGHT",       # 10
    "LEFT_SHOULDER",     # 11
    "RIGHT_SHOULDER",    # 12
    "LEFT_ELBOW",        # 13
    "RIGHT_ELBOW",       # 14
    "LEFT_WRIST",        # 15
    "RIGHT_WRIST",       # 16
    "LEFT_PINKY",        # 17
    "RIGHT_PINKY",       # 18
    "LEFT_INDEX",        # 19
    "RIGHT_INDEX",       # 20
    "LEFT_THUMB",        # 21
    "RIGHT_THUMB",       # 22
    "LEFT_HIP",          # 23
    "RIGHT_HIP",         # 24
    "LEFT_KNEE",         # 25
    "RIGHT_KNEE",        # 26
    "LEFT_ANKLE",        # 27
    "RIGHT_ANKLE",       # 28
    "LEFT_HEEL",         # 29
    "RIGHT_HEEL",        # 30
    "LEFT_FOOT_INDEX",   # 31
    "RIGHT_FOOT_INDEX",  # 32
]

# 常用关节索引常量
NOSE = 0
LEFT_EAR = 7
RIGHT_EAR = 8
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32


def get_landmark(frame: PoseFrame, index: int) -> np.ndarray:
    """获取指定索引的 landmark 坐标，返回 numpy 数组 [x, y, z]。"""
    lm = frame.landmarks[index]
    return np.array(lm, dtype=np.float64)


def midpoint(frame: PoseFrame, idx_a: int, idx_b: int) -> np.ndarray:
    """两个 landmark 的中点。"""
    return (get_landmark(frame, idx_a) + get_landmark(frame, idx_b)) / 2.0
