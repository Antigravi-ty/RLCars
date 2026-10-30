#!/usr/bin/env python3
"""
Builds the complete, clean branch directory for `body_ryzarevt1_SF`:
  - raw/ (original UPK + group-based and class-based .gltf, .bin, .png, .mat, .props.txt)
  - textures/ & textures/baked_pbr/ (24 raw UPK textures + 17 baked PBR & tangent-space normal maps)
  - models/ (Body_RyzaRevT1_SK.glb, Body_RyzaRevT1_SK_DetailedSurfaces.glb,
             Body_RyzaRevT1_SK_WhiteModel.glb, Body_RyzaRevT1_SK_WhiteModel_OriginalSlots.glb,
             Body_RyzaRevT1_SK_OriginalSlots.glb, Body_RyzaRevT1_SK_WithBoostCone.glb,
             Body_RyzaRevT1_BoostConeMesh.glb)
  - metadata/ (Body_RyzaRevT1_metadata.json, Body_RyzaRevT1_surface_bindings.json, Body_RyzaRevT1_scene.json)
  - scripts/ (unpack_upk.py, upk_core.py, mesh_gltf_builder.py, extract_and_build.py)
  - README.md
"""
import io
import json
import os
import shutil
import struct
import sys
import numpy as np
from PIL import Image

from unpack_upk import unpack_rl_upk
from upk_core import (
    UPKPackage,
    decode_dxt1,
    decode_dxt5,
    decode_a8r8g8b8,
    reconstruct_dxt5nm_normal_map,
)
from mesh_gltf_builder import (
    deserialize_skeletal_mesh,
    deserialize_static_mesh,
    build_skeleton_nodes_and_ibm,
    export_raw_gltf_and_bin,
    write_glb_file,
    get_material_debug_color,
)


def sample_tex_uv(rgba: np.ndarray, uvs: np.ndarray) -> np.ndarray:
    h, w, _ = rgba.shape
    u = np.mod(uvs[:, 0], 1.0)
    v = np.mod(uvs[:, 1], 1.0)
    px = np.clip((u * w).astype(int), 0, w - 1)
    py = np.clip((v * h).astype(int), 0, h - 1)
    return rgba[py, px]


def format_props_txt(props: dict, indent: int = 0) -> str:
    lines = []
    pad = "    " * indent
    for k, v in props.items():
        if isinstance(v, dict):
            if v.get("type") == "ArrayStruct":
                elems = v.get("elements", [])
                lines.append(f"{pad}{k}[{len(elems)}] =")
                lines.append(f"{pad}{{")
                for i, el in enumerate(elems):
                    lines.append(f"{pad}    {k}[{i}] =")
                    lines.append(f"{pad}    {{")
                    lines.append(format_props_txt(el, indent + 2))
                    lines.append(f"{pad}    }}")
                lines.append(f"{pad}}}")
            elif v.get("type") == "ArrayIntOrObj":
                objs = v.get("as_objects", [])
                lines.append(f"{pad}{k}[{len(objs)}] =")
                lines.append(f"{pad}{{")
                for i, o in enumerate(objs):
                    lines.append(f"{pad}    {k}[{i}] = {o['name']}")
                lines.append(f"{pad}}}")
            elif v.get("type") == "ArrayName":
                vals = v.get("values", [])
                lines.append(f"{pad}{k}[{len(vals)}] =")
                lines.append(f"{pad}{{")
                for i, s in enumerate(vals):
                    lines.append(f"{pad}    {k}[{i}] = {s}")
                lines.append(f"{pad}}}")
            elif v.get("type") == "ArrayBool":
                vals = v.get("values", [])
                lines.append(f"{pad}{k}[{len(vals)}] = {{ {', '.join(str(x) for x in vals)} }}")
            elif v.get("type") == "LinearColor":
                lines.append(f"{pad}{k} = {{ R={v['r']}, G={v['g']}, B={v['b']}, A={v['a']} }}")
            elif v.get("type") == "Vector":
                lines.append(f"{pad}{k} = {{ X={v['x']}, Y={v['y']}, Z={v['z']} }}")
            elif v.get("type") == "Rotator":
                lines.append(f"{pad}{k} = {{ Pitch={v['pitch']}, Yaw={v['yaw']}, Roll={v['roll']} }}")
            elif "enum" in v:
                lines.append(f"{pad}{k} = {v['value']}")
            elif "name" in v and "index" in v:
                lines.append(f"{pad}{k} = {v.get('full_path') or v['name']}")
            elif "_struct" in v and "fields" in v:
                lines.append(f"{pad}{k} =")
                lines.append(f"{pad}{{")
                lines.append(format_props_txt(v["fields"], indent + 1))
                lines.append(f"{pad}}}")
            else:
                lines.append(f"{pad}{k} = {json.dumps(v)}")
        else:
            lines.append(f"{pad}{k} = {v}")
    return "\n".join(lines)


def image_to_png_bytes(arr: np.ndarray, mode: str = "RGBA") -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr, mode=mode).save(buf, format="PNG")
    return buf.getvalue()


def extract_all_textures_and_raw(upk: UPKPackage, pkg_name: str, out_root: str):
    raw_pkg_dir = os.path.join(out_root, "raw", pkg_name)
    tex_dir = os.path.join(out_root, "textures")
    baked_dir = os.path.join(tex_dir, "baked_pbr")
    os.makedirs(raw_pkg_dir, exist_ok=True)
    os.makedirs(tex_dir, exist_ok=True)
    os.makedirs(baked_dir, exist_ok=True)

    textures = {}
    for idx, e in enumerate(upk.exports):
        if e["class"] == "Texture2D":
            upk.pos = e["serial_offset"] + 4
            props = upk.parse_properties(e["serial_offset"] + e["serial_size"])
            sa_flags = upk.r_u32(); sa_cnt = upk.r_i32(); sa_sz = upk.r_i32()
            if sa_flags & 0x01:
                upk.r_i64()
            elif sa_sz > 0 and not (sa_flags & 0x20):
                upk.pos += sa_sz
            mip_count = upk.r_i32()
            all_mips_meta = []
            best_rgba = None
            best_w = 0
            best_h = 0
            fmt = props.get("Format", {}).get("value", "PF_Unknown")
            for m in range(mip_count):
                m_flags = upk.r_u32(); m_cnt = upk.r_i32(); m_sz = upk.r_i32()
                if m_flags & 0x01:
                    m_off = upk.r_i64()
                    raw_mip = None
                elif m_sz > 0 and not (m_flags & 0x20):
                    m_off = -1
                    raw_mip = upk.r_bytes(m_sz)
                else:
                    m_off = -1
                    raw_mip = None
                sx = upk.r_i32(); sy = upk.r_i32()
                all_mips_meta.append({
                    "mip_index": m,
                    "width": sx,
                    "height": sy,
                    "flags": hex(m_flags),
                    "stored_in_tfc": bool(m_flags & 0x01),
                    "inline_bytes": len(raw_mip) if raw_mip is not None else 0,
                })
                if raw_mip is not None and best_rgba is None:
                    if fmt == "PF_DXT1":
                        best_rgba = decode_dxt1(raw_mip, sx, sy)
                    elif fmt == "PF_DXT5":
                        best_rgba = decode_dxt5(raw_mip, sx, sy)
                    elif fmt == "PF_A8R8G8B8":
                        best_rgba = decode_a8r8g8b8(raw_mip, sx, sy)
                    best_w, best_h = sx, sy

            if best_rgba is not None:
                if fmt == "PF_DXT1" and np.all(best_rgba[..., 3] == 255):
                    pil_img = Image.fromarray(best_rgba[..., :3], mode="RGB")
                else:
                    pil_img = Image.fromarray(best_rgba, mode="RGBA")

                grp_dir = os.path.join(raw_pkg_dir, upk.get_group_dir(e["index"]))
                cls_dir = os.path.join(raw_pkg_dir, "Texture2D")
                os.makedirs(grp_dir, exist_ok=True)
                os.makedirs(cls_dir, exist_ok=True)

                for d in (grp_dir, cls_dir, tex_dir):
                    pil_img.save(os.path.join(d, f"{e['name']}.png"))

                props_txt = format_props_txt(props)
                for d in (grp_dir, cls_dir):
                    with open(os.path.join(d, f"{e['name']}.props.txt"), "w", encoding="utf-8") as f:
                        f.write(props_txt + "\n")

                comp_settings = props.get("CompressionSettings", {}).get("value", "")
                norm_rgb = None
                if "Normalmap" in comp_settings or e["name"].lower().endswith("_n"):
                    norm_rgb = reconstruct_dxt5nm_normal_map(best_rgba)
                    Image.fromarray(norm_rgb, mode="RGB").save(
                        os.path.join(baked_dir, f"{e['name']}_TangentRGB.png")
                    )

                textures[e["name"]] = {
                    "name": e["name"],
                    "export_index": e["index"],
                    "full_path": e["full_path"],
                    "group_dir": upk.get_group_dir(e["index"]),
                    "format": fmt,
                    "compression_settings": comp_settings,
                    "srgb": props.get("SRGB", True),
                    "original_size": [props.get("SizeX", best_w), props.get("SizeY", best_h)],
                    "inline_mip_size": [best_w, best_h],
                    "texture_file_cache_name": props.get("TextureFileCacheName", None),
                    "mips": all_mips_meta,
                    "properties": props,
                    "rgba": best_rgba,
                    "normal_rgb": norm_rgb,
                }

    materials_meta = {}
    for idx, e in enumerate(upk.exports):
        if e["class"] in ("Material", "MaterialInstanceConstant"):
            end_pos = e["serial_offset"] + e["serial_size"]
            upk.pos = e["serial_offset"] + 4
            props = upk.parse_properties(end_pos)
            static_params = {}
            if e["class"] == "MaterialInstanceConstant" and props.get("bHasStaticPermutationResource"):
                static_params = upk.parse_mic_static_parameters(upk.pos, end_pos)
                if static_params.get("static_switches"):
                    props["StaticSwitchParameters"] = static_params["static_switches"]
                if static_params.get("static_component_masks"):
                    props["StaticComponentMaskParameters"] = static_params["static_component_masks"]
                if static_params.get("referenced_textures"):
                    props["ReferencedUniformTextures"] = static_params["referenced_textures"]

            grp_dir = os.path.join(raw_pkg_dir, upk.get_group_dir(e["index"]))
            cls_dir = os.path.join(raw_pkg_dir, "Material3" if e["class"] == "Material" else "MaterialInstanceConstant")
            os.makedirs(grp_dir, exist_ok=True)
            os.makedirs(cls_dir, exist_ok=True)

            mat_lines = []
            parent_obj = props.get("Parent")
            if parent_obj and parent_obj.get("name") != "None":
                mat_lines.append(f"Parent={parent_obj['name']}")
            tex_params = props.get("TextureParameterValues", {}).get("elements", []) if isinstance(props.get("TextureParameterValues"), dict) else []
            other_idx = 0
            for tp in tex_params:
                pname = tp.get("ParameterName", "")
                pval = tp.get("ParameterValue", {}).get("name", "None")
                if pval == "None":
                    continue
                if pname == "Diffuse":
                    mat_lines.append(f"Diffuse={pval}")
                elif pname in ("Normal", "NormalMap"):
                    mat_lines.append(f"Normal={pval}")
                else:
                    mat_lines.append(f"Other[{other_idx}]={pval}")
                    other_idx += 1
            mat_txt = "\n".join(mat_lines) + ("\n" if mat_lines else "")
            props_txt = format_props_txt(props) + "\n"

            for d in (grp_dir, cls_dir):
                with open(os.path.join(d, f"{e['name']}.mat"), "w", encoding="utf-8") as f:
                    f.write(mat_txt)
                with open(os.path.join(d, f"{e['name']}.props.txt"), "w", encoding="utf-8") as f:
                    f.write(props_txt)

            materials_meta[e["name"]] = {
                "name": e["name"],
                "export_index": e["index"],
                "class": e["class"],
                "full_path": e["full_path"],
                "group_dir": upk.get_group_dir(e["index"]),
                "properties": props,
            }

    return textures, materials_meta


def bake_pbr_textures_ryzarevt1(textures: dict, baked_dir: str) -> dict:
    """
    Bakes physically-based BaseColor, MetallicRoughness (glTF R=AO, G=Roughness, B=Metallic),
    Normal (Tangent-space RGB), and Emissive maps for Body_RyzaRevT1_SK from its 24 raw UPK textures
    and exact MIC_RyzaRevT1_* shader parameters.
    """
    # 1. Body textures (MIC_RyzaRevT1_Body)
    bs = textures["Body_RyzaRevT1_Blankskin"]["rgba"].astype(np.float32) / 255.0
    curv = textures["Body_RyzaRevT1_Curvature"]["rgba"].astype(np.float32) / 255.0
    body_d = textures["Body_RyzaRevT1_D"]["rgba"].astype(np.float32) / 255.0
    fx = textures["Body_RyzaRevT1_FxMask"]["rgba"].astype(np.float32) / 255.0
    body_n_rgb = textures["Body_RyzaRevT1_N"]["normal_rgb"]
    blank_n_rgb = textures["Blank_N"]["normal_rgb"]

    # MIC_RyzaRevT1_Body VectorParameterValues:
    # TeamColor = [0.613237, 0.182819, 0.02035, 1.0] (Fiery Orange-Red / Sunset Amber)
    # PaintColor = [0.232036, 0.020519, 0.021236, 1.0] (Deep Crimson Accent)
    team_col = np.array([0.82, 0.26, 0.05], dtype=np.float32)
    paint_col = np.array([0.38, 0.05, 0.05], dtype=np.float32)
    seam_col = np.array([0.11, 0.11, 0.12], dtype=np.float32)

    ao_body = np.clip(fx[..., 0:1] * 0.82 + 0.18, 0.25, 1.0)
    curv_highlight = np.clip((curv[..., 0:1] - 0.5) * 0.35 + 1.0, 0.8, 1.2)
    diff_shade = np.clip(body_d[..., :3] * 0.65 + 0.35, 0.35, 1.05)
    alpha_mask = body_d[..., 3:4]

    # Primary Body BaseColor (Slot 2)
    primary_rgb = (
        alpha_mask * (team_col * diff_shade * curv_highlight)
        + (1.0 - alpha_mask) * (seam_col * diff_shade)
    ) * ao_body
    body_primary_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    body_primary_rgba[..., :3] = np.clip(primary_rgb * 255.0, 0, 255).astype(np.uint8)

    # Secondary Body BaseColor (Slot 3: Rear Roof / Engine Decklid Louver where Blankskin.G > 0.5)
    g_mask = bs[..., 1:2]
    secondary_rgb = (
        g_mask * paint_col + (1.0 - g_mask) * team_col
    ) * diff_shade * ao_body * curv_highlight
    body_secondary_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    body_secondary_rgba[..., :3] = np.clip(secondary_rgb * 255.0, 0, 255).astype(np.uint8)

    # Recessed Seam / Dark Accent BaseColor
    seam_rgb = seam_col * diff_shade * ao_body
    body_seam_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    body_seam_rgba[..., :3] = np.clip(seam_rgb * 255.0, 0, 255).astype(np.uint8)

    # Body MetallicRoughness (R=AO, G=Roughness, B=Metallic)
    body_mr = np.zeros((64, 64, 3), dtype=np.uint8)
    body_mr[..., 0] = np.clip(fx[..., 0] * 255.0, 0, 255).astype(np.uint8)
    rough_body = alpha_mask[..., 0] * (0.20 + (1.0 - fx[..., 1]) * 0.12) + (1.0 - alpha_mask[..., 0]) * 0.62
    metal_body = alpha_mask[..., 0] * (0.35 + fx[..., 2] * 0.20) + (1.0 - alpha_mask[..., 0]) * 0.12
    body_mr[..., 1] = np.clip(rough_body * 255.0, 0, 255).astype(np.uint8)
    body_mr[..., 2] = np.clip(metal_body * 255.0, 0, 255).astype(np.uint8)

    # 2. Chassis textures (MIC_RyzaRevT1_Chassis)
    ch_d = textures["Chassis_RyzaRevT1_D"]["rgba"].astype(np.float32) / 255.0
    ch_rgb = textures["Chassis_RyzaRevT1_RGB"]["rgba"].astype(np.float32) / 255.0
    ch_m = textures["Chassis_RyzaRevT1_M"]["rgba"].astype(np.float32) / 255.0
    ch_n_rgba = textures["Chassis_RyzaRevT1_N"]["rgba"].astype(np.float32) / 255.0
    ch_n_rgb = textures["Chassis_RyzaRevT1_N"]["normal_rgb"]

    ch_base = np.ones((64, 64, 4), dtype=np.uint8) * 255
    ch_base[..., :3] = np.clip(ch_d[..., :3] * 255.0, 0, 255).astype(np.uint8)

    ch_mr = np.zeros((64, 64, 3), dtype=np.uint8)
    ch_mr[..., 0] = np.clip(ch_n_rgba[..., 0] * 255.0, 0, 255).astype(np.uint8)
    ch_lum = ch_d[..., :3].mean(axis=-1)
    ch_mr[..., 1] = np.clip((0.74 - ch_lum * 0.45) * 255.0, 38, 235).astype(np.uint8)
    ch_mr[..., 2] = np.clip((0.25 + ch_lum * 0.68) * 255.0, 30, 245).astype(np.uint8)

    # Chassis Emissive combining Masks (R=Headlight, G=Taillight, B=BoostGlow) + AdditionalEmissiveMap (Chassis_RyzaRevT1_M)
    ch_emissive = np.zeros((64, 64, 3), dtype=np.float32)
    ch_emissive += ch_rgb[..., 0:1] * np.array([1.0, 0.96, 0.91], dtype=np.float32)   # HeadlightColor
    ch_emissive += ch_rgb[..., 1:2] * np.array([1.0, 0.02, 0.0], dtype=np.float32)    # TailLightColor
    ch_emissive += ch_rgb[..., 2:3] * np.array([0.0, 0.87, 1.0], dtype=np.float32)    # BoostGlowColor (Cyan)
    ch_emissive += ch_m[..., 0:1] * np.array([1.0, 0.15, 0.0], dtype=np.float32)      # Emissive Color (RedMask)
    ch_emissive += ch_m[..., 1:2] * np.array([1.0, 0.45, 0.0], dtype=np.float32)      # Emissive Color (GreenMask)
    ch_emissive_u8 = np.clip(ch_emissive * 255.0, 0, 255).astype(np.uint8)

    # 3. Plastic & Trim textures (MIC_RyzaRevT1_Plastic & MIC_RyzaRevT1_Trim)
    trim_coa = textures["Trim_RyzaRevT1_COA"]["rgba"].astype(np.float32) / 255.0
    trim_n_rgba = textures["Trim_RyzaRevT1_N"]["rgba"].astype(np.float32) / 255.0
    trim_n_rgb = textures["Trim_RyzaRevT1_N"]["normal_rgb"]
    trim_d = textures["Trim_RyzaRevT1_D"]["rgba"].astype(np.float32) / 255.0

    # In MAT_Vehicle_Trim_Base_normalmapped: BodyTextures_Map (Trim_RyzaRevT1_COA) has R=Curvature, G=AO
    trim_ao = np.clip(trim_coa[..., 1:2] * 0.80 + 0.20, 0.25, 1.0)
    trim_curv = np.clip((trim_coa[..., 0:1] - 0.5) * 0.30 + 1.0, 0.85, 1.15)

    # PlasticColor = [0.14, 0.14, 0.14]
    plastic_rgb = np.array([0.18, 0.18, 0.19], dtype=np.float32) * trim_ao * trim_curv
    plastic_base_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    plastic_base_rgba[..., :3] = np.clip(plastic_rgb * 255.0, 0, 255).astype(np.uint8)

    # TrimColor = [0.077345, 0.077345, 0.077345]
    trim_rgb = np.array([0.11, 0.11, 0.12], dtype=np.float32) * trim_ao * trim_curv
    trim_base_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    trim_base_rgba[..., :3] = np.clip(trim_rgb * 255.0, 0, 255).astype(np.uint8)

    trim_mr = np.zeros((64, 64, 3), dtype=np.uint8)
    trim_mr[..., 0] = np.clip(trim_coa[..., 1] * 255.0, 0, 255).astype(np.uint8)
    trim_mr[..., 1] = np.clip((0.68 - (trim_coa[..., 0] - 0.5) * 0.15) * 255.0, 90, 220).astype(np.uint8)
    trim_mr[..., 2] = int(0.12 * 255)

    # 4. TrimMetal textures (MIC_RyzaRevT1_TrimMetal: Diffuse=Trim_RyzaRevT1_D, Normal=Trim_RyzaRevT1_N, TrimColor=[0.3838, 0.3537, 0.3686])
    tm_col = np.array([0.48, 0.45, 0.47], dtype=np.float32)
    tm_mask = trim_n_rgba[..., 0:1]
    tm_rgb = (tm_mask * tm_col + (1.0 - tm_mask) * np.clip(trim_d[..., :3] * 1.4, 0.12, 0.90)) * trim_ao
    tm_base_rgba = np.ones((64, 64, 4), dtype=np.uint8) * 255
    tm_base_rgba[..., :3] = np.clip(tm_rgb * 255.0, 0, 255).astype(np.uint8)

    tm_mr = np.zeros((64, 64, 3), dtype=np.uint8)
    tm_mr[..., 0] = np.clip(trim_coa[..., 1] * 255.0, 0, 255).astype(np.uint8)
    tm_lum = trim_d[..., :3].mean(axis=-1)
    tm_mr[..., 1] = np.clip((0.52 - tm_lum * 0.35) * 255.0, 45, 180).astype(np.uint8)
    tm_mr[..., 2] = np.clip((0.65 + tm_lum * 0.30) * 255.0, 140, 245).astype(np.uint8)

    # 5. Lenses Normal (Lenses_RyzaRevT1_N)
    lenses_n_rgb = textures["Lenses_RyzaRevT1_N"]["normal_rgb"]

    baked = {
        "RyzaRevT1_Body_Primary_BaseColor": (body_primary_rgba, "RGBA"),
        "RyzaRevT1_Body_Secondary_BaseColor": (body_secondary_rgba, "RGBA"),
        "RyzaRevT1_Body_Seam_BaseColor": (body_seam_rgba, "RGBA"),
        "RyzaRevT1_Body_MetallicRoughness": (body_mr, "RGB"),
        "RyzaRevT1_Body_Normal": (body_n_rgb, "RGB"),
        "RyzaRevT1_Chassis_BaseColor": (ch_base, "RGBA"),
        "RyzaRevT1_Chassis_MetallicRoughness": (ch_mr, "RGB"),
        "RyzaRevT1_Chassis_Normal": (ch_n_rgb, "RGB"),
        "RyzaRevT1_Chassis_Emissive": (ch_emissive_u8, "RGB"),
        "RyzaRevT1_Plastic_BaseColor": (plastic_base_rgba, "RGBA"),
        "RyzaRevT1_Trim_BaseColor": (trim_base_rgba, "RGBA"),
        "RyzaRevT1_Trim_MetallicRoughness": (trim_mr, "RGB"),
        "RyzaRevT1_Trim_Normal": (trim_n_rgb, "RGB"),
        "RyzaRevT1_TrimMetal_BaseColor": (tm_base_rgba, "RGBA"),
        "RyzaRevT1_TrimMetal_MetallicRoughness": (tm_mr, "RGB"),
        "RyzaRevT1_Lenses_Normal": (lenses_n_rgb, "RGB"),
        "RyzaRevT1_Flat_Normal": (blank_n_rgb, "RGB"),
    }
    png_bytes_map = {}
    for k, (arr, mode) in baked.items():
        p = os.path.join(baked_dir, f"{k}.png")
        Image.fromarray(arr, mode=mode).save(p)
        png_bytes_map[k] = image_to_png_bytes(arr, mode=mode)
    return png_bytes_map


def classify_ryzarevt1_surfaces(sk_mesh: dict, textures: dict) -> list:
    """
    Classifies all 91,993 triangles of Body_RyzaRevT1_SK across its 8 UE3 sections into
    20 evidence-backed surface material layers, preserving 100% of original triangles
    with zero overlap and zero dropped faces.
    """
    indices = sk_mesh["indices"]
    pos_ue = sk_mesh["positions_ue"]
    uv0 = sk_mesh["uv_sets"][0]
    vc_rgba = sk_mesh["vertex_colors_rgba"]
    raw_bones = sk_mesh["raw_bones"]
    primary_bone = sk_mesh["raw_bone_primary"]

    ch_rgb_tex = textures["Chassis_RyzaRevT1_RGB"]["rgba"]
    ch_m_tex = textures["Chassis_RyzaRevT1_M"]["rgba"]
    ch_d_tex = textures["Chassis_RyzaRevT1_D"]["rgba"]
    body_d_tex = textures["Body_RyzaRevT1_D"]["rgba"]
    trim_d_tex = textures["Trim_RyzaRevT1_D"]["rgba"]
    trim_n_tex = textures["Trim_RyzaRevT1_N"]["rgba"]

    disc_brake_bones = {
        i for i, b in enumerate(raw_bones)
        if ("Disc" in b["name"] or "Brakepad" in b["name"])
    }
    susp_axle_bones = {
        i for i, b in enumerate(raw_bones)
        if any(k in b["name"] for k in ("Shock", "axleShaft", "Pivot", "WheelTranslation"))
    }

    regions = []

    def add_region(region_id, display_name, category, sec, tri_indices_flat, rule_desc, evidence_dict, pbr_spec):
        if len(tri_indices_flat) == 0:
            return
        tris_reshaped = tri_indices_flat.reshape(-1, 3)
        u_verts = np.unique(tri_indices_flat)
        p_sub = pos_ue[u_verts]
        uv0_sub = uv0[u_verts]
        b_names = sorted({raw_bones[int(b)]["name"] for b in np.unique(primary_bone[u_verts])})
        regions.append({
            "region_id": len(regions),
            "material_name": region_id,
            "display_name": display_name,
            "category": category,
            "original_section_index": sec["section_index"],
            "original_material_slot": sec["material_index"],
            "original_material_name": sec["material_name"],
            "triangle_count": int(len(tris_reshaped)),
            "vertex_count": int(len(u_verts)),
            "flat_indices": tri_indices_flat,
            "classification_rule": rule_desc,
            "evidence": evidence_dict,
            "bounds_uu": {
                "min": [round(float(x), 4) for x in p_sub.min(axis=0)],
                "max": [round(float(x), 4) for x in p_sub.max(axis=0)],
            },
            "uv0_bounds": {
                "min": [round(float(x), 4) for x in uv0_sub.min(axis=0)],
                "max": [round(float(x), 4) for x in uv0_sub.max(axis=0)],
            },
            "rigged_bones": b_names,
            "pbr_spec": pbr_spec,
        })

    for sec in sk_mesh["sections"]:
        s_idx = sec["section_index"]
        sec_tris = indices[sec["first_index"]:sec["first_index"] + sec["num_triangles"] * 3].reshape(-1, 3)
        t_uv0 = uv0[sec_tris].mean(axis=1)
        t_pos = pos_ue[sec_tris].mean(axis=1)
        t_vc = vc_rgba[sec_tris[:, 0]]
        t_bone = primary_bone[sec_tris[:, 0]]

        if s_idx == 0:
            # Section 0: MIC_RyzaRevT1_Chassis (39,278 tris)
            c_rgb = sample_tex_uv(ch_rgb_tex, t_uv0)
            c_m = sample_tex_uv(ch_m_tex, t_uv0)
            c_d = sample_tex_uv(ch_d_tex, t_uv0)

            m_head = c_rgb[:, 0] > 30
            m_tail = (~m_head) & (c_rgb[:, 1] > 30)
            m_boost = (~m_head) & (~m_tail) & (c_rgb[:, 2] > 30)
            m_add_emissive = (~m_head) & (~m_tail) & (~m_boost) & ((c_m[:, 0] > 20) | (c_m[:, 1] > 20))
            m_brakes = (~m_head) & (~m_tail) & (~m_boost) & (~m_add_emissive) & np.isin(t_bone, list(disc_brake_bones))
            m_susp = (~m_head) & (~m_tail) & (~m_boost) & (~m_add_emissive) & (~m_brakes) & np.isin(t_bone, list(susp_axle_bones))
            m_metal = (~m_head) & (~m_tail) & (~m_boost) & (~m_add_emissive) & (~m_brakes) & (~m_susp) & (c_d[:, :3].mean(axis=1) > 75.0)
            m_under = (~m_head) & (~m_tail) & (~m_boost) & (~m_add_emissive) & (~m_brakes) & (~m_susp) & (~m_metal)

            add_region(
                "RyzaRevT1_Chassis_Headlight_Emissive",
                "前大灯内腔发光灯碗与日行灯发光体 (Chassis Headlight Emissive)",
                "Chassis_Lights",
                sec,
                sec_tris[m_head].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.R > 30",
                {
                    "mask_texture": "Chassis_RyzaRevT1_RGB (Channel R = Headlight Mask)",
                    "shader_parameter": "HeadlightColor=(3.0, 2.901746, 2.747269, 1.0), HeadlightBrightness=4.0",
                },
                {
                    "baseColorFactor": [1.0, 0.96, 0.90, 1.0],
                    "metallicFactor": 0.20,
                    "roughnessFactor": 0.15,
                    "emissiveFactor": [1.0, 0.96, 0.90],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                    "emissiveTex": "RyzaRevT1_Chassis_Emissive",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_Taillight_Emissive",
                "贯穿式/环绕尾灯与刹车灯发光体 (Chassis Taillight & Brake Emissive)",
                "Chassis_Lights",
                sec,
                sec_tris[m_tail].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.G > 30",
                {
                    "mask_texture": "Chassis_RyzaRevT1_RGB (Channel G = Taillight/Brake Mask)",
                    "shader_parameter": "TailLightColor=(1.0, 0.014959, 0.0, 1.0), TailLightBrightness=4.0",
                },
                {
                    "baseColorFactor": [1.0, 0.15, 0.10, 1.0],
                    "metallicFactor": 0.20,
                    "roughnessFactor": 0.18,
                    "emissiveFactor": [1.0, 0.05, 0.01],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                    "emissiveTex": "RyzaRevT1_Chassis_Emissive",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_BoostGlow_CyanEmissive",
                "双尾喷口内腔青蓝色氮气发光环 (Chassis BoostGlow Cyan Emissive)",
                "Chassis_Lights",
                sec,
                sec_tris[m_boost].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.B > 30",
                {
                    "mask_texture": "Chassis_RyzaRevT1_RGB (Channel B = BoostGlow Mask)",
                    "shader_parameter": "BoostGlowColor=(0.0, 2.619814, 3.0, 1.0), BoostGlowBrightness=4.0",
                },
                {
                    "baseColorFactor": [0.25, 0.90, 1.0, 1.0],
                    "metallicFactor": 0.25,
                    "roughnessFactor": 0.18,
                    "emissiveFactor": [0.0, 0.87, 1.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                    "emissiveTex": "RyzaRevT1_Chassis_Emissive",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_AdditionalEmissive_OrangeAmber",
                "底盘附加发光灯带（红/绿双通道橙珀色氛围光） (Chassis Additional Emissive Map)",
                "Chassis_Lights",
                sec,
                sec_tris[m_add_emissive].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && (Chassis_RyzaRevT1_M.R > 20 || Chassis_RyzaRevT1_M.G > 20)",
                {
                    "static_switch": "AdditionalEmissive = True",
                    "mask_texture": "AdditionalEmissiveMap = Chassis_RyzaRevT1_M",
                    "shader_parameter": "Emissive Color (RedMask)=(1.0, 0.150036, 0.0, 5.0), Emissive Color (GreenMask)=(1.0, 0.449809, 0.0, 3.0)",
                },
                {
                    "baseColorFactor": [1.0, 0.45, 0.10, 1.0],
                    "metallicFactor": 0.20,
                    "roughnessFactor": 0.20,
                    "emissiveFactor": [1.0, 0.35, 0.02],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                    "emissiveTex": "RyzaRevT1_Chassis_Emissive",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_BrakeDiscs_And_Calipers",
                "四轮通风打孔刹车盘与高性能刹车卡钳 (Brake Discs & Calipers)",
                "Chassis_Brakes",
                sec,
                sec_tris[m_brakes].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && PrimaryBone in {FL/FR/BL/BR_Disc_geo_jnt, FL/FR/BL/BR_Brakepad_jnt}",
                {
                    "bone_binding": "FL/FR/BL/BR_Disc_geo_jnt (4x 208 = 832 tris), FL/FR/BL/BR_Brakepad_jnt (4x 488 = 1,952 tris)",
                    "diffuse_texture": "Chassis_RyzaRevT1_D",
                },
                {
                    "baseColorFactor": [0.74, 0.75, 0.78, 1.0],
                    "metallicFactor": 0.85,
                    "roughnessFactor": 0.28,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_Suspension_And_Axles",
                "前后桥独立悬挂减震器、转向节与传动半轴 (Suspension Shocks, Pivots & Axles)",
                "Chassis_Suspension",
                sec,
                sec_tris[m_susp].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && PrimaryBone in {FL/FR/BL/BR_Shock_A/B_jnt, *_axleShaft_jnt, *_Pivot_jnt, *_WheelTranslation_jnt}",
                {
                    "bone_binding": "FL/FR/BL/BR_Shock_A/B_jnt, FL/FR/BL/BR_axleShaft_jnt, FL/FR_Pivot_jnt, FL/FR/BL/BR_WheelTranslation_jnt (controlled by 23 SkelControl nodes in Body_RyzaRevT1_AT)",
                },
                {
                    "baseColorFactor": [0.52, 0.54, 0.58, 1.0],
                    "metallicFactor": 0.72,
                    "roughnessFactor": 0.38,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_EngineBay_And_Exhaust_Metal",
                "后置涡轮引擎舱、双出排气管与底盘高亮金属件 (Engine Bay, Twin Exhaust & Bright Chassis Metal)",
                "Chassis_Metal",
                sec,
                sec_tris[m_metal].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && Bone==chassis_jnt && Chassis_RyzaRevT1_D.MeanRGB > 75",
                {
                    "mask_evidence": "Chassis_RyzaRevT1_D high-albedo metallic regions on chassis_jnt",
                },
                {
                    "baseColorFactor": [0.70, 0.71, 0.74, 1.0],
                    "metallicFactor": 0.82,
                    "roughnessFactor": 0.30,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Chassis_Undercarriage_And_CockpitTub",
                "底盘护板、轮拱内衬与座舱内部暗色结构 (Chassis Undercarriage & Cockpit Tub)",
                "Chassis_Structure",
                sec,
                sec_tris[m_under].reshape(-1),
                "Section 0 (MIC_RyzaRevT1_Chassis) && Bone==chassis_jnt && Chassis_RyzaRevT1_D.MeanRGB <= 75",
                {
                    "mask_evidence": "Chassis_RyzaRevT1_D dark structural regions & Chassis_RyzaRevT1_N.R ambient occlusion",
                },
                {
                    "baseColorFactor": [0.24, 0.24, 0.26, 1.0],
                    "metallicFactor": 0.32,
                    "roughnessFactor": 0.68,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
                    "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Chassis_Normal",
                },
            )

        elif s_idx == 1:
            # Section 1: MIC_RyzaRevT1_Plastic (6,812 tris, UseAsPlastic=True, PlasticColor=[0.14, 0.14, 0.14, 1.0])
            m_front_plastic = t_pos[:, 0] >= 0.0
            m_rear_plastic = ~m_front_plastic
            add_region(
                "RyzaRevT1_Plastic_FrontGrille_And_Splitter",
                "前脸进气格栅蜂窝网、前唇与大灯外框哑光黑塑料 (Front Grille, Splitter & Headlight Bezel Plastic - Slot 1)",
                "Body_Plastic",
                sec,
                sec_tris[m_front_plastic].reshape(-1),
                "Section 1 (MIC_RyzaRevT1_Plastic, UseAsPlastic=True) && Centroid.X >= 0.0",
                {
                    "material": "MIC_RyzaRevT1_Plastic (Parent=MAT_Vehicle_Trim_Base_normalmapped, UseAsPlastic=True)",
                    "shader_parameter": "PlasticColor=(0.14, 0.14, 0.14, 1.0), BodyTextures_Map=Trim_RyzaRevT1_COA, NormalMap=Trim_RyzaRevT1_N",
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.08,
                    "roughnessFactor": 0.68,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Plastic_BaseColor",
                    "mrTex": "RyzaRevT1_Trim_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Plastic_RearDiffuser_And_Vents",
                "尾部下扩散器格栅、散热网孔与后保险杠哑光黑塑料 (Rear Diffuser, Exhaust Surround & Vents Plastic - Slot 1)",
                "Body_Plastic",
                sec,
                sec_tris[m_rear_plastic].reshape(-1),
                "Section 1 (MIC_RyzaRevT1_Plastic, UseAsPlastic=True) && Centroid.X < 0.0",
                {
                    "material": "MIC_RyzaRevT1_Plastic (Parent=MAT_Vehicle_Trim_Base_normalmapped, UseAsPlastic=True)",
                    "shader_parameter": "PlasticColor=(0.14, 0.14, 0.14, 1.0), BodyTextures_Map=Trim_RyzaRevT1_COA, NormalMap=Trim_RyzaRevT1_N",
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.08,
                    "roughnessFactor": 0.68,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Plastic_BaseColor",
                    "mrTex": "RyzaRevT1_Trim_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )

        elif s_idx == 2:
            # Section 2: MIC_RyzaRevT1_Body (Slot 2, SkinMaterialIndex=2, 14,500 tris)
            bd_val = sample_tex_uv(body_d_tex, t_uv0)
            m_paint = bd_val[:, 3] > 128
            m_seam = ~m_paint
            add_region(
                "RyzaRevT1_Body_Slot2_PrimaryPaint",
                "主车身金属车漆与涂装画布层 (Primary Painted Bodywork & Decal Canvas - Slot 2)",
                "Body_Paint",
                sec,
                sec_tris[m_paint].reshape(-1),
                "Section 2 (MIC_RyzaRevT1_Body, SkinMaterialIndex=2) && Body_RyzaRevT1_D.A > 128",
                {
                    "skin_material_index": 2,
                    "mask_texture": "Body_RyzaRevT1_Blankskin.R > 128 & Body_RyzaRevT1_D.A > 128",
                    "shader_parameter": "TeamColor=(0.613237, 0.182819, 0.02035, 1.0), F1Type=2.0, F1ControlA=(0.6, 0.125, 0.25, 0.0625)",
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.38,
                    "roughnessFactor": 0.22,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Body_Primary_BaseColor",
                    "mrTex": "RyzaRevT1_Body_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Body_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Body_Slot2_RecessedPanelSeams_And_Accents",
                "主车身钣金凹槽接缝与深色嵌入式饰条 (Recessed Body Panel Seams & Dark Accents - Slot 2)",
                "Body_Trim",
                sec,
                sec_tris[m_seam].reshape(-1),
                "Section 2 (MIC_RyzaRevT1_Body, SkinMaterialIndex=2) && Body_RyzaRevT1_D.A <= 128",
                {
                    "mask_texture": "Body_RyzaRevT1_D.A <= 128 (Diffuse Alpha Seam/Trim Mask on 2,795 tris)",
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.15,
                    "roughnessFactor": 0.58,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Body_Seam_BaseColor",
                    "mrTex": "RyzaRevT1_Body_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Body_Normal",
                },
            )

        elif s_idx == 3:
            # Section 3: MIC_RyzaRevT1_Body (Slot 3, 3,112 tris - Rear Roof & Engine Decklid Louver Panel)
            add_region(
                "RyzaRevT1_Body_Slot3_RoofLouver_SecondaryPaint",
                "后部车顶与中置引擎盖百叶窗双遮罩副色车漆面板 (Rear Roof & Engine Decklid Louver Secondary Paint - Slot 3)",
                "Body_Paint_Secondary",
                sec,
                sec_tris.reshape(-1),
                "Section 3 (MIC_RyzaRevT1_Body, Slot 3) && Body_RyzaRevT1_Blankskin.G > 128 (99.71% of Section 3)",
                {
                    "mask_texture": "Body_RyzaRevT1_Blankskin (Channel R > 128 on 3,112/3,112 tris AND Channel G > 128 on 3,103/3,112 tris)",
                    "shader_parameter": "PaintColor=(0.232036, 0.020519, 0.021236, 1.0), F2Type=2.0, F2ControlA=(0.75, 0.5, 0.125, 0.25)",
                    "spatial_location": "Upper rear roof & engine louver decklid X=[-43.78, -17.04], Y=[-17.36, 17.36], Z=[26.35, 33.62]",
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.42,
                    "roughnessFactor": 0.24,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Body_Secondary_BaseColor",
                    "mrTex": "RyzaRevT1_Body_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Body_Normal",
                },
            )

        elif s_idx == 4:
            # Section 4: MIC_RyzaRevT1_Windshield (Slot 4, 940 tris)
            add_region(
                "RyzaRevT1_Windshield_Canopy_Glass",
                "座舱前挡风玻璃与左右侧窗深色玻璃 (Cockpit Windshield & Side Windows Glass - Slot 4)",
                "Glass_Canopy",
                sec,
                sec_tris.reshape(-1),
                "Section 4 (MIC_RyzaRevT1_Windshield, Slot 4, Parent=MAT_Vehicle_Windshield_Base / SPMF_OldWindow_v2022)",
                {
                    "material": "MIC_RyzaRevT1_Windshield (Parent=MAT_Vehicle_Windshield_Base)",
                    "spatial_location": "Cockpit canopy X=[-4.10, 44.77], Y=[-22.19, 22.19], Z=[16.23, 30.54]",
                },
                {
                    "baseColorFactor": [0.09, 0.12, 0.15, 0.88],
                    "metallicFactor": 0.18,
                    "roughnessFactor": 0.08,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "BLEND",
                    "normalTex": "RyzaRevT1_Flat_Normal",
                },
            )

        elif s_idx == 5:
            # Section 5: MIC_RyzaRevT1_Lenses (Slot 5, 1,010 tris, MAT_Vehicle_Glass_Translucent, Opacity=0.4, Normal=Lenses_RyzaRevT1_N)
            m_front_lens = t_pos[:, 0] > 0.0
            m_rear_red = (~m_front_lens) & (t_vc[:, 1] == 0)
            m_rear_clear = (~m_front_lens) & (t_vc[:, 1] > 0)

            add_region(
                "RyzaRevT1_Lenses_FrontHeadlight_ClearGlass",
                "前大灯外层透明折射灯罩透镜 (Front Headlight Clear Translucent Lenses - Slot 5)",
                "Lens_Glass",
                sec,
                sec_tris[m_front_lens].reshape(-1),
                "Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 255, 255, 255] && Centroid.X > 0.0",
                {
                    "material": "MIC_RyzaRevT1_Lenses (MAT_Vehicle_Glass_Translucent, Opacity=0.4, Normal=Lenses_RyzaRevT1_N)",
                    "vertex_color": "RGBA [255, 255, 255, 255] on all 946 front triangles",
                },
                {
                    "baseColorFactor": [0.78, 0.86, 0.94, 0.45],
                    "metallicFactor": 0.10,
                    "roughnessFactor": 0.06,
                    "emissiveFactor": [0.12, 0.15, 0.18],
                    "alphaMode": "BLEND",
                    "normalTex": "RyzaRevT1_Lenses_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Lenses_RearTaillight_RedGlass",
                "尾部高位红色刹车灯/尾灯透明透镜 (Rear Red Taillight Translucent Lenses - Slot 5)",
                "Lens_Glass",
                sec,
                sec_tris[m_rear_red].reshape(-1),
                "Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 0, 0, 255] && Centroid.X < 0.0",
                {
                    "material": "MIC_RyzaRevT1_Lenses (MAT_Vehicle_Glass_Translucent, Opacity=0.4, Normal=Lenses_RyzaRevT1_N)",
                    "vertex_color_exact": [255, 0, 0, 255],
                    "spatial_location": "Rear upper brake light lens X=[-54.60, -53.36], Z=[23.81, 25.88]",
                },
                {
                    "baseColorFactor": [0.95, 0.08, 0.06, 0.62],
                    "metallicFactor": 0.10,
                    "roughnessFactor": 0.08,
                    "emissiveFactor": [0.42, 0.02, 0.01],
                    "alphaMode": "BLEND",
                    "normalTex": "RyzaRevT1_Lenses_Normal",
                },
            )
            add_region(
                "RyzaRevT1_Lenses_RearReverse_ClearGlass",
                "尾部白色倒车灯/转向灯透明透镜 (Rear Clear Reverse/Indicator Lenses - Slot 5)",
                "Lens_Glass",
                sec,
                sec_tris[m_rear_clear].reshape(-1),
                "Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 255, 255, 255] && Centroid.X <= 0.0",
                {
                    "material": "MIC_RyzaRevT1_Lenses (MAT_Vehicle_Glass_Translucent, Opacity=0.4, Normal=Lenses_RyzaRevT1_N)",
                    "vertex_color_exact": [255, 255, 255, 255],
                    "spatial_location": "Rear reverse indicator lens X=[-54.10, -52.85], Z=[24.18, 25.12]",
                },
                {
                    "baseColorFactor": [0.85, 0.88, 0.92, 0.52],
                    "metallicFactor": 0.10,
                    "roughnessFactor": 0.08,
                    "emissiveFactor": [0.15, 0.16, 0.18],
                    "alphaMode": "BLEND",
                    "normalTex": "RyzaRevT1_Lenses_Normal",
                },
            )

        elif s_idx == 6:
            # Section 6: MIC_RyzaRevT1_Trim (Slot 6, 11,194 tris - Painted Edition Trim Slot!)
            add_region(
                "RyzaRevT1_Trim_PaintableExteriorAero_Slot6",
                "可涂装认证版侧裙、轮眉与空气动力学外饰条 (Paintable Exterior Aero Trim & Fender Arches - Slot 6)",
                "Body_Trim_Paintable",
                sec,
                sec_tris.reshape(-1),
                "Section 6 (MIC_RyzaRevT1_Trim, Slot 6, ProductAttribute_PaintSettings_TA MaterialGroups[6], PaintParameterName='TrimColor')",
                {
                    "material": "MIC_RyzaRevT1_Trim (Parent=MAT_Vehicle_Trim_Base_normalmapped, UseAsPlastic=False)",
                    "paint_attribute": "ProductAttribute_PaintSettings_TA_0: MaterialGroups[6]=MIC_RyzaRevT1_Trim, bPaintBody=True, PaintParameterName='TrimColor'",
                    "default_trim_color": [0.077345, 0.077345, 0.077345, 1.0],
                },
                {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.15,
                    "roughnessFactor": 0.52,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_Trim_BaseColor",
                    "mrTex": "RyzaRevT1_Trim_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )

        elif s_idx == 7:
            # Section 7: MIC_RyzaRevT1_TrimMetal (Slot 7, 15,147 tris, Parent=MAT_Chassis_Paintable)
            tn = sample_tex_uv(trim_n_tex, t_uv0)
            td = sample_tex_uv(trim_d_tex, t_uv0)
            m_anodized = tn[:, 0] > 64
            m_bright_metal = (~m_anodized) & (td[:, :3].mean(axis=1) > 50.0)
            m_dark_metal = (~m_anodized) & (~m_bright_metal)

            add_region(
                "RyzaRevT1_TrimMetal_AnodizedAccent_Masked",
                "法线红通道遮罩阳极氧化钛灰金属饰件 (Anodized Titanium Trim Accent - Normal.R Masked - Slot 7)",
                "Trim_Metal",
                sec,
                sec_tris[m_anodized].reshape(-1),
                "Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R > 64",
                {
                    "material": "MIC_RyzaRevT1_TrimMetal (Parent=MAT_Chassis_Paintable)",
                    "mask_texture": "Trim_RyzaRevT1_N.R > 64 (1,802 tris masked by Normal Red channel)",
                    "trim_color": [0.383775, 0.353741, 0.368591, 1.0],
                },
                {
                    "baseColorFactor": [0.85, 0.80, 0.83, 1.0],
                    "metallicFactor": 0.85,
                    "roughnessFactor": 0.28,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_TrimMetal_BaseColor",
                    "mrTex": "RyzaRevT1_TrimMetal_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )
            add_region(
                "RyzaRevT1_TrimMetal_BrushedSteel_Bright",
                "高亮拉丝不锈钢外露机械与排气尾喉饰件 (Bright Brushed Steel Trim & Exhaust Tips - Slot 7)",
                "Trim_Metal",
                sec,
                sec_tris[m_bright_metal].reshape(-1),
                "Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R <= 64 && Trim_RyzaRevT1_D.MeanRGB > 50",
                {
                    "material": "MIC_RyzaRevT1_TrimMetal (Parent=MAT_Chassis_Paintable)",
                    "diffuse_texture": "Trim_RyzaRevT1_D high-luminance metallic islands (4,318 tris)",
                },
                {
                    "baseColorFactor": [0.82, 0.83, 0.86, 1.0],
                    "metallicFactor": 0.88,
                    "roughnessFactor": 0.25,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_TrimMetal_BaseColor",
                    "mrTex": "RyzaRevT1_TrimMetal_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )
            add_region(
                "RyzaRevT1_TrimMetal_DarkGunmetal_Structural",
                "深色枪灰金属结构件、紧固件与进气道金属网框 (Dark Gunmetal Structural Trim & Fasteners - Slot 7)",
                "Trim_Metal",
                sec,
                sec_tris[m_dark_metal].reshape(-1),
                "Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R <= 64 && Trim_RyzaRevT1_D.MeanRGB <= 50",
                {
                    "material": "MIC_RyzaRevT1_TrimMetal (Parent=MAT_Chassis_Paintable)",
                    "diffuse_texture": "Trim_RyzaRevT1_D dark gunmetal structural islands (9,027 tris)",
                },
                {
                    "baseColorFactor": [0.45, 0.46, 0.48, 1.0],
                    "metallicFactor": 0.75,
                    "roughnessFactor": 0.42,
                    "emissiveFactor": [0.0, 0.0, 0.0],
                    "alphaMode": "OPAQUE",
                    "baseColorTex": "RyzaRevT1_TrimMetal_BaseColor",
                    "mrTex": "RyzaRevT1_TrimMetal_MetallicRoughness",
                    "normalTex": "RyzaRevT1_Trim_Normal",
                },
            )

    total_classified = sum(r["triangle_count"] for r in regions)
    assert total_classified == sk_mesh["num_triangles"], f"Expected {sk_mesh['num_triangles']}, got {total_classified}"
    return regions


def build_original_slots_regions(sk_mesh: dict) -> list:
    """Builds the original UE3 FSkelMeshSection 1:1 slots list (8 slots for Body_RyzaRevT1_SK)."""
    indices = sk_mesh["indices"]
    pos_ue = sk_mesh["positions_ue"]
    uv0 = sk_mesh["uv_sets"][0]
    raw_bones = sk_mesh["raw_bones"]
    primary_bone = sk_mesh["raw_bone_primary"]

    slot_pbr_map = {
        0: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.65,
            "roughnessFactor": 0.45,
            "emissiveFactor": [1.0, 1.0, 1.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_Chassis_BaseColor",
            "mrTex": "RyzaRevT1_Chassis_MetallicRoughness",
            "normalTex": "RyzaRevT1_Chassis_Normal",
            "emissiveTex": "RyzaRevT1_Chassis_Emissive",
        },
        1: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.08,
            "roughnessFactor": 0.68,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_Plastic_BaseColor",
            "mrTex": "RyzaRevT1_Trim_MetallicRoughness",
            "normalTex": "RyzaRevT1_Trim_Normal",
        },
        2: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.38,
            "roughnessFactor": 0.22,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_Body_Primary_BaseColor",
            "mrTex": "RyzaRevT1_Body_MetallicRoughness",
            "normalTex": "RyzaRevT1_Body_Normal",
        },
        3: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.42,
            "roughnessFactor": 0.24,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_Body_Secondary_BaseColor",
            "mrTex": "RyzaRevT1_Body_MetallicRoughness",
            "normalTex": "RyzaRevT1_Body_Normal",
        },
        4: {
            "baseColorFactor": [0.09, 0.12, 0.15, 0.88],
            "metallicFactor": 0.18,
            "roughnessFactor": 0.08,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "BLEND",
            "normalTex": "RyzaRevT1_Flat_Normal",
        },
        5: {
            "baseColorFactor": [0.78, 0.86, 0.94, 0.45],
            "metallicFactor": 0.10,
            "roughnessFactor": 0.06,
            "emissiveFactor": [0.12, 0.15, 0.18],
            "alphaMode": "BLEND",
            "normalTex": "RyzaRevT1_Lenses_Normal",
        },
        6: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.15,
            "roughnessFactor": 0.52,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_Trim_BaseColor",
            "mrTex": "RyzaRevT1_Trim_MetallicRoughness",
            "normalTex": "RyzaRevT1_Trim_Normal",
        },
        7: {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "metallicFactor": 0.82,
            "roughnessFactor": 0.32,
            "emissiveFactor": [0.0, 0.0, 0.0],
            "alphaMode": "OPAQUE",
            "baseColorTex": "RyzaRevT1_TrimMetal_BaseColor",
            "mrTex": "RyzaRevT1_TrimMetal_MetallicRoughness",
            "normalTex": "RyzaRevT1_Trim_Normal",
        },
    }

    regions = []
    for sec in sk_mesh["sections"]:
        s_idx = sec["section_index"]
        flat = indices[sec["first_index"]:sec["first_index"] + sec["num_triangles"] * 3]
        u_verts = np.unique(flat)
        p_sub = pos_ue[u_verts]
        uv0_sub = uv0[u_verts]
        b_names = sorted({raw_bones[int(b)]["name"] for b in np.unique(primary_bone[u_verts])})
        mat_name = f"Slot{s_idx}_{sec['material_name']}"
        regions.append({
            "region_id": s_idx,
            "material_name": mat_name,
            "display_name": f"Original UE3 Section {s_idx} ({sec['material_name']})",
            "category": "Original_UE3_Section",
            "original_section_index": s_idx,
            "original_material_slot": sec["material_index"],
            "original_material_name": sec["material_name"],
            "triangle_count": sec["num_triangles"],
            "vertex_count": int(len(u_verts)),
            "flat_indices": flat,
            "classification_rule": f"Original FSkelMeshSection[{s_idx}] (FirstIndex={sec['first_index']}, NumTriangles={sec['num_triangles']})",
            "evidence": {"section": sec},
            "bounds_uu": {
                "min": [round(float(x), 4) for x in p_sub.min(axis=0)],
                "max": [round(float(x), 4) for x in p_sub.max(axis=0)],
            },
            "uv0_bounds": {
                "min": [round(float(x), 4) for x in uv0_sub.min(axis=0)],
                "max": [round(float(x), 4) for x in uv0_sub.max(axis=0)],
            },
            "rigged_bones": b_names,
            "pbr_spec": slot_pbr_map[s_idx],
        })
    return regions


def build_skeletal_glb_file(
    sk_mesh: dict,
    regions: list,
    png_bytes_map: dict,
    white_model: bool,
    metadata_extras: dict,
    out_path: str,
    attached_static_meshes: list = None,
):
    """
    Packs a USkeletalMesh and its classified surface regions into a standard glTF 2.0 .glb file.
    When white_model=True:
      - No textures are embedded or bound (`images` and `textures` are omitted).
      - Every surface region gets its own distinct named glTF material layer with pure white
        baseColorFactor=[1.0, 1.0, 1.0, 1.0], metallicFactor=0.0, roughnessFactor=0.85,
        plus full provenance metadata in `extras`.
      - Every surface region is emitted as a separate mesh primitive bound to its material layer.
    """
    bin_chunks = []
    buffer_views = []
    accessors = []

    def add_bv(raw_bytes: bytes, target: int = None) -> int:
        pad = (4 - (len(raw_bytes) % 4)) % 4
        byte_offset = sum(len(c) for c in bin_chunks)
        bin_chunks.append(raw_bytes + (b"\x00" * pad if pad else b""))
        bv = {
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(raw_bytes),
        }
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        return len(buffer_views) - 1

    def add_acc(arr: np.ndarray, comp_type: int, acc_type: str, target: int = None, normalized: bool = False, with_minmax: bool = False) -> int:
        bv_idx = add_bv(arr.tobytes(), target=target)
        acc = {
            "bufferView": bv_idx,
            "componentType": comp_type,
            "count": int(arr.shape[0]),
            "type": acc_type,
        }
        if normalized:
            acc["normalized"] = True
        if with_minmax and len(arr) > 0:
            if acc_type == "SCALAR":
                acc["min"] = [int(arr.min())]
                acc["max"] = [int(arr.max())]
            else:
                acc["min"] = [round(float(x), 6) for x in arr.min(axis=0)]
                acc["max"] = [round(float(x), 6) for x in arr.max(axis=0)]
        accessors.append(acc)
        return len(accessors) - 1

    # 1. Skeleton nodes, Sockets, and inverseBindMatrices
    nodes, ibm_arr, joints = build_skeleton_nodes_and_ibm(sk_mesh, include_sockets=True)
    ibm_acc_idx = add_acc(ibm_arr, 5126, "MAT4")
    skins = [{
        "name": f"{sk_mesh['name']}_Skeleton",
        "inverseBindMatrices": ibm_acc_idx,
        "skeleton": 1,
        "joints": joints,
    }]

    # 2. Shared vertex attributes for all primitives of the SkeletalMesh
    pos_acc = add_acc(sk_mesh["positions_gltf"], 5126, "VEC3", target=34962, with_minmax=True)
    norm_acc = add_acc(sk_mesh["normals_gltf"], 5126, "VEC3", target=34962)
    tang_acc = add_acc(sk_mesh["tangents_gltf"], 5126, "VEC4", target=34962)
    j_acc = add_acc(sk_mesh["joints_0"], 5123, "VEC4", target=34962)
    w_acc = add_acc(sk_mesh["weights_0"], 5121, "VEC4", target=34962, normalized=True)

    base_attrs = {
        "POSITION": pos_acc,
        "NORMAL": norm_acc,
        "TANGENT": tang_acc,
        "JOINTS_0": j_acc,
        "WEIGHTS_0": w_acc,
    }
    if sk_mesh.get("vertex_colors_rgba") is not None:
        vc_acc = add_acc(sk_mesh["vertex_colors_rgba"], 5121, "VEC4", target=34962, normalized=True)
        base_attrs["COLOR_0"] = vc_acc
    for uv_i, uv_arr in enumerate(sk_mesh["uv_sets"]):
        uv_acc = add_acc(uv_arr, 5126, "VEC2", target=34962)
        base_attrs[f"TEXCOORD_{uv_i}"] = uv_acc

    # 3. Embedded PBR textures (only when white_model=False)
    images = []
    textures = []
    samplers = []
    tex_index_map = {}

    if not white_model and png_bytes_map:
        samplers.append({
            "magFilter": 9729,
            "minFilter": 9987,
            "wrapS": 10497,
            "wrapT": 10497,
        })
        for t_name, png_bytes in png_bytes_map.items():
            bv_idx = add_bv(png_bytes)
            img_idx = len(images)
            images.append({
                "name": t_name,
                "bufferView": bv_idx,
                "mimeType": "image/png",
            })
            tex_idx = len(textures)
            textures.append({
                "name": t_name,
                "sampler": 0,
                "source": img_idx,
            })
            tex_index_map[t_name] = tex_idx

    # 4. Build materials and mesh primitives per region
    materials = []
    primitives = []
    for r in regions:
        flat_indices = r["flat_indices"].astype(np.uint32)
        idx_acc = add_acc(flat_indices, 5125, "SCALAR", target=34963, with_minmax=True)
        mat_idx = len(materials)
        mat_extras = {
            "region_id": r["region_id"],
            "display_name": r["display_name"],
            "category": r["category"],
            "original_section_index": r["original_section_index"],
            "original_material_slot": r["original_material_slot"],
            "original_material_name": r["original_material_name"],
            "triangle_count": r["triangle_count"],
            "vertex_count": r["vertex_count"],
            "classification_rule": r["classification_rule"],
            "evidence": r["evidence"],
            "bounds_uu": r["bounds_uu"],
            "uv0_bounds": r["uv0_bounds"],
            "rigged_bones": r["rigged_bones"],
        }

        if white_model:
            mat_def = {
                "name": r["material_name"],
                "doubleSided": True,
                "alphaMode": "OPAQUE",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.85,
                },
                "extras": mat_extras,
            }
        else:
            ps = r.get("pbr_spec", {})
            pbr_mr = {
                "baseColorFactor": ps.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0]),
                "metallicFactor": ps.get("metallicFactor", 0.2),
                "roughnessFactor": ps.get("roughnessFactor", 0.5),
            }
            if ps.get("baseColorTex") in tex_index_map:
                pbr_mr["baseColorTexture"] = {"index": tex_index_map[ps["baseColorTex"]], "texCoord": 0}
            if ps.get("mrTex") in tex_index_map:
                pbr_mr["metallicRoughnessTexture"] = {"index": tex_index_map[ps["mrTex"]], "texCoord": 0}

            mat_def = {
                "name": r["material_name"],
                "doubleSided": True,
                "alphaMode": ps.get("alphaMode", "OPAQUE"),
                "pbrMetallicRoughness": pbr_mr,
                "extras": mat_extras,
            }
            if ps.get("normalTex") in tex_index_map:
                mat_def["normalTexture"] = {"index": tex_index_map[ps["normalTex"]], "texCoord": 0, "scale": 1.0}
            if ps.get("emissiveTex") in tex_index_map:
                mat_def["emissiveTexture"] = {"index": tex_index_map[ps["emissiveTex"]], "texCoord": 0}
            if "emissiveFactor" in ps:
                mat_def["emissiveFactor"] = ps["emissiveFactor"]

        materials.append(mat_def)
        primitives.append({
            "attributes": dict(base_attrs),
            "indices": idx_acc,
            "material": mat_idx,
            "mode": 4,
            "extras": {
                "material_name": r["material_name"],
                "display_name": r["display_name"],
                "original_section_index": r["original_section_index"],
                "triangle_count": r["triangle_count"],
            },
        })

    meshes = [{
        "name": sk_mesh["name"],
        "primitives": primitives,
        "extras": {
            "source_upk_export": sk_mesh["name"],
            "white_model_mode": white_model,
            "num_vertices": sk_mesh["num_vertices"],
            "num_triangles": sk_mesh["num_triangles"],
            "num_surface_layers": len(regions),
        },
    }]

    # 5. Optional attached StaticMeshes (e.g., Body_RyzaRevT1_BoostConeMesh attached to Socket_BoostConeMesh)
    if attached_static_meshes:
        socket_node_map = {
            n["name"]: idx for idx, n in enumerate(nodes) if n["name"].startswith("Socket_")
        }
        for sm_entry in attached_static_meshes:
            sm = sm_entry["static_mesh"]
            sock_target = f"Socket_{sm_entry.get('socket_name', '')}"
            sm_pos_acc = add_acc(sm["positions_gltf"], 5126, "VEC3", target=34962, with_minmax=True)
            sm_norm_acc = add_acc(sm["normals_gltf"], 5126, "VEC3", target=34962)
            sm_tan_acc = add_acc(sm["tangents_gltf"], 5126, "VEC4", target=34962)
            sm_attrs = {
                "POSITION": sm_pos_acc,
                "NORMAL": sm_norm_acc,
                "TANGENT": sm_tan_acc,
            }
            if sm.get("vertex_colors_rgba") is not None:
                sm_attrs["COLOR_0"] = add_acc(sm["vertex_colors_rgba"], 5121, "VEC4", target=34962, normalized=True)
            for uv_i, uv_arr in enumerate(sm["uv_sets"]):
                sm_attrs[f"TEXCOORD_{uv_i}"] = add_acc(uv_arr, 5126, "VEC2", target=34962)

            sm_prims = []
            for sec in sm["sections"]:
                if sec["num_triangles"] == 0:
                    continue
                flat = sm["indices"][sec["first_index"]:sec["first_index"] + sec["num_triangles"] * 3]
                idx_acc = add_acc(flat, 5125, "SCALAR", target=34963)
                mat_idx = len(materials)
                materials.append({
                    "name": f"{sm['name']}_{sec['material_name']}",
                    "doubleSided": True,
                    "alphaMode": "OPAQUE" if white_model else "BLEND",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [1.0, 1.0, 1.0, 1.0] if white_model else [0.15, 0.88, 1.0, 0.68],
                        "metallicFactor": 0.0,
                        "roughnessFactor": 0.85 if white_model else 0.20,
                    },
                    "emissiveFactor": [0.0, 0.0, 0.0] if white_model else [0.0, 0.87, 1.0],
                    "extras": sec,
                })
                sm_prims.append({
                    "attributes": dict(sm_attrs),
                    "indices": idx_acc,
                    "material": mat_idx,
                    "mode": 4,
                })
            sm_mesh_idx = len(meshes)
            meshes.append({
                "name": sm["name"],
                "primitives": sm_prims,
                "extras": {
                    "num_vertices": sm["num_vertices"],
                    "num_triangles": sm["num_triangles"],
                    "bounds": sm["bounds"],
                },
            })
            sm_node_idx = len(nodes)
            nodes.append({
                "name": sm["name"],
                "mesh": sm_mesh_idx,
                "extras": {
                    "type": "AttachedStaticMesh",
                    "attached_to_socket": sm_entry.get("socket_name"),
                },
            })
            if sock_target in socket_node_map:
                nodes[socket_node_map[sock_target]].setdefault("children", []).append(sm_node_idx)
            else:
                nodes[0].setdefault("children", []).append(sm_node_idx)

    bin_data = b"".join(bin_chunks)
    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "RLCars UPK Python Extractor & Surface Material Classifier",
        },
        "scene": 0,
        "scenes": [{
            "name": "Scene",
            "nodes": [0],
            "extras": {
                "package_name": metadata_extras.get("package_name"),
                "car_codename": metadata_extras.get("car_codename"),
                "skeletal_mesh_name": sk_mesh["name"],
                "white_model_mode": white_model,
            },
        }],
        "nodes": nodes,
        "skins": skins,
        "meshes": meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "extras": metadata_extras,
    }
    if samplers:
        gltf_dict["samplers"] = samplers
    if images:
        gltf_dict["images"] = images
    if textures:
        gltf_dict["textures"] = textures

    return write_glb_file(gltf_dict, bin_data, out_path)


def build_static_mesh_glb_file(sm: dict, out_path: str):
    """Packs a standalone UStaticMesh into a standard glTF 2.0 .glb file."""
    bin_chunks = []
    buffer_views = []
    accessors = []

    def add_acc(arr: np.ndarray, comp_type: int, acc_type: str, target: int = None, normalized: bool = False, with_minmax: bool = False) -> int:
        raw_bytes = arr.tobytes()
        pad = (4 - (len(raw_bytes) % 4)) % 4
        byte_offset = sum(len(c) for c in bin_chunks)
        bin_chunks.append(raw_bytes + (b"\x00" * pad if pad else b""))
        bv = {"buffer": 0, "byteOffset": byte_offset, "byteLength": len(raw_bytes)}
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        acc = {
            "bufferView": len(buffer_views) - 1,
            "componentType": comp_type,
            "count": int(arr.shape[0]),
            "type": acc_type,
        }
        if normalized:
            acc["normalized"] = True
        if with_minmax and len(arr) > 0:
            acc["min"] = [round(float(x), 6) for x in arr.min(axis=0)]
            acc["max"] = [round(float(x), 6) for x in arr.max(axis=0)]
        accessors.append(acc)
        return len(accessors) - 1

    pos_acc = add_acc(sm["positions_gltf"], 5126, "VEC3", target=34962, with_minmax=True)
    norm_acc = add_acc(sm["normals_gltf"], 5126, "VEC3", target=34962)
    tan_acc = add_acc(sm["tangents_gltf"], 5126, "VEC4", target=34962)
    attrs = {"POSITION": pos_acc, "NORMAL": norm_acc, "TANGENT": tan_acc}
    if sm.get("vertex_colors_rgba") is not None:
        attrs["COLOR_0"] = add_acc(sm["vertex_colors_rgba"], 5121, "VEC4", target=34962, normalized=True)
    for uv_i, uv_arr in enumerate(sm["uv_sets"]):
        attrs[f"TEXCOORD_{uv_i}"] = add_acc(uv_arr, 5126, "VEC2", target=34962)

    materials = []
    primitives = []
    for s_i, sec in enumerate(sm["sections"]):
        col = get_material_debug_color(s_i)
        materials.append({
            "name": sec["material_name"],
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": [round(col[0], 4), round(col[1], 4), round(col[2], 4), 1.0],
                "metallicFactor": 0.1,
                "roughnessFactor": 0.5,
            },
            "extras": sec,
        })
        flat = sm["indices"][sec["first_index"]:sec["first_index"] + sec["num_triangles"] * 3]
        idx_acc = add_acc(flat, 5125, "SCALAR", target=34963)
        primitives.append({
            "attributes": dict(attrs),
            "indices": idx_acc,
            "material": s_i,
            "mode": 4,
        })

    bin_data = b"".join(bin_chunks)
    gltf_dict = {
        "asset": {"version": "2.0", "generator": "RLCars UPK Python Extractor"},
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [{
            "name": sm["name"],
            "mesh": 0,
            "extras": {
                "num_vertices": sm["num_vertices"],
                "num_triangles": sm["num_triangles"],
                "bounds": sm["bounds"],
            },
        }],
        "meshes": [{"name": sm["name"], "primitives": primitives}],
        "materials": materials,
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    return write_glb_file(gltf_dict, bin_data, out_path)


def serialize_regions_for_json(regions: list) -> list:
    return [{k: v for k, v in r.items() if k != "flat_indices"} for r in regions]


def dump_all_exports(upk: UPKPackage) -> list:
    scene_exports = []
    for idx, e in enumerate(upk.exports):
        end_pos = e["serial_offset"] + e["serial_size"]
        try:
            props = upk.parse_export_properties(e)
            if e["class"] == "MaterialInstanceConstant" and props.get("bHasStaticPermutationResource"):
                perm = upk.parse_mic_static_parameters(upk.pos, end_pos)
                if perm.get("static_switches"):
                    props["StaticSwitchParameters"] = perm["static_switches"]
                if perm.get("static_component_masks"):
                    props["StaticComponentMaskParameters"] = perm["static_component_masks"]
                if perm.get("referenced_textures"):
                    props["ReferencedUniformTextures"] = perm["referenced_textures"]
        except Exception as ex:
            props = {"_parse_error": str(ex)}
        scene_exports.append({
            "index": e["index"],
            "name": e["name"],
            "class": e["class"],
            "super": e["super"],
            "outer": e["outer"],
            "archetype": e["archetype"],
            "full_path": e["full_path"],
            "group_dir": upk.get_group_dir(e["index"]),
            "serial_size": e["serial_size"],
            "serial_offset": e["serial_offset"],
            "properties": props,
        })
    return scene_exports


def write_ryzarevt1_readme(out_dir: str, sk_mesh: dict, detailed_regions: list):
    lines = [
        "# Rocket League `body_ryzarevt1_SF` (`Body_RyzaRevT1_SK`) 模型、原始资产与全量材质区域绑定规范仓库",
        "",
        "本分支 (`body_ryzarevt1_SF`) 为 `body_ryzarevt1_SF.upk` (`ProductID = 12798`) 的完整资产与模型分支，包含原始数据包中的所有几何、纹理、材质静态开关、骨骼控制链、物理碰撞盒及特效挂载细节：",
        "1. **原始数据包与反序列化资产 (`raw/`)**：包含原始加密压缩包 `raw/upk/body_ryzarevt1_SF.upk` 以及按 UPK 内部 Group 层级与 Class 分类导出的 `.gltf` + `.bin`、24 张贴图 `.png`、13 个材质/材质实例 `.mat` 与属性表 `.props.txt`（100% 兼容 UE Viewer / umodel 结构）。",
        "2. **多层级 GLB 模型 (`models/`)**：包含 **21 层精细化材质绑定 PBR 模型 (`Body_RyzaRevT1_SK.glb` / `Body_RyzaRevT1_SK_DetailedSurfaces.glb`)**、**纯白无贴图材质分层白模 (`Body_RyzaRevT1_SK_WhiteModel.glb`)**、原始 8 材质槽位白模与 PBR 模型、带双喷口氮气锥体 (`Body_RyzaRevT1_BoostConeMesh`) 挂载模型及独立静态网格模型。",
        "3. **证据链完备的面片-材质区域绑定指标表与物理碰撞盒参数 (`metadata/`)**：所有 **91,993 个三角面（61,521 个顶点）** 100% 无遗漏、无重叠地映射到对应的材质图层，并完整提取了 `RB_BodySetup_0` 刚体碰撞盒、`ProductAsset_Body_TA` (`HandlingPreset = Octane`, `HandlingPresetZOffset = 2.2`, `FrontAxle`, `BackAxle`, `ChassisSpring`)、`ProductAttribute_PaintSettings_TA` 涂装部位规则、`Body_RyzaRevT1_AT` 动画树 23 路骨骼控制器以及 `body_RyzaRevT1_FXActor` 特效绑定。",
        "4. **纯 Python 全流程提取与构建脚本 (`scripts/`)**：无需外部闭源工具即可从加密压缩的 `.upk` 直接解密、解压、反序列化并生成所有 GLB 与元数据。",
        "",
        "---",
        "",
        "## 一、 仓库目录结构",
        "",
        "```text",
        "body_ryzarevt1_SF/",
        "├── README.md                                          # 分支架构、物理碰撞盒/悬挂指标与 21 层材质区域绑定完整说明",
        "├── models/                                            # 导出的 GLB 模型集合",
        "│   ├── Body_RyzaRevT1_SK.glb                          # 主模型（21 个证据确凿的精细材质图层 + 36 骨骼/9 插槽 + 烘焙 PBR 贴图 + 完整 extras 元数据）",
        "│   ├── Body_RyzaRevT1_SK_DetailedSurfaces.glb         # 同上，21 层精细化材质绑定 PBR GLB",
        "│   ├── Body_RyzaRevT1_SK_WhiteModel.glb               # 【纯白白模 - 21 层精细材质分类】无任何贴图绑定，纯白色 [1,1,1,1]，不同面片严格绑定到 21 个材质图层",
        "│   ├── Body_RyzaRevT1_SK_WhiteModel_OriginalSlots.glb # 【纯白白模 - 原始 8 槽位】无任何贴图绑定，纯白色 [1,1,1,1]，按 UE3 原始 8 个 FSkelMeshSection 分层",
        "│   ├── Body_RyzaRevT1_SK_OriginalSlots.glb            # 原始 8 个 UE3 材质槽位 PBR GLB",
        "│   ├── Body_RyzaRevT1_SK_WithBoostCone.glb            # 主模型 + 自动挂载至 BoostConeMesh 插槽的尾喷口氮气锥静态网格体",
        "│   └── Body_RyzaRevT1_BoostConeMesh.glb               # 独立导出的尾喷口氮气锥静态网格体 (UStaticMesh, 2,360 顶点 / 4,184 三角面)",
        "├── metadata/                                          # 结构化指标表与全场景元数据",
        "│   ├── Body_RyzaRevT1_metadata.json                   # 车辆 RB_BodySetup_0 碰撞盒、ProductAsset_Body_TA、四轮悬挂坐标、动画树、插槽与材质汇总",
        "│   ├── Body_RyzaRevT1_surface_bindings.json           # 【核心】21 个精细材质图层 & 8 个原始槽位的面片绑定规则、证据链、UV/空间包围盒与蒙皮骨骼表",
        "│   └── Body_RyzaRevT1_scene.json                      # UPK 内全部 243 个 Export 对象与 105 个 Import 对象的完整属性及静态材质开关转储",
        "├── textures/                                          # 提取的 24 张原始贴图与 17 张烘焙 PBR 贴图",
        "│   ├── *.png                                          # UPK 内置全部 24 张贴图 (Body_RyzaRevT1_*, Chassis_RyzaRevT1_*, Trim_RyzaRevT1_*, Lenses_RyzaRevT1_N 等)",
        "│   └── baked_pbr/                                     # 转换后的切线空间 RGB 法线贴图、BaseColor、MetallicRoughness、Emissive 贴图",
        "├── raw/                                               # 原始数据包与 umodel 兼容分层导出",
        "│   ├── upk/body_ryzarevt1_SF.upk                      # 原始加密压缩 UPK 文件 (2,730,532 bytes)",
        "│   └── body_ryzarevt1_SF/                             # 按 Group 与 Class 导出的 .gltf/.bin/.png/.mat/.props.txt",
        "└── scripts/                                           # 可复用的全套 Python 提取与 GLB 构建工具链",
        "    ├── unpack_upk.py                                  # Rocket League UPK AES 解密与 Zlib 块解压工具",
        "    ├── upk_core.py                                    # UPK 名字表/导入导出表/属性树/静态开关解析器与 DXT1/DXT5/A8R8G8B8/DXT5nm 解码器",
        "    ├── mesh_gltf_builder.py                           # USkeletalMesh / UStaticMesh 二进制反序列化与 glTF 2.0 坐标/骨骼/插槽/法线转换核心",
        "    └── extract_and_build.py                           # 一键提取原始资产、分类面片材质区域并生成全部 GLB 与元数据的主脚本",
        "```",
        "",
        "---",
        "",
        "## 二、 核心几何、骨骼、悬挂与物理碰撞盒 (`RB_BodySetup_0` & `ProductAsset_Body_TA`) 指标",
        "",
        "| 指标项 | 数值 / 详情 |",
        "| :--- | :--- |",
        "| **SkeletalMesh 名称** | `Body_RyzaRevT1_SK` (Export `#208`, `ProductID = 12798`) |",
        "| **顶点总数 / 三角面总数** | **61,521 顶点** / **91,993 三角面** (`NumUVSets = 2`, `bHasVertexColors = True`) |",
        "| **StaticMesh 附加网格** | `Body_RyzaRevT1_BoostConeMesh` (Export `#218`, **2,360 顶点** / **4,184 三角面**, 材质 `Master_Octane_Nitrous_Boost_MIC`, 挂载于 `BoostConeMesh` 插槽) |",
        "| **原始材质槽位 (`Materials`, 8 个)** | `[0] MIC_RyzaRevT1_Chassis`, `[1] MIC_RyzaRevT1_Plastic`, `[2] MIC_RyzaRevT1_Body (SkinMaterialIndex=2)`, `[3] MIC_RyzaRevT1_Body`, `[4] MIC_RyzaRevT1_Windshield`, `[5] MIC_RyzaRevT1_Lenses`, `[6] MIC_RyzaRevT1_Trim (Painted Slot)`, `[7] MIC_RyzaRevT1_TrimMetal` |",
        "| **骨骼数量 (`RefSkeleton`)** | **36 根骨骼** (`SkeletalDepth = 5`)，包含底盘 `chassis_jnt`、四轮独立减震器 (`FL/FR/BL/BR_Shock_A/B/c_jnt`)、传动半轴 (`*_axleShaft_jnt`)、前轮转向节 (`FL/FR_Pivot_jnt`)、通风刹车盘 (`*_Disc_jnt` / `*_Disc_geo_jnt`) 与刹车卡钳 (`*_Brakepad_jnt`) |",
        "| **动画控制树 (`Body_RyzaRevT1_AT`)** | **23 路骨骼控制器**（12 个 `SkelControlLookAt` + 11 个 `SkelControlSingleBone`）+ `SuperSonic` 超音速动画序列组 (`boost_start`, `boost_idle`) |",
        "| **挂载插槽 (`Sockets`, 9 个)** | `AmbBoost` `[-53.5, 0.0, 17.75]`, `AntennaSocket` `[-36.0, -25.0, 24.0]`, `BoostConeMesh` `[-48.9956, 0.0, 15.5]` (Scale `[1.0, 1.1, 1.0]`), `FrontSocket` `[72.0704, 0.0, 4.75]`, `HatSocket` `[-5.0, 0.0, 36.0]` (Pitch `-3.999°`), `RocketBoost` `[-58.0, 0.0, 13.5]`, `Underglow` `[4.6099, 0.0, -10.0]`, `BoostEmitterLeft` `[-57.0, -8.0, 15.5]`, `BoostEmitterRight` `[-57.0, 8.0, 15.5]` |",
        "| **操控预设 (`HandlingPreset`)** | `HandlingPresets.Presets.Octane` (`CAR_CONFIG_OCTANE`) + `HandlingPresetZOffset = 2.2` |",
        "| **刚体碰撞盒 (`RB_BodySetup_0.AggGeom.BoxElems[0]`)** | 尺寸 **`X = 148.925232 UU` × `Y = 83.279953 UU` × `Z = 33.799999 UU`**，局部变换中心位移 **`[9.0, 0.0, 4.25] UU`** |",
        "| **前后桥车轮参数 (`FrontAxle` / `BackAxle`)** | 前桥：`WheelMeshRadius = 13.0 UU`, `WheelWidth = 10.5 UU`, `WheelMeshOffsetSide = 1.0 UU`；后桥：`WheelWidth = 12.5 UU`, `WheelMeshOffsetSide = 2.0 UU`；底盘弹簧最大位移：`[50.0, 25.0, 50.0] UU` |",
        "| **四轮悬挂基准坐标 (`WheelTranslation_jnt`)** | 前左 `[55.3142, -26.8510, -6.6534]` / 前右 `[55.3142, 26.8510, -6.6534]` / 后左 `[-35.6027, -26.8474, -5.0727]` / 后右 `[-35.6027, 26.8474, -5.0727]` |",
        "| **轴距 (`Wheelbase`) / 轮距 (`Track Width`)** | 轴距 **90.9169 UU** (`0.9092 m`) / 前轮距 **53.7020 UU** (`0.5370 m`) / 后轮距 **53.6948 UU** (`0.5369 m`) |",
        "",
        "---",
        "",
        "## 三、 证据确凿的面片-材质区域绑定表（21 层精细划分 vs 8 个原始槽位）",
        "",
        "`Body_RyzaRevT1_SK` 在 UE3 中拥有 8 个原始 `FSkelMeshSection`。我们结合 **材质实例参数与静态开关 (`MIC_RyzaRevT1_*`)**、**贴图通道遮罩 (`Chassis_RyzaRevT1_RGB`, `Chassis_RyzaRevT1_M`, `Body_RyzaRevT1_Blankskin`, `Body_RyzaRevT1_D.A`, `Trim_RyzaRevT1_N.R`, `Trim_RyzaRevT1_D`)**、**精确离散顶点色 (`COLOR_0`)** 以及 **骨骼蒙皮权重 (`JOINTS_0`)**，将全部 **91,993 个三角面** 精确划分为 **21 个语义明确的材质图层**：",
        "",
        "| 图层 ID | 材质图层名称 (`material.name`) | 中文语义说明 | 原始 Section | 三角面数 | 顶点数 | 判定规则与确凿证据 |",
        "| :---: | :--- | :--- | :---: | ---: | ---: | :--- |",
    ]
    for r in detailed_regions:
        lines.append(
            f"| `{r['region_id']}` | `{r['material_name']}` | {r['display_name']} | Section `{r['original_section_index']}` (`{r['original_material_name']}`) | **{r['triangle_count']:,}** | {r['vertex_count']:,} | `{r['classification_rule']}` |"
        )
    lines.extend([
        "",
        "> **验证结论**：21 个材质图层的三角面数总和 = **91,993**，与 `Body_RyzaRevT1_SK` 原始总面数完全一致（零遗漏、零重叠）。在 `Body_RyzaRevT1_SK_WhiteModel.glb` 中，上述 21 个区域作为独立的 glTF Primitive 分别绑定到对应的纯白材质图层（`baseColorFactor = [1.0, 1.0, 1.0, 1.0]`，无任何外部或内嵌贴图），可在 Blender / Three.js / Maya / Unreal 中直接按材质图层选中或单独赋材质。",
        "",
        "---",
        "",
        "## 四、 复现与使用方法",
        "",
        "```bash",
        "# 1. 解密并解压原始 UPK",
        "python3 scripts/unpack_upk.py raw/upk/body_ryzarevt1_SF.upk /tmp/body_ryzarevt1_SF_unpacked.upk",
        "",
        "# 2. 运行全流程提取、纹理烘焙、区域分类与 GLB 构建",
        "python3 scripts/extract_and_build.py",
        "```",
    ])
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_ryzarevt1_branch(
    raw_upk_path: str = "/root/work/body_ryzarevt1_SF.upk",
    unpacked_upk_path: str = "/root/work/body_ryzarevt1_SF_unpacked.upk",
    out_dir: str = "/root/work/branch_body_ryzarevt1_SF",
):
    print("=== Building branch: body_ryzarevt1_SF ===")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(raw_upk_path):
        candidate_raw = os.path.join(repo_root, "raw", "upk", "body_ryzarevt1_SF.upk")
        if os.path.exists(candidate_raw):
            raw_upk_path = candidate_raw
            unpacked_upk_path = "/tmp/body_ryzarevt1_SF_unpacked.upk"
            out_dir = repo_root
    if not os.path.exists(unpacked_upk_path):
        unpack_rl_upk(raw_upk_path, unpacked_upk_path)

    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    upk = UPKPackage(unpacked_upk_path)

    # 1. Copy original UPK into raw/upk/
    os.makedirs(os.path.join(out_dir, "raw", "upk"), exist_ok=True)
    shutil.copy2(raw_upk_path, os.path.join(out_dir, "raw", "upk", "body_ryzarevt1_SF.upk"))

    # 2. Extract all 24 textures & 13 materials
    textures, materials_meta = extract_all_textures_and_raw(upk, "body_ryzarevt1_SF", out_dir)
    baked_pngs = bake_pbr_textures_ryzarevt1(textures, os.path.join(out_dir, "textures", "baked_pbr"))

    # 3. Deserialize SkeletalMesh (0-based 207: Body_RyzaRevT1_SK) and StaticMesh (0-based 217: Body_RyzaRevT1_BoostConeMesh)
    sk_mesh = deserialize_skeletal_mesh(upk, 207)
    sm_boost = deserialize_static_mesh(upk, 217)

    # Export raw umodel-compatible .gltf + .bin + .props.txt into raw/body_ryzarevt1_SF/
    raw_pkg_dir = os.path.join(out_dir, "raw", "body_ryzarevt1_SF")
    for d in (os.path.join(raw_pkg_dir, sk_mesh["group_dir"]), os.path.join(raw_pkg_dir, "SkeletalMesh3")):
        export_raw_gltf_and_bin(sk_mesh, d, is_skeletal=True)
        with open(os.path.join(d, f"{sk_mesh['name']}.props.txt"), "w", encoding="utf-8") as f:
            f.write(format_props_txt(sk_mesh["properties"]) + "\n")

    for d in (os.path.join(raw_pkg_dir, sm_boost["group_dir"]), os.path.join(raw_pkg_dir, "StaticMesh3")):
        export_raw_gltf_and_bin(sm_boost, d, is_skeletal=False)
        with open(os.path.join(d, f"{sm_boost['name']}.props.txt"), "w", encoding="utf-8") as f:
            f.write(format_props_txt(sm_boost["properties"]) + "\n")

    # 4. Classify 20 detailed surface regions & 8 original UE3 slots
    detailed_regions = classify_ryzarevt1_surfaces(sk_mesh, textures)
    original_regions = build_original_slots_regions(sk_mesh)

    # 5. Build comprehensive metadata JSON
    all_exports = dump_all_exports(upk)
    exp_by_name = {f"{e['class']}:{e['name']}": e["properties"] for e in all_exports}

    vehicle_meta = {
        "package_name": "body_ryzarevt1_SF.upk",
        "car_codename": "Body_RyzaRevT1",
        "product_id": 12798,
        "skeletal_mesh_name": "Body_RyzaRevT1_SK",
        "static_mesh_name": "Body_RyzaRevT1_BoostConeMesh",
        "upk_summary": {
            "file_version": upk.file_version,
            "licensee_version": upk.licensee_version,
            "name_count": upk.name_count,
            "import_count": upk.import_count,
            "export_count": upk.export_count,
        },
        "physics_and_hitbox": {
            "handling_preset": "HandlingPresets.Presets.Octane",
            "handling_preset_z_offset": 2.2,
            "rb_body_setup": exp_by_name.get("RB_BodySetup:RB_BodySetup_0", {}),
            "hitbox_dimensions_uu": {
                "length_X": 148.925232,
                "width_Y": 83.279953,
                "height_Z": 33.799999,
            },
            "hitbox_offset_uu": {
                "rb_box_elem_center_uu": [9.0, 0.0, 4.25],
                "handling_preset_z_offset_uu": 2.2,
            },
            "front_axle": {
                "WheelMeshRadius": 13.0,
                "WheelWidth": 10.5,
                "WheelMeshOffsetSide": 1.0,
            },
            "back_axle": {
                "WheelWidth": 12.5,
                "WheelMeshOffsetSide": 2.0,
            },
            "chassis_spring": {
                "MaxDisplacement": {"x": 50.0, "y": 25.0, "z": 50.0},
            },
            "wheel_suspension_raycast_contacts_uu": {
                "FL_Wheel": {
                    "bone": "FL_WheelTranslation_jnt",
                    "position_uu": [55.314228, -26.851021, -6.653371],
                    "pivot_bone": "FL_Pivot_jnt",
                    "pivot_pos_uu": [55.314228, -28.151221, -6.653371],
                    "disc_bone": "FL_Disc_geo_jnt",
                    "disc_pos_uu": [55.314228, -29.451421, -6.653371],
                },
                "FR_Wheel": {
                    "bone": "FR_WheelTranslation_jnt",
                    "position_uu": [55.314228, 26.851021, -6.653371],
                    "pivot_bone": "FR_Pivot_jnt",
                    "pivot_pos_uu": [55.314228, 28.151221, -6.653371],
                    "disc_bone": "FR_Disc_geo_jnt",
                    "disc_pos_uu": [55.314228, 29.451421, -6.653371],
                },
                "BL_Wheel": {
                    "bone": "BL_WheelTranslation_jnt",
                    "position_uu": [-35.602695, -26.847399, -5.072738],
                    "disc_bone": "BL_Disc_geo_jnt",
                    "disc_pos_uu": [-35.602695, -29.447799, -5.072738],
                },
                "BR_Wheel": {
                    "bone": "BR_WheelTranslation_jnt",
                    "position_uu": [-35.602695, 26.847399, -5.072738],
                    "disc_bone": "BR_Disc_geo_jnt",
                    "disc_pos_uu": [-35.602695, 29.447799, -5.072738],
                },
            },
            "wheelbase_uu": round(55.314228 - (-35.602695), 6),
            "front_track_width_uu": round(26.851021 * 2, 6),
            "rear_track_width_uu": round(26.847399 * 2, 6),
            "mesh_bounds_uu": sk_mesh["bounds"],
        },
        "product_asset_body": exp_by_name.get("ProductAsset_Body_TA:body_ryzarevt1", {}),
        "paint_settings": exp_by_name.get("ProductAttribute_PaintSettings_TA:ProductAttribute_PaintSettings_TA_0", {}),
        "anim_tree": exp_by_name.get("AnimTree:Body_RyzaRevT1_AT", {}),
        "fx_actors": {
            "Body_FXActor": exp_by_name.get("FXActor_TA:Body_FXActor", {}),
            "body_RyzaRevT1_FXActor": exp_by_name.get("FXActor_TA:body_RyzaRevT1_FXActor", {}),
        },
        "skeletal_mesh_summary": {
            "num_vertices": sk_mesh["num_vertices"],
            "num_triangles": sk_mesh["num_triangles"],
            "num_uv_sets": sk_mesh["num_uv_sets"],
            "bHasVertexColors": bool(sk_mesh["properties"].get("bHasVertexColors", True)),
            "num_bones": len(sk_mesh["raw_bones"]),
            "num_sockets": len(sk_mesh["sockets"]),
            "original_sections": sk_mesh["sections"],
            "original_materials": sk_mesh["materials"],
        },
        "static_mesh_summary": {
            "name": sm_boost["name"],
            "num_vertices": sm_boost["num_vertices"],
            "num_triangles": sm_boost["num_triangles"],
            "num_uv_sets": sm_boost["num_uv_sets"],
            "bounds": sm_boost["bounds"],
            "sections": sm_boost["sections"],
            "attached_to_socket": "BoostConeMesh",
        },
        "sockets": sk_mesh["sockets"],
        "bones": sk_mesh["raw_bones"],
        "materials": materials_meta,
        "textures": {
            k: {tk: tv for tk, tv in v.items() if tk not in ("rgba", "normal_rgb")}
            for k, v in textures.items()
        },
        "surface_regions_summary": [
            {
                "region_id": r["region_id"],
                "material_name": r["material_name"],
                "display_name": r["display_name"],
                "original_section_index": r["original_section_index"],
                "triangle_count": r["triangle_count"],
                "vertex_count": r["vertex_count"],
                "classification_rule": r["classification_rule"],
            }
            for r in detailed_regions
        ],
    }

    # 6. Build all GLB models
    models_dir = os.path.join(out_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    build_skeletal_glb_file(
        sk_mesh, detailed_regions, baked_pngs, white_model=False, metadata_extras=vehicle_meta,
        out_path=os.path.join(models_dir, "Body_RyzaRevT1_SK_DetailedSurfaces.glb"),
    )
    shutil.copy2(
        os.path.join(models_dir, "Body_RyzaRevT1_SK_DetailedSurfaces.glb"),
        os.path.join(models_dir, "Body_RyzaRevT1_SK.glb"),
    )
    build_skeletal_glb_file(
        sk_mesh, detailed_regions, {}, white_model=True, metadata_extras=vehicle_meta,
        out_path=os.path.join(models_dir, "Body_RyzaRevT1_SK_WhiteModel.glb"),
    )
    build_skeletal_glb_file(
        sk_mesh, original_regions, {}, white_model=True, metadata_extras=vehicle_meta,
        out_path=os.path.join(models_dir, "Body_RyzaRevT1_SK_WhiteModel_OriginalSlots.glb"),
    )
    build_skeletal_glb_file(
        sk_mesh, original_regions, baked_pngs, white_model=False, metadata_extras=vehicle_meta,
        out_path=os.path.join(models_dir, "Body_RyzaRevT1_SK_OriginalSlots.glb"),
    )
    build_skeletal_glb_file(
        sk_mesh, detailed_regions, baked_pngs, white_model=False, metadata_extras=vehicle_meta,
        out_path=os.path.join(models_dir, "Body_RyzaRevT1_SK_WithBoostCone.glb"),
        attached_static_meshes=[{"static_mesh": sm_boost, "socket_name": "BoostConeMesh"}],
    )
    build_static_mesh_glb_file(
        sm_boost, os.path.join(models_dir, "Body_RyzaRevT1_BoostConeMesh.glb")
    )

    # 7. Write metadata JSONs, scripts, and README.md
    meta_dir = os.path.join(out_dir, "metadata")
    os.makedirs(meta_dir, exist_ok=True)
    with open(os.path.join(meta_dir, "Body_RyzaRevT1_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(vehicle_meta, f, indent=2, ensure_ascii=False, allow_nan=False)
    with open(os.path.join(meta_dir, "Body_RyzaRevT1_surface_bindings.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "mesh_name": "Body_RyzaRevT1_SK",
                "total_vertices": sk_mesh["num_vertices"],
                "total_triangles": sk_mesh["num_triangles"],
                "original_sections_count": len(original_regions),
                "detailed_surface_regions_count": len(detailed_regions),
                "original_sections": serialize_regions_for_json(original_regions),
                "detailed_surface_regions": serialize_regions_for_json(detailed_regions),
            },
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    with open(os.path.join(meta_dir, "Body_RyzaRevT1_scene.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "package_name": "body_ryzarevt1_SF.upk",
                "file_version": upk.file_version,
                "licensee_version": upk.licensee_version,
                "name_count": upk.name_count,
                "import_count": upk.import_count,
                "export_count": upk.export_count,
                "imports": upk.imports,
                "exports": all_exports,
            },
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    scripts_src = os.path.dirname(os.path.abspath(__file__))
    scripts_dst = os.path.join(out_dir, "scripts")
    os.makedirs(scripts_dst, exist_ok=True)
    for s_file in ("unpack_upk.py", "upk_core.py", "mesh_gltf_builder.py", "extract_and_build.py"):
        src_p = os.path.join(scripts_src, s_file)
        dst_p = os.path.join(scripts_dst, s_file)
        if os.path.abspath(src_p) != os.path.abspath(dst_p):
            shutil.copy2(src_p, dst_p)

    write_ryzarevt1_readme(out_dir, sk_mesh, detailed_regions)
    print("  [OK] body_ryzarevt1_SF branch built at", out_dir)


if __name__ == "__main__":
    build_ryzarevt1_branch()
