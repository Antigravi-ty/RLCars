# Scarab (圣甲虫) (`body-scarab`)

本分支包含 **Scarab (圣甲虫)** (`Body_Scarab_SF`) 的完整 3D 骨骼模型（按平面材质分类拆分的 PBR GLB、原始材质槽位 GLB、白模 GLB）、车体物理参数（Hitbox 尺寸/偏移、前后桥悬挂与车轮参数、骨骼挂点 Socket）以及完整递归反序列化的 UPK 对象属性表。

---

## 1. 模型文件 (`models/`)

| 文件名 | 说明 |
|---|---|
| `models/Body_Scarab.glb` / `models/Body_Scarab_DetailedSurfaces.glb` | **细分平面材质 PBR 模型**：在保留 100% 原始顶点、UV、法线与骨骼蒙皮权重 (`JOINTS_0`, `WEIGHTS_0`) 的基础上，结合官方遮罩贴图 (`BlankSkin`、`FXMasks`、`Chassis_RGB`) 将车身与底盘的各个平面材质拆分为独立的命名 Primitive，并内嵌完整 PBR 贴图（BaseColor、法线、金属度/粗糙度、车灯自发光） |
| `models/Body_Scarab_OriginalSlots.glb` | **原始 UE3 材质槽位 PBR 模型**：严格保留 UPK 内 `SkeletalMesh` 的原始材质 Section 划分与骨骼树 |
| `models/Body_Scarab_WhiteModel.glb` | **高精度几何白模**：保留所有细分平面材质槽位名称与法线贴图，统一使用素模材质，便于检视拓朴与二次赋材质 |

### 细分平面材质分类表 (`Body_Scarab_DetailedSurfaces.glb`)

| 材质槽位名称 (`material.name`) | 所属分类 | 三角面数 (Triangles) |
|---|---|---|
| `Body_Scarab_Chassis_Undercarriage` | `Chassis` | 6,859 |
| `Body_Scarab_Chassis_BrushedMetal` | `Chassis` | 12,401 |
| `Body_Scarab_Chassis_Chrome_Accent` | `Chassis` | 90 |
| `Body_Scarab_Chassis_Headlight_Emissive` | `Chassis` | 26 |
| `Body_Scarab_Chassis_Taillight_BoostGlow` | `Chassis` | 12 |
| `Body_Scarab_Body_PrimaryPaint` | `Body` | 5,805 |
| `Body_Scarab_Body_SecondaryTrim` | `Body` | 4,043 |
| `Body_Scarab_Body_Windshield_Glass` | `Body` | 3,884 |

---

## 2. 物理与操控参数 (`metadata/Body_Scarab_metadata.json`)

- **操控预设 (`HandlingPreset`)**: `Octane` (`CAR_CONFIG_OCTANE`)
- **Hitbox 尺寸 (Unreal Units / uu)**: `X = 118.0074, Y = 84.19941, Z = 36.15907`
- **Hitbox 偏移 (Unreal Units / uu)**: `X = 13.87566, Y = 0.0, Z = 20.75499`
- **骨骼节点数量**: `40`

### 骨骼挂载点 (`SkeletalMeshSocket`)

| Socket 名称 | 绑定骨骼 (`BoneName`) | 相对坐标 (`RelativeLocation` in uu) |
|---|---|---|
| `AmbientBoost` | `chassis_jnt` | `{'type': 'Vector', 'x': 3.66432, 'y': 0, 'z': 44.45}` |
| `Underglow` | `root_jnt` | `{'x': 0, 'y': 0, 'z': 0}` |
| `RocketBoost` | `chassis_jnt` | `{'type': 'Vector', 'x': -48.5, 'y': 0, 'z': 11.7}` |
| `HatSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 3.66432, 'y': 0, 'z': 43.7}` |
| `AntennaSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': -14, 'y': -24.1209, 'z': 25.5}` |
| `FrontSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 47.8365, 'y': 0, 'z': 0}` |
| `HoodSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 45.7825, 'y': 0, 'z': 9.84168}` |

---

## 3. 元数据与原始导出资源

- `metadata/Body_Scarab_metadata.json`：整合了 `ProductAsset_Body_TA`、`RB_BodySetup`、前后轴 `VehicleAxleSettings`、`ChassisSpring`、`SkinParameters`、全部 `MaterialInstanceConstant` 参数与骨骼树。
- `metadata/*_scene.json`：UPK 全量导出表 (`ExportTable`) 与导入表 (`ImportTable`) 的递归属性反序列化 JSON。
- `raw/`：按 UPK Group 层级导出的原始 `.gltf`、`.bin`、`.png`、`.mat`、`.props.txt` 资源。
