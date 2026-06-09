"""
VMD (Vocaloid Motion Data) 文件导出模块。
将骨骼动画序列写入标准 MikuMikuDance VMD 格式。
"""
from __future__ import annotations

import struct
from pathlib import Path


# VMD 文件格式常量
VMD_HEADER = b"Vocaloid Motion Data 0002"
VMD_HEADER_SIZE = 30  # 30 bytes, 不足部分用 \x00 填充
BONE_NAME_SIZE = 15    # 骨骼名 15 bytes (Shift-JIS)
INTERP_SIZE = 64       # 插值曲线 64 bytes


def _encode_bone_name(name: str) -> bytes:
    """将骨骼名编码为 Shift-JIS，填充到 15 字节。"""
    encoded = name.encode("shift_jis", errors="replace")
    if len(encoded) > BONE_NAME_SIZE:
        encoded = encoded[:BONE_NAME_SIZE]
    return encoded.ljust(BONE_NAME_SIZE, b"\x00")


def _build_default_interpolation() -> bytes:
    """生成默认的贝塞尔插值曲线（线性）。"""
    # 4 组插值，每组 4 个点（x1, y1, x2, y2），共 16 字节
    # 每组重复 4 次（X, Y, Z, Rotation），共 64 字节
    # 默认线性：(0, 0) -> (127, 127) 的贝塞尔控制点
    points = bytes([0, 0, 127, 127, 0, 0, 127, 127,
                    0, 0, 127, 127, 0, 0, 127, 127])
    return points * 4  # 重复 4 次 = 64 字节


class BoneKeyframe:
    """单个骨骼关键帧。"""

    def __init__(
        self,
        bone_name: str,
        frame: int,
        position: tuple[float, float, float] = (0.0, 0.0, 0.0),
        quaternion: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
        interpolation: bytes | None = None,
    ):
        self.bone_name = bone_name
        self.frame = frame
        self.position = position
        self.quaternion = quaternion  # (x, y, z, w)
        self.interpolation = interpolation or _build_default_interpolation()

    def to_bytes(self) -> bytes:
        """序列化为 VMD 二进制格式。"""
        parts = [
            _encode_bone_name(self.bone_name),   # 15 bytes
            struct.pack("<I", self.frame),         # 4 bytes uint32
            struct.pack("<fff", *self.position),   # 12 bytes (3x float32)
            struct.pack("<ffff", *self.quaternion), # 16 bytes (4x float32 xyzw)
            self.interpolation,                    # 64 bytes
        ]
        return b"".join(parts)


class VMDWriter:
    """VMD 文件写入器。"""

    def __init__(self):
        self.keyframes: list[BoneKeyframe] = []

    def add_keyframe(
        self,
        bone_name: str,
        frame: int,
        position: tuple[float, float, float] = (0.0, 0.0, 0.0),
        quaternion: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
    ) -> None:
        """添加一个骨骼关键帧。"""
        self.keyframes.append(BoneKeyframe(
            bone_name=bone_name,
            frame=frame,
            position=position,
            quaternion=quaternion,
        ))

    def add_frame_data(
        self,
        frame_index: int,
        bone_data: dict[str, dict[str, float]],
    ) -> None:
        """
        从 motion_mapper 输出的骨骼数据添加关键帧。

        Args:
            frame_index: 帧号
            bone_data: MotionMapper.map_frame() 的输出
        """
        for bone_name, data in bone_data.items():
            if "px" in data:
                # 位置骨骼
                self.add_keyframe(
                    bone_name=bone_name,
                    frame=frame_index,
                    position=(data["px"], data["py"], data["pz"]),
                    quaternion=(0.0, 0.0, 0.0, 1.0),
                )
            else:
                # 旋转骨骼
                self.add_keyframe(
                    bone_name=bone_name,
                    frame=frame_index,
                    position=(0.0, 0.0, 0.0),
                    quaternion=(data["x"], data["y"], data["z"], data["w"]),
                )

    def write(self, path: str | Path) -> None:
        """将所有关键帧写入 VMD 文件。"""
        path = Path(path)

        # 按骨骼名+帧号排序（VMD 标准要求）
        self.keyframes.sort(key=lambda kf: (kf.bone_name, kf.frame))

        with open(path, "wb") as f:
            # 写入 header（30 bytes）
            header = VMD_HEADER.ljust(VMD_HEADER_SIZE, b"\x00")
            f.write(header)

            # 写入关键帧数量
            f.write(struct.pack("<I", len(self.keyframes)))

            # 写入所有关键帧
            for kf in self.keyframes:
                f.write(kf.to_bytes())

        print(f"VMD 文件已导出: {path} ({len(self.keyframes)} 个关键帧)")

    def clear(self) -> None:
        """清空所有关键帧。"""
        self.keyframes.clear()

    @property
    def frame_count(self) -> int:
        return len(self.keyframes)

    @property
    def bone_names(self) -> set[str]:
        return {kf.bone_name for kf in self.keyframes}


def export_motion_to_vmd(
    frames: list[tuple[int, dict[str, dict[str, float]]]],
    output_path: str | Path,
) -> None:
    """
    便捷函数：将帧数据列表导出为 VMD 文件。

    Args:
        frames: [(frame_index, bone_data), ...] 列表
        output_path: 输出 VMD 文件路径
    """
    writer = VMDWriter()
    for frame_index, bone_data in frames:
        writer.add_frame_data(frame_index, bone_data)
    writer.write(output_path)
