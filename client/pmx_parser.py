"""
PMX 2.0 二进制文件解析器。
解析顶点、索引、材质、骨骼、变形（morph）等数据。
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PMXVertex:
    position: np.ndarray        # (3,) float32
    normal: np.ndarray          # (3,) float32
    uv: np.ndarray              # (2,) float32
    extra_uvs: list[np.ndarray]  # list of (4,) float32
    bone_indices: np.ndarray    # (4,) int32
    bone_weights: np.ndarray    # (4,) float32
    edge_scale: float


@dataclass
class PMXMaterial:
    name: str
    name_en: str
    diffuse: np.ndarray         # (4,) RGBA float32
    specular: np.ndarray        # (3,) RGB float32
    specular_strength: float
    ambient: np.ndarray         # (3,) RGB float32
    draw_flags: int             # bitfield
    edge_color: np.ndarray      # (4,) RGBA float32
    edge_size: float
    texture_index: int          # -1 if none
    sphere_texture_index: int
    sphere_mode: int            # 0=disabled, 1=mul, 2=add, 3=sub
    toon_type: int              # 0=texture, 1=shared
    toon_texture_index: int
    vertex_count: int           # index count for this material group

    @property
    def is_double_sided(self) -> bool:
        return bool(self.draw_flags & 0x01)

    @property
    def has_ground_shadow(self) -> bool:
        return bool(self.draw_flags & 0x02)

    @property
    def has_edge(self) -> bool:
        return bool(self.draw_flags & 0x10)

    @property
    def has_self_shadow(self) -> bool:
        return bool(self.draw_flags & 0x04)

    @property
    def has_self_shadow_map(self) -> bool:
        return bool(self.draw_flags & 0x08)


@dataclass
class PMXBone:
    name: str
    name_en: str
    parent_index: int           # -1 if root
    position: np.ndarray        # (3,) float32 world-space rest position
    flags: int
    tail_bone_index: int = -1   # if flag 0x0001 not set
    tail_position: np.ndarray | None = None  # if flag 0x0001 set
    inherit_parent_index: int = -1
    inherit_weight: float = 1.0
    fixed_axis: np.ndarray | None = None
    local_axis_x: np.ndarray | None = None
    local_axis_z: np.ndarray | None = None
    ik_target_bone_index: int = -1
    ik_loop: int = 0
    ik_angle_limit: float = 0.0
    ik_links: list[dict] = field(default_factory=list)
    children: list[int] = field(default_factory=list)  # populated post-parse

    @property
    def is_rotatable(self) -> bool:
        return bool(self.flags & 0x0002)

    @property
    def is_translatable(self) -> bool:
        return bool(self.flags & 0x0004)

    @property
    def is_visible(self) -> bool:
        return bool(self.flags & 0x0008)

    @property
    def is_operable(self) -> bool:
        return bool(self.flags & 0x0010)

    @property
    def is_ik(self) -> bool:
        return bool(self.flags & 0x0020)

    @property
    def has_inherit_rotation(self) -> bool:
        return bool(self.flags & 0x0100)

    @property
    def has_inherit_translation(self) -> bool:
        return bool(self.flags & 0x0200)

    @property
    def has_fixed_axis(self) -> bool:
        return bool(self.flags & 0x0400)

    @property
    def has_local_axis(self) -> bool:
        return bool(self.flags & 0x0800)

    @property
    def has_physics_after_deform(self) -> bool:
        return bool(self.flags & 0x1000)

    @property
    def has_external_parent(self) -> bool:
        return bool(self.flags & 0x2000)


@dataclass
class VertexMorphOffset:
    vertex_index: int
    position_offset: np.ndarray  # (3,) float32


@dataclass
class UVMorphOffset:
    vertex_index: int
    uv_offset: np.ndarray  # (4,) float32


@dataclass
class BoneMorphOffset:
    bone_index: int
    position_offset: np.ndarray  # (3,) float32
    rotation_offset: np.ndarray  # (4,) quaternion [x,y,z,w]


@dataclass
class GroupMorphOffset:
    morph_index: int
    weight: float


@dataclass
class PMXMorph:
    name: str
    name_en: str
    morph_type: int             # 0=group, 1=vertex, 2=bone, 3=UV, ...
    offsets: list               # type-specific offset objects


@dataclass
class PMXModel:
    header: dict
    vertices: list[PMXVertex]
    indices: list[int]
    textures: list[str]
    materials: list[PMXMaterial]
    bones: list[PMXBone]
    morphs: list[PMXMorph]
    model_dir: str              # directory containing the PMX file

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def index_count(self) -> int:
        return len(self.indices)

    @property
    def bone_count(self) -> int:
        return len(self.bones)

    @property
    def morph_count(self) -> int:
        return len(self.morphs)


# ============================================================
# 二进制读取器
# ============================================================

class BinaryReader:
    """PMX 二进制文件读取器。"""

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read_bytes(self, n: int) -> bytes:
        result = self._data[self._pos:self._pos + n]
        self._pos += n
        return result

    def read_int8(self) -> int:
        val = struct.unpack_from('<b', self._data, self._pos)[0]
        self._pos += 1
        return val

    def read_uint8(self) -> int:
        val = struct.unpack_from('<B', self._data, self._pos)[0]
        self._pos += 1
        return val

    def read_int16(self) -> int:
        val = struct.unpack_from('<h', self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_uint16(self) -> int:
        val = struct.unpack_from('<H', self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_int32(self) -> int:
        val = struct.unpack_from('<i', self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_uint32(self) -> int:
        val = struct.unpack_from('<I', self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_float32(self) -> float:
        val = struct.unpack_from('<f', self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_vec2(self) -> np.ndarray:
        v = np.frombuffer(self._data, dtype='<f4', count=2, offset=self._pos).copy()
        self._pos += 8
        return v

    def read_vec3(self) -> np.ndarray:
        v = np.frombuffer(self._data, dtype='<f4', count=3, offset=self._pos).copy()
        self._pos += 12
        return v

    def read_vec4(self) -> np.ndarray:
        v = np.frombuffer(self._data, dtype='<f4', count=4, offset=self._pos).copy()
        self._pos += 16
        return v

    def read_mat4x4(self) -> np.ndarray:
        """读取 4x4 矩阵（16 个 float32，列主序）。"""
        v = np.frombuffer(self._data, dtype='<f4', count=16, offset=self._pos).astype(np.float32)
        self._pos += 64
        return v.reshape(4, 4)

    def read_index(self, size: int, is_vertex: bool = False) -> int:
        """读取变宽索引。size: 1/2/4 字节。is_vertex=True 时为无符号。"""
        if size == 1:
            return self.read_uint8() if is_vertex else self.read_int8()
        elif size == 2:
            return self.read_uint16() if is_vertex else self.read_int16()
        elif size == 4:
            return self.read_uint32() if is_vertex else self.read_int32()
        else:
            raise ValueError(f"Invalid index size: {size}")

    def read_string(self, encoding: int) -> str:
        """读取 PMX 字符串。encoding: 0=UTF-16LE, 1=UTF-8。"""
        byte_count = self.read_int32()
        if byte_count <= 0:
            return ""
        raw = self.read_bytes(byte_count)
        if encoding == 0:
            return raw.decode('utf-16-le')
        else:
            return raw.decode('utf-8')

    @property
    def position(self) -> int:
        return self._pos

    def skip(self, n: int) -> None:
        self._pos += n


# ============================================================
# PMX 解析器
# ============================================================

def parse_pmx(filepath: str | Path) -> PMXModel:
    """解析 PMX 2.0 文件，返回 PMXModel。"""
    filepath = Path(filepath)
    data = filepath.read_bytes()
    reader = BinaryReader(data)
    model_dir = str(filepath.parent)

    # --- Header ---
    magic = reader.read_bytes(4)
    if magic != b'PMX ':
        raise ValueError(f"Not a PMX file: magic={magic}")

    version = reader.read_float32()
    if version < 2.0:
        raise ValueError(f"Unsupported PMX version: {version}")

    globals_count = reader.read_uint8()
    globals = [reader.read_uint8() for _ in range(globals_count)]

    encoding = globals[0]          # 0=UTF-16LE, 1=UTF-8
    extra_uv_count = globals[1]    # 0-4
    vertex_index_size = globals[2]
    texture_index_size = globals[3]
    material_index_size = globals[4]
    bone_index_size = globals[5]
    morph_index_size = globals[6]
    rigidbody_index_size = globals[7]

    header = {
        'version': version,
        'encoding': encoding,
        'extra_uv_count': extra_uv_count,
        'vertex_index_size': vertex_index_size,
        'texture_index_size': texture_index_size,
        'material_index_size': material_index_size,
        'bone_index_size': bone_index_size,
        'morph_index_size': morph_index_size,
        'rigidbody_index_size': rigidbody_index_size,
    }

    # --- Model Info (name, name_en, comment, comment_en) ---
    model_name = reader.read_string(encoding)
    model_name_en = reader.read_string(encoding)
    model_comment = reader.read_string(encoding)
    model_comment_en = reader.read_string(encoding)

    header['model_name'] = model_name
    header['model_name_en'] = model_name_en

    # --- Textures ---
    # (先读纹理，后面材质需要用到)
    # 但 PMX 顺序是: 顶点 → 索引 → 纹理 → 材质 → 骨骼 → 变形
    # 所以按顺序解析

    # --- Vertices ---
    vertex_count = reader.read_int32()
    vertices: list[PMXVertex] = []
    for _ in range(vertex_count):
        pos = reader.read_vec3()
        normal = reader.read_vec3()
        uv = reader.read_vec2()

        extra_uvs = []
        for _ in range(extra_uv_count):
            extra_uvs.append(reader.read_vec4())

        weight_type = reader.read_uint8()

        bone_indices = np.array([0, 0, 0, 0], dtype=np.int32)
        bone_weights = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

        if weight_type == 0:  # BDEF1
            bone_indices[0] = reader.read_index(bone_index_size)
        elif weight_type == 1:  # BDEF2
            bone_indices[0] = reader.read_index(bone_index_size)
            bone_indices[1] = reader.read_index(bone_index_size)
            w = reader.read_float32()
            bone_weights[0] = w
            bone_weights[1] = 1.0 - w
        elif weight_type == 2:  # BDEF4
            for i in range(4):
                bone_indices[i] = reader.read_index(bone_index_size)
            for i in range(4):
                bone_weights[i] = reader.read_float32()
            # 归一化
            total = bone_weights.sum()
            if total > 0:
                bone_weights /= total
        elif weight_type == 3:  # SDEF
            bone_indices[0] = reader.read_index(bone_index_size)
            bone_indices[1] = reader.read_index(bone_index_size)
            w = reader.read_float32()
            bone_weights[0] = w
            bone_weights[1] = 1.0 - w
            # SDEF-C, SDEF-R0, SDEF-R1 (3 x vec3)
            reader.skip(36)
        elif weight_type == 4:  # QDEF
            for i in range(4):
                bone_indices[i] = reader.read_index(bone_index_size)
            for i in range(4):
                bone_weights[i] = reader.read_float32()
            total = bone_weights.sum()
            if total > 0:
                bone_weights /= total
        else:
            raise ValueError(f"Unknown weight type: {weight_type}")

        edge_scale = reader.read_float32()

        vertices.append(PMXVertex(
            position=pos,
            normal=normal,
            uv=uv,
            extra_uvs=extra_uvs,
            bone_indices=bone_indices,
            bone_weights=bone_weights,
            edge_scale=edge_scale,
        ))

    # --- Indices ---
    index_count = reader.read_int32()
    indices: list[int] = []
    for _ in range(index_count):
        idx = reader.read_index(vertex_index_size, is_vertex=True)
        indices.append(idx)

    # --- Textures ---
    texture_count = reader.read_int32()
    textures: list[str] = []
    for _ in range(texture_count):
        tex_path = reader.read_string(encoding)
        textures.append(tex_path)

    # --- Materials ---
    material_count = reader.read_int32()
    materials: list[PMXMaterial] = []
    for _ in range(material_count):
        mat_name = reader.read_string(encoding)
        mat_name_en = reader.read_string(encoding)

        diffuse = reader.read_vec4()
        specular = reader.read_vec3()
        specular_strength = reader.read_float32()
        ambient = reader.read_vec3()

        draw_flags = reader.read_uint8()

        edge_color = reader.read_vec4()
        edge_size = reader.read_float32()

        tex_idx = reader.read_index(texture_index_size)
        sphere_tex_idx = reader.read_index(texture_index_size)
        sphere_mode = reader.read_uint8()

        toon_type = reader.read_uint8()
        if toon_type == 0:
            toon_tex_idx = reader.read_index(texture_index_size)
        else:
            toon_tex_idx = reader.read_uint8()

        comment = reader.read_string(encoding)
        vertex_count_mat = reader.read_int32()

        materials.append(PMXMaterial(
            name=mat_name,
            name_en=mat_name_en,
            diffuse=diffuse,
            specular=specular,
            specular_strength=specular_strength,
            ambient=ambient,
            draw_flags=draw_flags,
            edge_color=edge_color,
            edge_size=edge_size,
            texture_index=tex_idx,
            sphere_texture_index=sphere_tex_idx,
            sphere_mode=sphere_mode,
            toon_type=toon_type,
            toon_texture_index=toon_tex_idx,
            vertex_count=vertex_count_mat,
        ))

    # --- Bones ---
    bone_count = reader.read_int32()
    bones: list[PMXBone] = []
    for _ in range(bone_count):
        bone_name = reader.read_string(encoding)
        bone_name_en = reader.read_string(encoding)

        parent_idx = reader.read_index(bone_index_size)
        position = reader.read_vec3()

        flags = reader.read_uint16()

        tail_bone_idx = -1
        tail_pos = None
        if flags & 0x0001:
            tail_pos = reader.read_vec3()
        else:
            tail_bone_idx = reader.read_index(bone_index_size)

        inherit_parent_idx = -1
        inherit_weight = 1.0
        if flags & 0x0100 or flags & 0x0200:
            inherit_parent_idx = reader.read_index(bone_index_size)
            inherit_weight = reader.read_float32()

        fixed_axis = None
        if flags & 0x0400:
            fixed_axis = reader.read_vec3()

        local_axis_x = None
        local_axis_z = None
        if flags & 0x0800:
            local_axis_x = reader.read_vec3()
            local_axis_z = reader.read_vec3()

        ext_parent_key = 0
        if flags & 0x2000:
            ext_parent_key = reader.read_int32()

        ik_target = -1
        ik_loop = 0
        ik_angle_limit = 0.0
        ik_links = []
        if flags & 0x0020:
            ik_target = reader.read_index(bone_index_size)
            ik_loop = reader.read_int32()
            ik_angle_limit = reader.read_float32()
            ik_link_count = reader.read_int32()
            for _ in range(ik_link_count):
                link_bone_idx = reader.read_index(bone_index_size)
                has_limit = reader.read_uint8()
                limit_min = None
                limit_max = None
                if has_limit:
                    limit_min = reader.read_vec3()
                    limit_max = reader.read_vec3()
                ik_links.append({
                    'bone_index': link_bone_idx,
                    'has_limit': bool(has_limit),
                    'limit_min': limit_min,
                    'limit_max': limit_max,
                })

        bones.append(PMXBone(
            name=bone_name,
            name_en=bone_name_en,
            parent_index=parent_idx,
            position=position,
            flags=flags,
            tail_bone_index=tail_bone_idx,
            tail_position=tail_pos,
            inherit_parent_index=inherit_parent_idx,
            inherit_weight=inherit_weight,
            fixed_axis=fixed_axis,
            local_axis_x=local_axis_x,
            local_axis_z=local_axis_z,
            ik_target_bone_index=ik_target,
            ik_loop=ik_loop,
            ik_angle_limit=ik_angle_limit,
            ik_links=ik_links,
        ))

    # Build parent-child hierarchy
    for i, bone in enumerate(bones):
        if bone.parent_index >= 0 and bone.parent_index < len(bones):
            bones[bone.parent_index].children.append(i)

    # --- Morphs ---
    morph_count = reader.read_int32()
    morphs: list[PMXMorph] = []
    for _ in range(morph_count):
        morph_name = reader.read_string(encoding)
        morph_name_en = reader.read_string(encoding)
        morph_panel = reader.read_uint8()
        morph_type = reader.read_uint8()
        offset_count = reader.read_int32()

        offsets = []
        if morph_type == 0:  # Group
            for _ in range(offset_count):
                mi = reader.read_index(morph_index_size)
                weight = reader.read_float32()
                offsets.append(GroupMorphOffset(morph_index=mi, weight=weight))
        elif morph_type == 1:  # Vertex
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                pos_off = reader.read_vec3()
                offsets.append(VertexMorphOffset(vertex_index=vi, position_offset=pos_off))
        elif morph_type == 2:  # Bone
            for _ in range(offset_count):
                bi = reader.read_index(bone_index_size)
                pos_off = reader.read_vec3()
                rot_off = reader.read_vec4()
                offsets.append(BoneMorphOffset(
                    bone_index=bi,
                    position_offset=pos_off,
                    rotation_offset=rot_off,
                ))
        elif morph_type == 3:  # UV
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                uv_off = reader.read_vec4()
                offsets.append(UVMorphOffset(vertex_index=vi, uv_offset=uv_off))
        elif morph_type == 4:  # UV1
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                uv_off = reader.read_vec4()
                offsets.append(UVMorphOffset(vertex_index=vi, uv_offset=uv_off))
        elif morph_type == 5:  # UV2
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                uv_off = reader.read_vec4()
                offsets.append(UVMorphOffset(vertex_index=vi, uv_offset=uv_off))
        elif morph_type == 6:  # UV3
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                uv_off = reader.read_vec4()
                offsets.append(UVMorphOffset(vertex_index=vi, uv_offset=uv_off))
        elif morph_type == 7:  # UV4
            for _ in range(offset_count):
                vi = reader.read_index(vertex_index_size, is_vertex=True)
                uv_off = reader.read_vec4()
                offsets.append(UVMorphOffset(vertex_index=vi, uv_offset=uv_off))
        elif morph_type == 8:  # Material
            for _ in range(offset_count):
                mi = reader.read_index(material_index_size)
                reader.skip(1)  # offset type (add/mul)
                reader.skip(64)  # diffuse(16) + specular(12) + spec_strength(4) + ambient(12) + edge_color(16) + edge_size(4)
                # Actually let me read it properly
                offsets.append(None)  # placeholder
        else:
            # Skip unknown morph types
            reader.skip(offset_count * 4)  # rough skip
            offsets = []

        morphs.append(PMXMorph(
            name=morph_name,
            name_en=morph_name_en,
            morph_type=morph_type,
            offsets=offsets,
        ))

    return PMXModel(
        header=header,
        vertices=vertices,
        indices=indices,
        textures=textures,
        materials=materials,
        bones=bones,
        morphs=morphs,
        model_dir=model_dir,
    )


# ============================================================
# NumPy 批量导出（用于 GPU 上传）
# ============================================================

def get_vertex_array(model: PMXModel) -> np.ndarray:
    """导出顶点数组为 numpy 数组，形状 (N, 3+3+2+4+4) = (N, 16)。
    布局: position(3), normal(3), uv(2), bone_indices(4), bone_weights(4)
    """
    n = model.vertex_count
    arr = np.zeros((n, 16), dtype=np.float32)
    for i, v in enumerate(model.vertices):
        arr[i, 0:3] = v.position
        arr[i, 3:6] = v.normal
        arr[i, 6:8] = v.uv
        arr[i, 8:12] = v.bone_indices.astype(np.float32)
        arr[i, 12:16] = v.bone_weights
    return arr


def get_vertex_array_int(model: PMXModel) -> tuple[np.ndarray, np.ndarray]:
    """导出顶点数组，骨骼索引用 int32 单独返回。
    返回 (float_array(N, 12), int_array(N, 4))
    float: position(3), normal(3), uv(2), bone_weights(4)
    int: bone_indices(4)
    """
    n = model.vertex_count
    floats = np.zeros((n, 12), dtype=np.float32)
    ints = np.zeros((n, 4), dtype=np.int32)
    for i, v in enumerate(model.vertices):
        floats[i, 0:3] = v.position
        floats[i, 3:6] = v.normal
        floats[i, 6:8] = v.uv
        floats[i, 8:12] = v.bone_weights
        ints[i] = v.bone_indices
    return floats, ints


def get_index_array(model: PMXModel) -> np.ndarray:
    """导出索引数组。"""
    return np.array(model.indices, dtype=np.uint32)


def get_positions_array(model: PMXModel) -> np.ndarray:
    """导出顶点位置数组 (N, 3)。"""
    n = model.vertex_count
    arr = np.zeros((n, 3), dtype=np.float32)
    for i, v in enumerate(model.vertices):
        arr[i] = v.position
    return arr


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else r'E:\Code\Projects\Emotion-Agent\web\models\星穹铁道—火花2.pmx'
    model = parse_pmx(path)
    print(f"PMX version: {model.header['version']}")
    print(f"Vertices: {model.vertex_count}")
    print(f"Indices: {model.index_count}")
    print(f"Textures: {len(model.textures)}")
    print(f"Materials: {len(model.materials)}")
    print(f"Bones: {model.bone_count}")
    print(f"Morphs: {model.morph_count}")
    print(f"\nTextures:")
    for t in model.textures:
        print(f"  {t}")
    print(f"\nMaterials:")
    for m in model.materials:
        print(f"  {m.name} (indices: {m.vertex_count}, tex: {m.texture_index}, toon: {m.toon_type}/{m.toon_texture_index})")
    print(f"\nBones (first 20):")
    for b in model.bones[:20]:
        print(f"  {b.name} (parent: {b.parent_index}, children: {b.children})")
    print(f"\nMorphs:")
    for m in model.morphs:
        print(f"  {m.name} (type: {m.morph_type}, offsets: {len(m.offsets)})")
