"""
骨骼映射模块。
将 MediaPipe 33 个 world landmarks 转换为 PMX 骨骼四元数。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from cli_avatar.pose_estimator import (
    PoseFrame,
    NOSE, LEFT_EAR, RIGHT_EAR,
    LEFT_SHOULDER, RIGHT_SHOULDER,
    LEFT_ELBOW, RIGHT_ELBOW,
    LEFT_WRIST, RIGHT_WRIST,
    LEFT_HIP, RIGHT_HIP,
    LEFT_KNEE, RIGHT_KNEE,
    LEFT_ANKLE, RIGHT_ANKLE,
    LEFT_HEEL, RIGHT_HEEL,
    LEFT_FOOT_INDEX, RIGHT_FOOT_INDEX,
    midpoint,
    get_landmark,
)


# ============================================================
# 四元数工具（纯 numpy，无需 scipy）
# ============================================================

def quat_from_axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    """从轴角创建四元数 [x, y, z, w]。"""
    axis = axis / (np.linalg.norm(axis) + 1e-10)
    half = angle_rad / 2.0
    s = math.sin(half)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, math.cos(half)])


def quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """四元数乘法 q1 * q2，[x, y, z, w] 格式。"""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])


def quat_conjugate(q: np.ndarray) -> np.ndarray:
    """四元数共轭。"""
    return np.array([-q[0], -q[1], -q[2], q[3]])


def quat_normalize(q: np.ndarray) -> np.ndarray:
    """归一化四元数。"""
    n = np.linalg.norm(q)
    if n < 1e-10:
        return np.array([0.0, 0.0, 0.0, 1.0])
    return q / n


def quat_from_unit_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """
    计算将 v_from 旋转到 v_to 的四元数。
    两个向量必须是单位向量。
    """
    v_from = v_from / (np.linalg.norm(v_from) + 1e-10)
    v_to = v_to / (np.linalg.norm(v_to) + 1e-10)

    dot = np.clip(np.dot(v_from, v_to), -1.0, 1.0)

    if dot > 0.9999:
        # 几乎同向，返回单位四元数
        return np.array([0.0, 0.0, 0.0, 1.0])

    if dot < -0.9999:
        # 几乎反向，找一个垂直轴
        ortho = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(v_from, ortho)) > 0.9:
            ortho = np.array([0.0, 1.0, 0.0])
        axis = np.cross(v_from, ortho)
        axis = axis / (np.linalg.norm(axis) + 1e-10)
        return np.array([axis[0], axis[1], axis[2], 0.0])

    axis = np.cross(v_from, v_to)
    w = 1.0 + dot
    q = np.array([axis[0], axis[1], axis[2], w])
    return quat_normalize(q)


def rotate_vector_by_quat(v: np.ndarray, q: np.ndarray) -> np.ndarray:
    """用四元数旋转向量。q = [x, y, z, w]。"""
    qv = np.array([v[0], v[1], v[2], 0.0])
    qc = quat_conjugate(q)
    result = quat_multiply(quat_multiply(q, qv), qc)
    return result[:3]


# ============================================================
# 骨骼定义
# ============================================================

@dataclass
class BoneDef:
    """PMX 骨骼定义。"""
    name: str                     # PMX 骨骼名（日文）
    parent_landmark: int          # 父关节 landmark 索引
    child_landmark: int           # 子关节 landmark 索引
    rest_direction: np.ndarray    # T-pose 下的骨骼方向（单位向量）
    twist_axis: str = "none"      # 扭转约束轴："none", "x", "y", "z"
    use_midpoint_parent: int = -1  # 如果 >= 0，与 parent_landmark 取中点作为骨骼起点
    use_midpoint_child: int = -1   # 如果 >= 0，与 child_landmark 取中点作为骨骼终点
    position_bone: bool = False   # 是否为位置骨骼（如 センター）


# PMX 标准骨骼定义
# rest_direction 是 T-pose 下的骨骼方向（MediaPipe 坐标系：Y 向下，Z 向摄像头）
# 注意：这里的方向是"从父关节指向子关节"
PMX_BONE_DEFS: list[BoneDef] = [
    # 躯干
    BoneDef(
        name="センター",
        parent_landmark=LEFT_HIP, child_landmark=LEFT_HIP,
        rest_direction=np.array([0.0, 1.0, 0.0]),
        position_bone=True,
        use_midpoint_parent=LEFT_HIP,
        use_midpoint_child=RIGHT_HIP,
    ),
    BoneDef(
        name="上半身",
        parent_landmark=LEFT_HIP, child_landmark=LEFT_SHOULDER,
        rest_direction=np.array([0.0, -1.0, 0.0]),
        use_midpoint_parent=LEFT_HIP,
        use_midpoint_child=RIGHT_HIP,
        use_midpoint_child_as_end=LEFT_SHOULDER,
    ),
    BoneDef(
        name="上半身2",
        parent_landmark=LEFT_SHOULDER, child_landmark=NOSE,
        rest_direction=np.array([0.0, -1.0, 0.0]),
        use_midpoint_parent=LEFT_SHOULDER,
        use_midpoint_child=RIGHT_SHOULDER,
    ),
    BoneDef(
        name="首",
        parent_landmark=LEFT_EAR, child_landmark=NOSE,
        rest_direction=np.array([0.0, -1.0, 0.0]),
        use_midpoint_parent=LEFT_EAR,
        use_midpoint_child=RIGHT_EAR,
    ),
    BoneDef(
        name="頭",
        parent_landmark=LEFT_EAR, child_landmark=NOSE,
        rest_direction=np.array([0.0, -1.0, 0.0]),
        use_midpoint_parent=LEFT_EAR,
        use_midpoint_child=RIGHT_EAR,
    ),

    # 左臂
    BoneDef(
        name="左腕",
        parent_landmark=LEFT_SHOULDER, child_landmark=LEFT_ELBOW,
        rest_direction=np.array([-1.0, 0.0, 0.0]),  # T-pose 左臂水平向左
    ),
    BoneDef(
        name="左ひじ",
        parent_landmark=LEFT_ELBOW, child_landmark=LEFT_WRIST,
        rest_direction=np.array([-1.0, 0.0, 0.0]),
        twist_axis="x",
    ),

    # 右臂
    BoneDef(
        name="右腕",
        parent_landmark=RIGHT_SHOULDER, child_landmark=RIGHT_ELBOW,
        rest_direction=np.array([1.0, 0.0, 0.0]),  # T-pose 右臂水平向右
    ),
    BoneDef(
        name="右ひじ",
        parent_landmark=RIGHT_ELBOW, child_landmark=RIGHT_WRIST,
        rest_direction=np.array([1.0, 0.0, 0.0]),
        twist_axis="x",
    ),

    # 左腿
    BoneDef(
        name="左足",
        parent_landmark=LEFT_HIP, child_landmark=LEFT_KNEE,
        rest_direction=np.array([0.0, 1.0, 0.0]),  # T-pose 腿垂直向下
    ),
    BoneDef(
        name="左ひざ",
        parent_landmark=LEFT_KNEE, child_landmark=LEFT_ANKLE,
        rest_direction=np.array([0.0, 1.0, 0.0]),
        twist_axis="y",
    ),

    # 右腿
    BoneDef(
        name="右足",
        parent_landmark=RIGHT_HIP, child_landmark=RIGHT_KNEE,
        rest_direction=np.array([0.0, 1.0, 0.0]),
    ),
    BoneDef(
        name="右ひざ",
        parent_landmark=RIGHT_KNEE, child_landmark=RIGHT_ANKLE,
        rest_direction=np.array([0.0, 1.0, 0.0]),
        twist_axis="y",
    ),
]


# ============================================================
# 骨骼映射器
# ============================================================

@dataclass
class SmoothFilter:
    """指数移动平均平滑滤波器。"""
    alpha: float = 0.3  # 平滑系数，越小越平滑
    _prev: np.ndarray | None = field(default=None, repr=False)

    def filter(self, current: np.ndarray) -> np.ndarray:
        if self._prev is None:
            self._prev = current.copy()
            return current
        smoothed = self.alpha * current + (1.0 - self.alpha) * self._prev
        self._prev = smoothed.copy()
        return smoothed

    def reset(self) -> None:
        self._prev = None


class MotionMapper:
    """将 MediaPipe landmarks 转换为 PMX 骨骼四元数。"""

    def __init__(
        self,
        bone_defs: list[BoneDef] | None = None,
        smooth_alpha: float = 0.4,
        coord_flip_y: bool = True,
        coord_flip_z: bool = True,
    ):
        self.bone_defs = bone_defs or PMX_BONE_DEFS
        self.smooth_alpha = smooth_alpha
        self.coord_flip_y = coord_flip_y
        self.coord_flip_z = coord_flip_z

        # 每根骨骼的平滑滤波器
        self._filters: dict[str, SmoothFilter] = {}
        for bd in self.bone_defs:
            if bd.position_bone:
                self._filters[bd.name] = SmoothFilter(alpha=smooth_alpha)
            else:
                self._filters[bd.name] = SmoothFilter(alpha=smooth_alpha)

    def map_frame(self, frame: PoseFrame) -> dict[str, dict[str, float]]:
        """
        将一帧 landmarks 转换为骨骼数据。

        返回格式：
        {
            "bone_name": {
                "x": float, "y": float, "z": float, "w": float,  # 四元数
                # 或对于位置骨骼：
                "px": float, "py": float, "pz": float,  # 位置偏移
            }
        }
        """
        result = {}

        for bd in self.bone_defs:
            if bd.position_bone:
                bone_data = self._compute_position(frame, bd)
            else:
                bone_data = self._compute_rotation(frame, bd)

            if bone_data is not None:
                # 平滑滤波
                values = np.array(list(bone_data.values()))
                smoothed = self._filters[bd.name].filter(values)
                keys = list(bone_data.keys())
                result[bd.name] = {k: float(v) for k, v in zip(keys, smoothed)}
            else:
                # landmark 不可见，保持上一帧数据
                if bd.name in self._filters and self._filters[bd.name]._prev is not None:
                    prev = self._filters[bd.name]._prev
                    if bd.position_bone:
                        result[bd.name] = {"px": float(prev[0]), "py": float(prev[1]), "pz": float(prev[2])}
                    else:
                        result[bd.name] = {"x": float(prev[0]), "y": float(prev[1]), "z": float(prev[2]), "w": float(prev[3])}

        return result

    def _convert_coords(self, pos: np.ndarray) -> np.ndarray:
        """MediaPipe 坐标系 → Three.js/PMX 坐标系。"""
        x, y, z = pos
        if self.coord_flip_y:
            y = -y
        if self.coord_flip_z:
            z = -z
        return np.array([x, y, z])

    def _get_bone_start(self, frame: PoseFrame, bd: BoneDef) -> np.ndarray:
        """获取骨骼起点位置。"""
        if bd.use_midpoint_parent >= 0:
            return self._convert_coords(
                midpoint(frame, bd.use_midpoint_parent, bd.parent_landmark)
                if bd.use_midpoint_parent != bd.parent_landmark
                else get_landmark(frame, bd.parent_landmark)
            )
        return self._convert_coords(get_landmark(frame, bd.parent_landmark))

    def _get_bone_end(self, frame: PoseFrame, bd: BoneDef) -> np.ndarray:
        """获取骨骼终点位置。"""
        if bd.use_midpoint_child >= 0:
            return self._convert_coords(
                midpoint(frame, bd.use_midpoint_child, bd.child_landmark)
                if bd.use_midpoint_child != bd.child_landmark
                else get_landmark(frame, bd.child_landmark)
            )
        return self._convert_coords(get_landmark(frame, bd.child_landmark))

    def _compute_position(self, frame: PoseFrame, bd: BoneDef) -> dict[str, float] | None:
        """计算位置骨骼（如 センター）的位置偏移。"""
        if frame.visibility[bd.parent_landmark] < 0.3:
            return None

        pos = self._get_bone_start(frame, bd)
        return {"px": pos[0], "py": pos[1], "pz": pos[2]}

    def _compute_rotation(self, frame: PoseFrame, bd: BoneDef) -> dict[str, float] | None:
        """计算旋转骨骼的四元数。"""
        # 检查可见性
        if frame.visibility[bd.parent_landmark] < 0.3 or frame.visibility[bd.child_landmark] < 0.3:
            return None

        start = self._get_bone_start(frame, bd)
        end = self._get_bone_end(frame, bd)

        # 当前骨骼方向
        direction = end - start
        dir_len = np.linalg.norm(direction)
        if dir_len < 1e-6:
            return None
        direction = direction / dir_len

        # T-pose 参考方向
        rest_dir = bd.rest_direction / (np.linalg.norm(bd.rest_direction) + 1e-10)

        # 计算旋转
        quat = quat_from_unit_vectors(rest_dir, direction)

        # 扭转约束：移除绕骨骼轴的旋转分量
        if bd.twist_axis != "none":
            quat = self._constrain_twist(quat, direction, bd.twist_axis)

        return {"x": quat[0], "y": quat[1], "z": quat[2], "w": quat[3]}

    def _constrain_twist(
        self, quat: np.ndarray, bone_dir: np.ndarray, twist_axis: str
    ) -> np.ndarray:
        """
        约束骨骼的扭转自由度。
        通过分解四元数为摆动（swing）和扭转（twist）分量，只保留摆动。
        """
        # 将四元数分解为 swing + twist
        # twist 是绕 bone_dir 轴的旋转
        # swing 是其余部分

        # 投影旋转轴到 bone_dir
        if abs(quat[3]) > 0.9999:
            return quat  # 几乎无旋转

        # 提取旋转轴和角度
        sin_half = math.sqrt(1.0 - quat[3] * quat[3])
        if sin_half < 1e-6:
            return quat

        axis = np.array([quat[0], quat[1], quat[2]]) / sin_half
        angle = 2.0 * math.asin(min(sin_half, 1.0))

        # 分解为沿 bone_dir 的分量（twist）和垂直分量（swing）
        twist_component = np.dot(axis, bone_dir) * bone_dir
        swing_axis = axis - twist_component
        swing_len = np.linalg.norm(swing_axis)

        if swing_len < 1e-6:
            # 纯扭转，返回单位四元数
            return np.array([0.0, 0.0, 0.0, 1.0])

        swing_axis = swing_axis / swing_len
        swing_angle = angle * swing_len

        return quat_from_axis_angle(swing_axis, swing_angle)

    def reset(self) -> None:
        """重置所有平滑滤波器。"""
        for f in self._filters.values():
            f.reset()


# ============================================================
# 便捷函数
# ============================================================

def landmarks_to_bone_data(
    frame: PoseFrame,
    mapper: MotionMapper | None = None,
) -> dict[str, dict[str, float]]:
    """便捷函数：将一帧 landmarks 转换为骨骼数据。"""
    if mapper is None:
        mapper = MotionMapper()
    return mapper.map_frame(frame)
