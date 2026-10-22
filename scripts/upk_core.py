#!/usr/bin/env python3
"""
Rocket League UPK Decryption, Decompression, and Asset Deserialization Core Library
Supports UPK Version 868 / LicenseeVersion 34 (Rocket League).
"""
import io
import json
import math
import os
import struct
import zlib
from collections import Counter
import numpy as np
from PIL import Image


# ==============================================================================
# 1. DXT1 / DXT5 / A8R8G8B8 Texture Decoding & Normal Map Reconstruction
# ==============================================================================

def decode_dxt1(data: bytes, width: int, height: int) -> np.ndarray:
    out = np.zeros((height, width, 4), dtype=np.uint8)
    blocks_x = max(1, width // 4)
    blocks_y = max(1, height // 4)
    pos = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            c0, c1, bits = struct.unpack_from('<HHI', data, pos)
            pos += 8
            r0 = ((c0 >> 11) & 0x1F); r0 = (r0 << 3) | (r0 >> 2)
            g0 = ((c0 >> 5) & 0x3F);  g0 = (g0 << 2) | (g0 >> 4)
            b0 = (c0 & 0x1F);         b0 = (b0 << 3) | (b0 >> 2)
            r1 = ((c1 >> 11) & 0x1F); r1 = (r1 << 3) | (r1 >> 2)
            g1 = ((c1 >> 5) & 0x3F);  g1 = (g1 << 2) | (g1 >> 4)
            b1 = (c1 & 0x1F);         b1 = (b1 << 3) | (b1 >> 2)
            if c0 > c1:
                pal = (
                    (r0, g0, b0, 255),
                    (r1, g1, b1, 255),
                    ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255),
                    ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255),
                )
            else:
                pal = (
                    (r0, g0, b0, 255),
                    (r1, g1, b1, 255),
                    ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255),
                    (0, 0, 0, 0),
                )
            for py in range(min(4, height - by * 4)):
                for px in range(min(4, width - bx * 4)):
                    idx = (bits >> (2 * (py * 4 + px))) & 0x3
                    out[by * 4 + py, bx * 4 + px] = pal[idx]
    return out


def decode_dxt5(data: bytes, width: int, height: int) -> np.ndarray:
    out = np.zeros((height, width, 4), dtype=np.uint8)
    blocks_x = max(1, width // 4)
    blocks_y = max(1, height // 4)
    pos = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            a0 = data[pos]
            a1 = data[pos + 1]
            abits = int.from_bytes(data[pos + 2:pos + 8], 'little')
            c0, c1, cbits = struct.unpack_from('<HHI', data, pos + 8)
            pos += 16
            if a0 > a1:
                apal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
            else:
                apal = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
            r0 = ((c0 >> 11) & 0x1F); r0 = (r0 << 3) | (r0 >> 2)
            g0 = ((c0 >> 5) & 0x3F);  g0 = (g0 << 2) | (g0 >> 4)
            b0 = (c0 & 0x1F);         b0 = (b0 << 3) | (b0 >> 2)
            r1 = ((c1 >> 11) & 0x1F); r1 = (r1 << 3) | (r1 >> 2)
            g1 = ((c1 >> 5) & 0x3F);  g1 = (g1 << 2) | (g1 >> 4)
            b1 = (c1 & 0x1F);         b1 = (b1 << 3) | (b1 >> 2)
            cpal = (
                (r0, g0, b0),
                (r1, g1, b1),
                ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3),
            )
            for py in range(min(4, height - by * 4)):
                for px in range(min(4, width - bx * 4)):
                    p_idx = py * 4 + px
                    c_idx = (cbits >> (2 * p_idx)) & 0x3
                    a_idx = (abits >> (3 * p_idx)) & 0x7
                    r, g, b = cpal[c_idx]
                    out[by * 4 + py, bx * 4 + px] = (r, g, b, apal[a_idx])
    return out


def decode_a8r8g8b8(data: bytes, width: int, height: int) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8, count=width * height * 4).reshape((height, width, 4))
    out = np.empty_like(arr)
    out[..., 0] = arr[..., 2]  # R
    out[..., 1] = arr[..., 1]  # G
    out[..., 2] = arr[..., 0]  # B
    out[..., 3] = arr[..., 3]  # A
    return out


def reconstruct_dxt5nm_normal_map(rgba: np.ndarray) -> np.ndarray:
    """
    Reconstructs a standard tangent-space RGB normal map from UE3 TC_NormalmapSwizzle (DXT5nm)
    where X is stored in Alpha (A) and Y is stored in Green (G).
    """
    nx = (rgba[..., 3].astype(np.float32) / 255.0) * 2.0 - 1.0
    ny = (rgba[..., 1].astype(np.float32) / 255.0) * 2.0 - 1.0
    nz_sq = np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0)
    nz = np.sqrt(nz_sq)
    out = np.zeros((rgba.shape[0], rgba.shape[1], 3), dtype=np.uint8)
    out[..., 0] = np.clip(np.round((nx * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(np.round((ny * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(np.round((nz * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    return out


# ==============================================================================
# 2. UPK Binary Reader & Recursive Property Deserializer
# ==============================================================================

class UPKPackage:
    def __init__(self, path: str):
        with open(path, 'rb') as f:
            self.data = f.read()
        self.pos = 0
        self.names = []
        self.imports = []
        self.exports = []
        self._parse_header()

    def r_u8(self):
        v = self.data[self.pos]; self.pos += 1; return v

    def r_i32(self):
        v = struct.unpack_from('<i', self.data, self.pos)[0]; self.pos += 4; return v

    def r_u32(self):
        v = struct.unpack_from('<I', self.data, self.pos)[0]; self.pos += 4; return v

    def r_i64(self):
        v = struct.unpack_from('<q', self.data, self.pos)[0]; self.pos += 8; return v

    def r_f32(self):
        v = struct.unpack_from('<f', self.data, self.pos)[0]; self.pos += 4; return round(float(v), 6)

    def r_bytes(self, n):
        b = self.data[self.pos:self.pos + n]; self.pos += n; return b

    def r_fstring(self):
        length = self.r_i32()
        if length == 0:
            return ""
        if length > 0:
            b = self.r_bytes(length)
            return b[:-1].decode('latin1', errors='replace')
        else:
            length = -length
            b = self.r_bytes(length * 2)
            return b[:-2].decode('utf-16le', errors='replace')

    def r_fname(self):
        idx = self.r_i32()
        num = self.r_i32()
        base = self.names[idx] if 0 <= idx < len(self.names) else f"__INVALID_{idx}__"
        return base if num == 0 else f"{base}_{num - 1}"

    def _parse_header(self):
        self.tag = self.r_u32()
        self.file_version = self.r_u32() & 0xFFFF
        self.licensee_version = (self.file_version >> 16) if False else struct.unpack_from('<H', self.data, 6)[0]
        self.total_header_size = self.r_i32()
        self.folder_name = self.r_fstring()
        self.package_flags = self.r_u32()
        self.name_count = self.r_i32()
        self.name_offset = self.r_i32()
        self.export_count = self.r_i32()
        self.export_offset = self.r_i32()
        self.import_count = self.r_i32()
        self.import_offset = self.r_i32()
        self.depends_offset = self.r_i32()

        self.pos = self.name_offset
        for _ in range(self.name_count):
            s = self.r_fstring()
            _flags = self.r_i64()
            self.names.append(s)

        self.pos = self.import_offset
        for i in range(self.import_count):
            class_pkg = self.r_fname()
            class_name = self.r_fname()
            outer_idx = self.r_i32()
            obj_name = self.r_fname()
            self.imports.append({
                "index": -(i + 1),
                "class_package": class_pkg,
                "class": class_name,
                "outer_index": outer_idx,
                "name": obj_name,
            })

        self.pos = self.export_offset
        for i in range(self.export_count):
            class_idx = self.r_i32()
            super_idx = self.r_i32()
            outer_idx = self.r_i32()
            obj_name = self.r_fname()
            archetype_idx = self.r_i32()
            obj_flags = self.r_i64()
            serial_size = self.r_i32()
            serial_offset = self.r_i64() if self.licensee_version >= 22 else self.r_i32()
            export_flags = self.r_u32()
            net_obj_count = self.r_i32()
            self.pos += 4 * net_obj_count
            guid = self.r_bytes(16).hex()
            pkg_flags = self.r_u32()
            self.exports.append({
                "index": i + 1,
                "class_index": class_idx,
                "super_index": super_idx,
                "outer_index": outer_idx,
                "name": obj_name,
                "archetype_index": archetype_idx,
                "object_flags": obj_flags,
                "serial_size": serial_size,
                "serial_offset": serial_offset,
                "export_flags": export_flags,
                "guid": guid,
                "package_flags": pkg_flags,
            })

        for imp in self.imports:
            imp["outer"] = self.get_obj_name(imp["outer_index"])
            imp["full_path"] = self.get_full_path(imp["index"])
        for exp in self.exports:
            exp["class"] = self.get_obj_name(exp["class_index"])
            exp["super"] = self.get_obj_name(exp["super_index"])
            exp["outer"] = self.get_obj_name(exp["outer_index"])
            exp["archetype"] = self.get_obj_name(exp["archetype_index"])
            exp["full_path"] = self.get_full_path(exp["index"])

    def get_obj_name(self, idx: int) -> str:
        if idx == 0:
            return "None"
        elif idx < 0:
            return self.imports[-idx - 1]["name"] if -idx - 1 < len(self.imports) else f"Import_{idx}"
        else:
            return self.exports[idx - 1]["name"] if idx - 1 < len(self.exports) else f"Export_{idx}"

    def get_full_path(self, idx: int) -> str:
        parts = []
        curr = idx
        visited = set()
        while curr != 0 and curr not in visited:
            visited.add(curr)
            if curr < 0 and -curr - 1 < len(self.imports):
                obj = self.imports[-curr - 1]
                parts.append(obj["name"])
                curr = obj["outer_index"]
            elif curr > 0 and curr - 1 < len(self.exports):
                obj = self.exports[curr - 1]
                parts.append(obj["name"])
                curr = obj["outer_index"]
            else:
                break
        return ".".join(reversed(parts))

    def get_group_dir(self, exp_idx: int) -> str:
        """Returns the group directory path inside the package for an export (1-based index)."""
        parts = []
        curr = self.exports[exp_idx - 1]["outer_index"]
        visited = set()
        while curr != 0 and curr not in visited:
            visited.add(curr)
            if curr > 0 and curr - 1 < len(self.exports):
                obj = self.exports[curr - 1]
                parts.append(obj["name"])
                curr = obj["outer_index"]
            elif curr < 0 and -curr - 1 < len(self.imports):
                obj = self.imports[-curr - 1]
                parts.append(obj["name"])
                curr = obj["outer_index"]
            else:
                break
        return "/".join(reversed(parts))

    def parse_properties(self, stop_pos: int) -> dict:
        props = {}
        while self.pos < stop_pos:
            if self.pos + 8 > stop_pos:
                break
            prop_name = self.r_fname()
            if prop_name == "None":
                break
            if prop_name.startswith("__INVALID_"):
                break
            prop_type = self.r_fname()
            prop_size = self.r_i32()
            array_idx = self.r_i32()
            struct_name = None
            enum_name = None
            if prop_type == "StructProperty":
                struct_name = self.r_fname()
            elif prop_type == "ByteProperty":
                enum_name = self.r_fname()
            elif prop_type == "BoolProperty":
                val = bool(self.r_u8())
                key = prop_name if array_idx == 0 else f"{prop_name}[{array_idx}]"
                props[key] = val
                continue

            val_start = self.pos
            val = self._parse_prop_value(prop_type, prop_size, struct_name, enum_name)
            self.pos = val_start + prop_size
            key = prop_name if array_idx == 0 else f"{prop_name}[{array_idx}]"
            props[key] = val
        return props

    def _parse_prop_value(self, prop_type, prop_size, struct_name, enum_name):
        end_p = self.pos + prop_size
        if prop_type == "IntProperty":
            return self.r_i32()
        elif prop_type == "FloatProperty":
            return self.r_f32()
        elif prop_type == "NameProperty":
            return self.r_fname()
        elif prop_type == "StrProperty":
            return self.r_fstring()
        elif prop_type in ("ObjectProperty", "ComponentProperty", "ClassProperty", "InterfaceProperty"):
            idx = self.r_i32()
            return {"index": idx, "name": self.get_obj_name(idx), "full_path": self.get_full_path(idx)}
        elif prop_type == "ByteProperty":
            if prop_size == 8:
                return {"enum": enum_name, "value": self.r_fname()}
            elif prop_size == 1:
                return {"enum": enum_name, "value": self.r_u8()}
            return self.r_bytes(prop_size).hex()
        elif prop_type == "StructProperty":
            if struct_name in ("Vector", "Float3"):
                return {"type": "Vector", "x": self.r_f32(), "y": self.r_f32(), "z": self.r_f32()}
            elif struct_name == "Rotator":
                p, y, r = self.r_i32(), self.r_i32(), self.r_i32()
                return {
                    "type": "Rotator",
                    "pitch": p, "yaw": y, "roll": r,
                    "pitch_deg": round(p * 360.0 / 65536.0, 4),
                    "yaw_deg": round(y * 360.0 / 65536.0, 4),
                    "roll_deg": round(r * 360.0 / 65536.0, 4),
                }
            elif struct_name in ("LinearColor",):
                return {"type": "LinearColor", "r": self.r_f32(), "g": self.r_f32(), "b": self.r_f32(), "a": self.r_f32()}
            elif struct_name == "Color":
                b, g, r, a = self.r_u8(), self.r_u8(), self.r_u8(), self.r_u8()
                return {"type": "Color", "r": r, "g": g, "b": b, "a": a}
            elif struct_name == "Guid":
                return self.r_bytes(16).hex()
            elif struct_name in ("Quat", "Vector4", "Plane"):
                return {"type": struct_name, "x": self.r_f32(), "y": self.r_f32(), "z": self.r_f32(), "w": self.r_f32()}
            elif struct_name == "Vector2D":
                return {"type": "Vector2D", "x": self.r_f32(), "y": self.r_f32()}
            elif struct_name == "Box":
                return {
                    "type": "Box",
                    "min": [self.r_f32(), self.r_f32(), self.r_f32()],
                    "max": [self.r_f32(), self.r_f32(), self.r_f32()],
                    "is_valid": bool(self.r_u8()),
                }
            elif struct_name == "Matrix":
                # UE3 FMatrix is 4 FPlanes where each FPlane is serialized as (W, X, Y, Z) in Rocket League RB_BodySetup
                m = [self.r_f32() for _ in range(16)]
                return {
                    "type": "Matrix",
                    "raw_floats": m,
                    "translation_xyz": [m[13], m[14], m[15]],
                }
            else:
                try:
                    sub = self.parse_properties(end_p)
                    if sub:
                        return {"_struct": struct_name, "fields": sub}
                except Exception:
                    pass
                self.pos = end_p - prop_size
                return {"_struct": struct_name, "raw": self.r_bytes(prop_size).hex()}
        elif prop_type == "ArrayProperty":
            if prop_size < 4:
                return []
            cnt = self.r_i32()
            rem = prop_size - 4
            if cnt == 0:
                return []
            if cnt > 0 and cnt < 10000:
                saved = self.pos
                try:
                    elems = []
                    ok = True
                    for _ in range(cnt):
                        if self.pos >= end_p:
                            ok = False; break
                        pk_idx = self.r_i32()
                        pk_num = self.r_i32()
                        if not (0 <= pk_idx < len(self.names)):
                            ok = False; break
                        pname = self.names[pk_idx]
                        if pname == "None":
                            elems.append({})
                            continue
                        self.pos -= 8
                        el = self.parse_properties(end_p)
                        elems.append(el)
                    if ok and self.pos == end_p:
                        return {"type": "ArrayStruct", "count": cnt, "elements": elems}
                except Exception:
                    pass
                self.pos = saved
            if cnt > 0 and rem == cnt * 4:
                vals = [self.r_i32() for _ in range(cnt)]
                self.pos = end_p - rem
                fvals = [self.r_f32() for _ in range(cnt)]
                return {
                    "type": "ArrayIntOrObj",
                    "count": cnt,
                    "values": vals,
                    "as_objects": [{"index": v, "name": self.get_obj_name(v)} for v in vals],
                    "as_floats": fvals,
                }
            if cnt > 0 and rem == cnt * 12:
                vecs = [[self.r_f32(), self.r_f32(), self.r_f32()] for _ in range(cnt)]
                return {"type": "ArrayVector", "count": cnt, "vectors": vecs}
            return {"type": "ArrayRaw", "count": cnt, "size": rem}
        return self.r_bytes(prop_size).hex()
