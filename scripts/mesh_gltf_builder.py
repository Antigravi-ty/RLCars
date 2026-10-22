#!/usr/bin/env python3
"""
Rocket League UPK SkeletalMesh & StaticMesh Deserializer and glTF 2.0 / GLB Exporter.
Implements exact UE3 -> glTF 2.0 coordinate system, normal/tangent unpacking,
depth-first bone sorting, inverseBindMatrices, socket node attachment, and
evidence-backed surface material region splitting.
"""
import io
import json
import math
import os
import struct
import numpy as np
from PIL import Image
from upk_core import (
    UPKPackage,
    decode_dxt1,
    decode_dxt5,
    decode_a8r8g8b8,
    reconstruct_dxt5nm_normal_map,
)


def get_material_debug_color(index: int):
    table = [0.9, 0.3, 0.6, 1.0]
    table2 = [0, 1, 2, 4, 7, 3, 5, 6]
    idx = (index & 0xFFF8) | (table2[index & 7] ^ 7)
    def c(x):
        return (x & 1) | ((x >> 2) & 2)
    return [table[c(idx)], table[c(idx >> 1)], table[c(idx >> 2)], 1.0]


def quat_to_axis(q):
    X, Y, Z, W = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    x2, y2, z2 = X * 2.0, Y * 2.0, Z * 2.0
    xx, xy, xz = X * x2, X * y2, X * z2
    yy, yz, zz = Y * y2, Y * z2, Z * z2
    wx, wy, wz = W * x2, W * y2, W * z2
    return np.array([
        [1.0 - (yy + zz), xy - wz, xz + wy],
        [xy + wz, 1.0 - (xx + zz), yz - wx],
        [xz - wy, yz + wx, 1.0 - (xx + yy)],
    ], dtype=np.float32)


def untransform_coords(parent_orig, parent_axis, child_orig, child_axis):
    orig = (
        parent_orig
        + child_orig[0] * parent_axis[0]
        + child_orig[1] * parent_axis[1]
        + child_orig[2] * parent_axis[2]
    )
    axis = np.zeros((3, 3), dtype=np.float32)
    for i in range(3):
        axis[i] = (
            child_axis[i, 0] * parent_axis[0]
            + child_axis[i, 1] * parent_axis[1]
            + child_axis[i, 2] * parent_axis[2]
        )
    return orig, axis


def invert_coords(orig, axis):
    inv_orig = -np.array([
        np.dot(orig, axis[0]),
        np.dot(orig, axis[1]),
        np.dot(orig, axis[2]),
    ], dtype=np.float32)
    inv_axis = axis.T.copy()
    mat = np.eye(4, dtype=np.float32)
    mat[:3, :3] = inv_axis
    mat[3, :3] = inv_orig
    return mat


def unpack_normals_and_tangents(n0_arr: np.ndarray, n2_arr: np.ndarray):
    """
    Vectorized unpacking of UE3 FPackedNormal TangentX (n0) and TangentZ (n2)
    into glTF right-handed Y-up NORMAL (N, 3) and TANGENT (N, 4).
    """
    c0 = (n0_arr ^ 0x80808080).view(np.int8).reshape(-1, 4).astype(np.float32) / 127.0
    c2 = (n2_arr ^ 0x80808080).view(np.int8).reshape(-1, 4).astype(np.float32) / 127.0

    # Swap Y and Z for glTF coordinate system (TransformDirection)
    norm = np.stack([c2[:, 0], c2[:, 2], c2[:, 1]], axis=1)
    norm_len = np.linalg.norm(norm, axis=1, keepdims=True)
    norm = np.where(norm_len > 0, norm / norm_len, norm)

    tang_xyz = np.stack([c0[:, 0], c0[:, 2], c0[:, 1]], axis=1)
    tang_len = np.linalg.norm(tang_xyz, axis=1, keepdims=True)
    tang_xyz = np.where(tang_len > 0, tang_xyz / tang_len, tang_xyz)
    tang_w = np.where(c2[:, 3] < 0, -1.0, 1.0).astype(np.float32).reshape(-1, 1)
    tang = np.hstack([tang_xyz, tang_w])
    return norm.astype(np.float32), tang.astype(np.float32)


def sort_bones_depth_first(bones):
    """
    Matches CSkeletalMesh::SortBones() in UEViewer:
    sorts bones recursively starting from root bone 0 and returns
    (sorted_bones, old_to_new_map, new_to_old_map).
    """
    num_bones = len(bones)
    order = [0]
    def sort_recursive(parent_idx):
        for i in range(1, num_bones):
            if bones[i]['parent_index'] == parent_idx:
                order.append(i)
                sort_recursive(i)
    sort_recursive(0)
    old_to_new = {old_i: new_i for new_i, old_i in enumerate(order)}
    sorted_bones = []
    for new_i, old_i in enumerate(order):
        b = dict(bones[old_i])
        b['original_index'] = old_i
        b['index'] = new_i
        b['parent_index'] = old_to_new[b['parent_index']] if new_i > 0 else -1
        sorted_bones.append(b)
    return sorted_bones, old_to_new, order


def deserialize_skeletal_mesh(upk: UPKPackage, exp_idx: int) -> dict:
    """Deserializes a USkeletalMesh export (0-based index in upk.exports)."""
    exp = upk.exports[exp_idx]
    end_pos = exp['serial_offset'] + exp['serial_size']
    upk.pos = exp['serial_offset'] + 4
    props = upk.parse_properties(end_pos)
    pos = upk.pos
    data = upk.data

    bounds = struct.unpack_from('<7f', data, pos); pos += 28
    mat_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
    mat_indices = struct.unpack_from(f'<{mat_count}i', data, pos); pos += 4 * mat_count
    materials = [upk.get_obj_name(m) for m in mat_indices]

    origin = struct.unpack_from('<3f', data, pos); pos += 12
    rot_origin = struct.unpack_from('<3i', data, pos); pos += 12

    bone_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
    raw_bones = []
    for b_idx in range(bone_count):
        bname_idx, bname_num, bflags = struct.unpack_from('<iiI', data, pos)
        bname = upk.names[bname_idx] if bname_num == 0 else f"{upk.names[bname_idx]}_{bname_num - 1}"
        quat = list(struct.unpack_from('<4f', data, pos + 12))
        bpos = list(struct.unpack_from('<3f', data, pos + 28))
        num_children, parent_idx, bone_color = struct.unpack_from('<iiI', data, pos + 40)
        pos += 52
        raw_bones.append({
            "index": b_idx,
            "name": bname,
            "flags": bflags,
            "orientation_xyzw": [round(x, 6) for x in quat],
            "position_xyz": [round(x, 6) for x in bpos],
            "num_children": num_children,
            "parent_index": parent_idx if b_idx > 0 else -1,
            "color": bone_color,
        })

    skel_depth = struct.unpack_from('<i', data, pos)[0]; pos += 4
    lod_count = struct.unpack_from('<I', data, pos)[0]; pos += 4

    # Parse LOD 0
    sec_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
    sections = []
    for s_i in range(sec_count):
        mat_idx, chunk_idx, base_idx, num_tris, tri_sorting = struct.unpack_from('<HHIIB', data, pos)
        pos += 13
        sections.append({
            "section_index": s_i,
            "material_index": mat_idx,
            "material_name": materials[mat_idx] if mat_idx < len(materials) else f"mat_{mat_idx}",
            "chunk_index": chunk_idx,
            "first_index": base_idx,
            "num_triangles": num_tris,
            "triangle_sorting": tri_sorting,
        })

    needs_cpu, data_type_size, idx_elem_size, idx_elem_count = struct.unpack_from('<IBII', data, pos)
    pos += 13
    indices = np.frombuffer(
        data, dtype='<u4' if idx_elem_size == 4 else '<u2', offset=pos, count=idx_elem_count
    ).astype(np.uint32)
    pos += idx_elem_size * idx_elem_count

    used_bones_count = struct.unpack_from('<I', data, pos)[0]
    pos += 4 + 2 * used_bones_count

    chunk_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
    chunks = []
    for c_i in range(chunk_count):
        base_vert_idx, rig_count = struct.unpack_from('<II', data, pos)
        pos += 8 + rig_count * 61
        soft_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4 + soft_count * 68
        bone_map_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
        bone_map = list(struct.unpack_from(f'<{bone_map_count}H', data, pos))
        pos += 2 * bone_map_count
        num_rig, num_soft, max_inf = struct.unpack_from('<iii', data, pos)
        pos += 12
        chunks.append({
            "chunk_index": c_i,
            "first_vertex": base_vert_idx,
            "bone_map": bone_map,
            "num_rigid_verts": num_rig,
            "num_soft_verts": num_soft,
            "max_influences": max_inf,
        })

    lod_size, num_verts = struct.unpack_from('<II', data, pos); pos += 8
    req_bones_count = struct.unpack_from('<I', data, pos)[0]; pos += 4 + req_bones_count
    bflags, belem, bsize = struct.unpack_from('<III', data, pos)
    pos += 12 + (8 if (bflags & 1) else bsize)
    num_uv_sets = struct.unpack_from('<I', data, pos)[0]; pos += 4
    gpu_num_uvs, full_prec_uvs, packed_pos = struct.unpack_from('<III', data, pos)
    mesh_ext = struct.unpack_from('<3f', data, pos + 12)
    mesh_orig = struct.unpack_from('<3f', data, pos + 24)
    pos += 36
    elem_size, elem_count = struct.unpack_from('<II', data, pos); pos += 8
    raw_verts = np.frombuffer(data, dtype=np.uint8, offset=pos, count=elem_size * elem_count).reshape(elem_count, elem_size)
    pos += elem_size * elem_count

    has_vertex_colors = bool(props.get('bHasVertexColors', False))
    vcolors_rgba = None
    if has_vertex_colors:
        vc_elem_size, vc_elem_count = struct.unpack_from('<II', data, pos); pos += 8
        vc_bgra = np.frombuffer(data, dtype=np.uint8, offset=pos, count=4 * vc_elem_count).reshape(vc_elem_count, 4)
        # UE3 FColor is BGRA in memory; in ExportGLTF.cpp ColorBuf->Put(Lod.VertexColors[vertIndex]) writes those 4 bytes directly!
        # Wait: let's check both BGRA and RGBA so we know exact values
        vcolors_rgba = vc_bgra[:, [2, 1, 0, 3]].copy()
        vcolors_raw_bytes = vc_bgra.copy()
        pos += vc_elem_size * vc_elem_count
    else:
        vcolors_raw_bytes = None

    # Unpack positions, normals, tangents, UVs, and bone influences
    n0_arr = np.frombuffer(raw_verts[:, 0:4].tobytes(), dtype='<u4')
    n2_arr = np.frombuffer(raw_verts[:, 4:8].tobytes(), dtype='<u4')
    normals_gltf, tangents_gltf = unpack_normals_and_tangents(n0_arr, n2_arr)

    pos_ue = np.frombuffer(raw_verts[:, 16:28].tobytes(), dtype='<f4').reshape(elem_count, 3).copy()
    # glTF position: swap Y and Z, scale 0.01
    pos_gltf = np.stack([pos_ue[:, 0] * 0.01, pos_ue[:, 2] * 0.01, pos_ue[:, 1] * 0.01], axis=1).astype(np.float32)

    uv_sets = []
    for uv_i in range(gpu_num_uvs):
        uv_off = 28 + uv_i * 4
        uv_arr = np.frombuffer(raw_verts[:, uv_off:uv_off + 4].tobytes(), dtype='<f2').reshape(elem_count, 2).astype(np.float32)
        uv_sets.append(uv_arr)

    # Sort bones depth-first and remap vertex bone indices per chunk
    sorted_bones, old_to_new_bone, _ = sort_bones_depth_first(raw_bones)
    raw_bone_idx = raw_verts[:, 8:12]
    raw_bone_w = raw_verts[:, 12:16]

    joints_0 = np.zeros((elem_count, 4), dtype=np.uint16)
    weights_0 = np.zeros((elem_count, 4), dtype=np.uint8)
    raw_bone_primary = np.zeros(elem_count, dtype=np.uint16)

    for c in chunks:
        v_start = c['first_vertex']
        v_end = v_start + c['num_rigid_verts'] + c['num_soft_verts']
        bmap = c['bone_map']
        for v_i in range(v_start, v_end):
            b_loc = raw_bone_idx[v_i]
            w_loc = raw_bone_w[v_i]
            slot = 0
            for j in range(4):
                w = int(w_loc[j])
                if w == 0:
                    continue
                orig_b = bmap[int(b_loc[j])]
                if slot == 0:
                    raw_bone_primary[v_i] = orig_b
                joints_0[v_i, slot] = old_to_new_bone[orig_b]
                weights_0[v_i, slot] = w
                slot += 1
            # Normalize weights to sum to 255 if needed
            w_sum = int(weights_0[v_i, :slot].sum())
            if slot > 0 and w_sum != 255:
                scale = 255.0 / w_sum
                new_w = [int(round(weights_0[v_i, k] * scale)) for k in range(slot)]
                new_w[0] += 255 - sum(new_w)
                for k in range(slot):
                    weights_0[v_i, k] = max(0, min(255, new_w[k]))

    # Parse Sockets referenced by this SkeletalMesh
    sockets = []
    sock_prop = props.get('Sockets', {})
    for s_obj in sock_prop.get('as_objects', []):
        s_idx = s_obj['index']
        if s_idx > 0:
            s_exp = upk.exports[s_idx - 1]
            upk.pos = s_exp['serial_offset'] + 4
            s_props = upk.parse_properties(s_exp['serial_offset'] + s_exp['serial_size'])
            loc = s_props.get('RelativeLocation', {'x': 0.0, 'y': 0.0, 'z': 0.0})
            rot = s_props.get('RelativeRotation', {'pitch': 0, 'yaw': 0, 'roll': 0, 'pitch_deg': 0.0, 'yaw_deg': 0.0, 'roll_deg': 0.0})
            scale = s_props.get('RelativeScale', {'x': 1.0, 'y': 1.0, 'z': 1.0})
            sockets.append({
                "export_index": s_idx,
                "object_name": s_exp['name'],
                "socket_name": s_props.get('SocketName', s_exp['name']),
                "bone_name": s_props.get('BoneName', 'chassis_jnt'),
                "relative_location_uu": [loc.get('x', 0.0), loc.get('y', 0.0), loc.get('z', 0.0)],
                "relative_location_gltf_m": [
                    round(loc.get('x', 0.0) * 0.01, 6),
                    round(loc.get('z', 0.0) * 0.01, 6),
                    round(loc.get('y', 0.0) * 0.01, 6),
                ],
                "relative_rotation_uerot": [rot.get('pitch', 0), rot.get('yaw', 0), rot.get('roll', 0)],
                "relative_rotation_deg": [rot.get('pitch_deg', 0.0), rot.get('yaw_deg', 0.0), rot.get('roll_deg', 0.0)],
                "relative_scale": [scale.get('x', 1.0), scale.get('y', 1.0), scale.get('z', 1.0)],
            })

    return {
        "name": exp['name'],
        "export_index": exp['index'],
        "group_dir": upk.get_group_dir(exp['index']),
        "properties": props,
        "bounds": {
            "origin": [round(x, 6) for x in bounds[:3]],
            "box_extent": [round(x, 6) for x in bounds[3:6]],
            "sphere_radius": round(bounds[6], 6),
        },
        "materials": materials,
        "origin": list(origin),
        "rot_origin": list(rot_origin),
        "skeletal_depth": skel_depth,
        "raw_bones": raw_bones,
        "sorted_bones": sorted_bones,
        "sections": sections,
        "chunks": chunks,
        "num_vertices": elem_count,
        "num_triangles": idx_elem_count // 3,
        "num_uv_sets": gpu_num_uvs,
        "indices": indices,
        "positions_ue": pos_ue,
        "positions_gltf": pos_gltf,
        "normals_gltf": normals_gltf,
        "tangents_gltf": tangents_gltf,
        "uv_sets": uv_sets,
        "vertex_colors_rgba": vcolors_rgba,
        "vertex_colors_raw": vcolors_raw_bytes,
        "joints_0": joints_0,
        "weights_0": weights_0,
        "raw_bone_primary": raw_bone_primary,
        "sockets": sockets,
    }


def deserialize_static_mesh(upk: UPKPackage, exp_idx: int) -> dict:
    """Deserializes a UStaticMesh export (0-based index in upk.exports)."""
    exp = upk.exports[exp_idx]
    end_pos = exp['serial_offset'] + exp['serial_size']
    upk.pos = exp['serial_offset'] + 4
    props = upk.parse_properties(end_pos)
    pos = upk.pos
    data = upk.data

    bounds = struct.unpack_from('<7f', data, pos); pos += 28
    body_setup = struct.unpack_from('<i', data, pos)[0]; pos += 4
    kdop_bounds = struct.unpack_from('<6f', data, pos); pos += 24
    kn_size, kn_count = struct.unpack_from('<II', data, pos); pos += 8 + kn_size * kn_count
    kt_size, kt_count = struct.unpack_from('<II', data, pos); pos += 8 + kt_size * kt_count
    internal_ver = struct.unpack_from('<I', data, pos)[0]; pos += 4

    unk_flag = struct.unpack_from('<I', data, pos)[0]; pos += 4
    f178_count = struct.unpack_from('<I', data, pos)[0]; pos += 4 + f178_count * 7
    f74, unk859, lod_count = struct.unpack_from('<III', data, pos); pos += 12

    # LOD 0
    bflags, belem, bsize = struct.unpack_from('<III', data, pos)
    pos += 12 + (8 if (bflags & 1) else bsize)
    sec_count = struct.unpack_from('<I', data, pos)[0]; pos += 4
    sections = []
    materials = []
    for s_i in range(sec_count):
        mat, f10, f14, shadow, first_idx, num_faces, f24, f28, idx = struct.unpack_from('<iiiiiiiii', data, pos)
        pos += 36
        f30_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4 + f30_count * 8 + 1
        mat_name = upk.get_obj_name(mat) if mat != 0 else f"dummy_material_{s_i}"
        materials.append(mat_name)
        sections.append({
            "section_index": s_i,
            "material_index": s_i,
            "material_name": mat_name,
            "first_index": first_idx,
            "num_triangles": num_faces,
            "first_vertex": f24,
            "last_vertex": f28,
        })

    vs_size, vs_num, vs_bsize, vs_bcount = struct.unpack_from('<IIII', data, pos); pos += 16
    pos_ue = np.frombuffer(data, dtype='<f4', offset=pos, count=vs_bcount * 3).reshape(-1, 3).copy()
    pos += vs_bsize * vs_bcount
    pos_gltf = np.stack([pos_ue[:, 0] * 0.01, pos_ue[:, 2] * 0.01, pos_ue[:, 1] * 0.01], axis=1).astype(np.float32)

    uv_tc, uv_isize, uv_num, uv_full, uv_bsize, uv_bcount = struct.unpack_from('<IIIIII', data, pos); pos += 24
    uv_raw = np.frombuffer(data, dtype=np.uint8, offset=pos, count=uv_bsize * uv_bcount).reshape(uv_bcount, uv_bsize)
    pos += uv_bsize * uv_bcount

    n0_arr = np.frombuffer(uv_raw[:, 0:4].tobytes(), dtype='<u4')
    n2_arr = np.frombuffer(uv_raw[:, 4:8].tobytes(), dtype='<u4')
    normals_gltf, tangents_gltf = unpack_normals_and_tangents(n0_arr, n2_arr)

    uv_sets = []
    for uv_i in range(uv_tc):
        if uv_full:
            uv_off = 8 + uv_i * 8
            uv_arr = np.frombuffer(uv_raw[:, uv_off:uv_off + 8].tobytes(), dtype='<f4').reshape(uv_bcount, 2).copy()
        else:
            uv_off = 8 + uv_i * 4
            uv_arr = np.frombuffer(uv_raw[:, uv_off:uv_off + 4].tobytes(), dtype='<f2').reshape(uv_bcount, 2).astype(np.float32)
        uv_sets.append(uv_arr)

    cs_isize, cs_num = struct.unpack_from('<II', data, pos); pos += 8
    vcolors_raw = None
    vcolors_rgba = None
    if cs_num > 0:
        cs_bsize, cs_bcount = struct.unpack_from('<II', data, pos); pos += 8
        vc_bgra = np.frombuffer(data, dtype=np.uint8, offset=pos, count=cs_bcount * 4).reshape(cs_bcount, 4).copy()
        pos += cs_bsize * cs_bcount
        # Check if all white or all black (as in UStaticMesh3::ConvertMesh)
        u32_view = vc_bgra.view(np.uint32)
        if not (np.all(u32_view == 0) or np.all(u32_view == 0xFFFFFFFF)):
            vcolors_raw = vc_bgra
            vcolors_rgba = vc_bgra[:, [2, 1, 0, 3]].copy()

    lod_num_verts = struct.unpack_from('<I', data, pos)[0]; pos += 4
    ib_size, ib_count = struct.unpack_from('<II', data, pos); pos += 8
    indices = np.frombuffer(
        data, dtype='<u2' if ib_size == 2 else '<u4', offset=pos, count=ib_count
    ).astype(np.uint32)

    return {
        "name": exp['name'],
        "export_index": exp['index'],
        "group_dir": upk.get_group_dir(exp['index']),
        "properties": props,
        "bounds": {
            "origin": [round(x, 6) for x in bounds[:3]],
            "box_extent": [round(x, 6) for x in bounds[3:6]],
            "sphere_radius": round(bounds[6], 6),
        },
        "materials": materials,
        "sections": sections,
        "num_vertices": vs_bcount,
        "num_triangles": ib_count // 3,
        "num_uv_sets": uv_tc,
        "indices": indices,
        "positions_ue": pos_ue,
        "positions_gltf": pos_gltf,
        "normals_gltf": normals_gltf,
        "tangents_gltf": tangents_gltf,
        "uv_sets": uv_sets,
        "vertex_colors_rgba": vcolors_rgba,
        "vertex_colors_raw": vcolors_raw,
    }


def build_skeleton_nodes_and_ibm(mesh_data: dict, include_sockets: bool = False):
    """
    Builds glTF nodes and inverseBindMatrices (N, 4, 4) for a SkeletalMesh.
    Node 0 is the mesh root node ("children": [1]).
    Nodes 1..num_bones are the sorted skeleton bones.
    If include_sockets=True, appends socket child nodes to their respective parent bones.
    """
    sorted_bones = mesh_data["sorted_bones"]
    num_bones = len(sorted_bones)
    nodes = [{
        "name": mesh_data["name"],
        "mesh": 0,
        "skin": 0,
        "children": [1],
    }]

    bone_coords = {}
    ibm_list = []
    bone_name_to_node_idx = {}

    for b_idx, b in enumerate(sorted_bones):
        node_idx = b_idx + 1
        bone_name_to_node_idx[b["name"]] = node_idx
        children = [
            j + 1 for j in range(num_bones)
            if j != b_idx and sorted_bones[j]["parent_index"] == b_idx
        ]
        pos_ue = b["position_xyz"]
        quat_ue = list(b["orientation_xyzw"])
        # In USkeletalMesh3::ConvertMesh(), for i >= 1: Orientation.W *= -1
        # Wait: note that i >= 1 in ConvertMesh is before SortBones, which is all non-root bones (b_idx >= 1)!
        if b["original_index"] >= 1:
            quat_ue[3] *= -1.0
        # In ExportSkinData(): if boneIndex == 0: boneRot.Conjugate()
        if b_idx == 0:
            quat_ue[0] = -quat_ue[0]
            quat_ue[1] = -quat_ue[1]
            quat_ue[2] = -quat_ue[2]

        # TransformPosition & TransformRotation (swap Y and Z, scale pos by 0.01)
        bone_pos = [
            round(pos_ue[0] * 0.01, 6),
            round(pos_ue[2] * 0.01, 6),
            round(pos_ue[1] * 0.01, 6),
        ]
        bone_rot = [
            round(quat_ue[0], 6),
            round(quat_ue[2], 6),
            round(quat_ue[1], 6),
            round(quat_ue[3], 6),
        ]

        node_obj = {"name": b["name"]}
        if children:
            node_obj["children"] = children
        node_obj["translation"] = bone_pos
        node_obj["rotation"] = bone_rot
        nodes.append(node_obj)

        # Compute IBM
        q_ibm = np.array([quat_ue[0], quat_ue[2], quat_ue[1], -quat_ue[3]], dtype=np.float32)
        p_ibm = np.array([pos_ue[0] * 0.01, pos_ue[2] * 0.01, pos_ue[1] * 0.01], dtype=np.float32)
        axis = quat_to_axis(q_ibm)
        if b_idx > 0:
            p_orig, p_axis = bone_coords[b["parent_index"]]
            p_ibm, axis = untransform_coords(p_orig, p_axis, p_ibm, axis)
        bone_coords[b_idx] = (p_ibm, axis)
        ibm_list.append(invert_coords(p_ibm, axis))

    if include_sockets and mesh_data.get("sockets"):
        for sock in mesh_data["sockets"]:
            parent_node = bone_name_to_node_idx.get(sock["bone_name"], 1)
            sock_node_idx = len(nodes)
            nodes[parent_node].setdefault("children", []).append(sock_node_idx)
            nodes.append({
                "name": f"Socket_{sock['socket_name']}",
                "translation": sock["relative_location_gltf_m"],
                "scale": sock["relative_scale"],
                "extras": {
                    "type": "SkeletalMeshSocket",
                    "socketName": sock["socket_name"],
                    "boneName": sock["bone_name"],
                    "relativeLocationUU": sock["relative_location_uu"],
                    "relativeRotationDeg": sock["relative_rotation_deg"],
                },
            })

    ibm_arr = np.stack(ibm_list, axis=0).astype(np.float32)
    joints = list(range(1, num_bones + 1))
    return nodes, ibm_arr, joints


def export_raw_gltf_and_bin(mesh_data: dict, out_dir: str, is_skeletal: bool = True):
    """
    Exports a SkeletalMesh or StaticMesh to `<name>.gltf` and `<name>.bin` in `out_dir`,
    matching UE Viewer (umodel) glTF 2.0 structure.
    """
    os.makedirs(out_dir, exist_ok=True)
    name = mesh_data["name"]
    bin_chunks = []
    buffer_views = []
    accessors = []

    def add_buffer(arr_bytes: bytes, count: int, comp_type: int, acc_type: str, normalized: bool = False, bounds_min=None, bounds_max=None):
        pad = (4 - (len(arr_bytes) % 4)) % 4
        if pad:
            arr_bytes = arr_bytes + b'\x00' * pad
        bv_idx = len(buffer_views)
        byte_offset = sum(len(c) for c in bin_chunks)
        bin_chunks.append(arr_bytes)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(arr_bytes),
        })
        acc = {
            "bufferView": bv_idx,
        }
        if normalized:
            acc["normalized"] = True
        if bounds_min is not None and bounds_max is not None:
            acc["min"] = [round(float(x), 6) for x in bounds_min]
            acc["max"] = [round(float(x), 6) for x in bounds_max]
        acc["componentType"] = comp_type
        acc["count"] = count
        acc["type"] = acc_type
        accessors.append(acc)
        return len(accessors) - 1

    if is_skeletal:
        nodes, ibm_arr, joints = build_skeleton_nodes_and_ibm(mesh_data, include_sockets=False)
        ibm_acc_idx = add_buffer(ibm_arr.tobytes(), len(joints), 5126, "MAT4")
        skins = [{
            "inverseBindMatrices": ibm_acc_idx,
            "skeleton": 1,
            "joints": joints,
        }]
    else:
        nodes = [{"name": name, "mesh": 0}]
        skins = None

    materials = []
    primitives = []
    all_indices = mesh_data["indices"]
    pos_gltf = mesh_data["positions_gltf"]
    norm_gltf = mesh_data["normals_gltf"]
    tang_gltf = mesh_data["tangents_gltf"]
    uv_sets = mesh_data["uv_sets"]
    vc_rgba = mesh_data["vertex_colors_rgba"]

    for s_idx, sec in enumerate(mesh_data["sections"]):
        color = get_material_debug_color(s_idx)
        materials.append({
            "name": sec["material_name"],
            "pbrMetallicRoughness": {
                "baseColorFactor": [round(color[0], 4), round(color[1], 4), round(color[2], 4), 1.0],
                "metallicFactor": 0.1,
                "roughnessFactor": 0.5,
            },
        })
        sec_idx_slice = all_indices[sec["first_index"]:sec["first_index"] + sec["num_triangles"] * 3]
        # Remap to local indices in order of first appearance (matching ExportSection in ExportGLTF.cpp)
        unique_verts = []
        remap = {}
        local_indices = np.empty(len(sec_idx_slice), dtype=np.uint32)
        for k, v_orig in enumerate(sec_idx_slice):
            v_int = int(v_orig)
            if v_int not in remap:
                remap[v_int] = len(unique_verts)
                unique_verts.append(v_int)
            local_indices[k] = remap[v_int]
        u_arr = np.array(unique_verts, dtype=np.uint32)
        num_local = len(u_arr)

        if num_local <= 65536:
            idx_acc = add_buffer(local_indices.astype(np.uint16).tobytes(), len(local_indices), 5123, "SCALAR")
        else:
            idx_acc = add_buffer(local_indices.astype(np.uint32).tobytes(), len(local_indices), 5125, "SCALAR")

        p_sub = pos_gltf[u_arr]
        pos_acc = add_buffer(
            p_sub.tobytes(), num_local, 5126, "VEC3",
            bounds_min=p_sub.min(axis=0), bounds_max=p_sub.max(axis=0)
        )
        norm_acc = add_buffer(norm_gltf[u_arr].tobytes(), num_local, 5126, "VEC3")
        tang_acc = add_buffer(tang_gltf[u_arr].tobytes(), num_local, 5126, "VEC4")

        attrs = {
            "POSITION": pos_acc,
            "NORMAL": norm_acc,
            "TANGENT": tang_acc,
        }
        if vc_rgba is not None:
            vc_acc = add_buffer(vc_rgba[u_arr].tobytes(), num_local, 5121, "VEC4", normalized=True)
            attrs["COLOR_0"] = vc_acc
        if is_skeletal:
            j_acc = add_buffer(mesh_data["joints_0"][u_arr].tobytes(), num_local, 5123, "VEC4")
            w_acc = add_buffer(mesh_data["weights_0"][u_arr].tobytes(), num_local, 5121, "VEC4", normalized=True)
            attrs["JOINTS_0"] = j_acc
            attrs["WEIGHTS_0"] = w_acc
        for uv_i, uv_arr in enumerate(uv_sets):
            uv_acc = add_buffer(uv_arr[u_arr].tobytes(), num_local, 5126, "VEC2")
            attrs[f"TEXCOORD_{uv_i}"] = uv_acc

        primitives.append({
            "attributes": attrs,
            "indices": idx_acc,
            "material": s_idx,
        })

    bin_data = b"".join(bin_chunks)
    gltf_obj = {
        "asset": {
            "generator": "RLCars UPK Python Extractor (UE Viewer glTF 2.0 compatible)",
            "version": "2.0",
        },
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
    }
    if skins is not None:
        gltf_obj["skins"] = skins
    gltf_obj["materials"] = materials
    gltf_obj["meshes"] = [{
        "primitives": primitives,
        "name": name,
    }]
    gltf_obj["buffers"] = [{
        "uri": f"{name}.bin",
        "byteLength": len(bin_data),
    }]
    gltf_obj["bufferViews"] = buffer_views
    gltf_obj["accessors"] = accessors

    gltf_path = os.path.join(out_dir, f"{name}.gltf")
    bin_path = os.path.join(out_dir, f"{name}.bin")
    with open(gltf_path, "w", encoding="utf-8") as f:
        json.dump(gltf_obj, f, indent=2)
    with open(bin_path, "wb") as f:
        f.write(bin_data)
    return gltf_path, bin_path


def write_glb_file(gltf_dict: dict, bin_data: bytes, out_path: str):
    """Packs a glTF 2.0 JSON dict and binary buffer into a standard .glb file."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json_bytes = json.dumps(gltf_dict, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    if json_pad:
        json_bytes += b' ' * json_pad

    bin_pad = (4 - (len(bin_data) % 4)) % 4
    if bin_pad:
        bin_data += b'\x00' * bin_pad

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    with open(out_path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total_len))  # 'glTF', version 2, length
        f.write(struct.pack('<II', len(json_bytes), 0x4E4F534A))  # JSON chunk
        f.write(json_bytes)
        f.write(struct.pack('<II', len(bin_data), 0x004E4942))  # BIN chunk
        f.write(bin_data)
    return out_path
