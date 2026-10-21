# Merc (Internal Codename: Vanquish) (`body-merc`)

本分支包含 **Merc (Internal Codename: Vanquish)** (`Body_Vanquish_SF`) 的完整 3D 骨骼模型（按平面材质分类拆分的 PBR GLB、原始材质槽位 GLB、白模 GLB）、车体物理参数（Hitbox 尺寸/偏移、前后桥悬挂与车轮参数、骨骼挂点 Socket）以及完整递归反序列化的 UPK 对象属性表。

---

## 1. 模型文件 (`models/`)

| 文件名 | 说明 |
|---|---|
| `models/Body_Merc.glb` / `models/Body_Merc_DetailedSurfaces.glb` | **细分平面材质 PBR 模型**：在保留 100% 原始顶点、UV、法线与骨骼蒙皮权重 (`JOINTS_0`, `WEIGHTS_0`) 的基础上，结合官方遮罩贴图 (`BlankSkin`、`FXMasks`、`Chassis_RGB`) 将车身与底盘的各个平面材质拆分为独立的命名 Primitive，并内嵌完整 PBR 贴图（BaseColor、法线、金属度/粗糙度、车灯自发光） |
| `models/Body_Merc_OriginalSlots.glb` | **原始 UE3 材质槽位 PBR 模型**：严格保留 UPK 内 `SkeletalMesh` 的原始材质 Section 划分与骨骼树 |
| `models/Body_Merc_WhiteModel.glb` | **高精度几何白模**：保留所有细分平面材质槽位名称与法线贴图，统一使用素模材质，便于检视拓朴与二次赋材质 |

### 细分平面材质分类表 (`Body_Merc_DetailedSurfaces.glb`)

| 材质槽位名称 (`material.name`) | 所属分类 | 三角面数 (Triangles) |
|---|---|---|
| `Body_Merc_Chassis_Undercarriage` | `Chassis` | 6,375 |
| `Body_Merc_Chassis_BrushedMetal` | `Chassis` | 9,270 |
| `Body_Merc_Chassis_Chrome_Accent` | `Chassis` | 319 |
| `Body_Merc_Chassis_Headlight_Emissive` | `Chassis` | 204 |
| `Body_Merc_Chassis_Taillight_BoostGlow` | `Chassis` | 210 |
| `Body_Merc_Body_PrimaryPaint` | `Body` | 6,400 |
| `Body_Merc_Body_SecondaryTrim` | `Body` | 549 |
| `Body_Merc_Body_Windshield_Glass` | `Body` | 697 |

---

## 2. 物理与操控参数 (`metadata/Body_Merc_metadata.json`)

- **操控预设 (`HandlingPreset`)**: `Merc` (`CAR_CONFIG_MERC`)
- **Hitbox 尺寸 (Unreal Units / uu)**: `X = 120.7202, Y = 76.71031, Z = 41.65907`
- **Hitbox 偏移 (Unreal Units / uu)**: `X = 11.37566, Y = 0.0, Z = 21.50499`
- **骨骼节点数量**: `24`

### 骨骼挂载点 (`SkeletalMeshSocket`)

| Socket 名称 | 绑定骨骼 (`BoneName`) | 相对坐标 (`RelativeLocation` in uu) |
|---|---|---|
| `FrontSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 72.6239, 'y': 0, 'z': 1.25}` |
| `HatSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 13.0823, 'y': 0, 'z': 45}` |
| `BoostEmitterTop` | `chassis_jnt` | `{'type': 'Vector', 'x': -63, 'y': 0, 'z': 30.25}` |
| `BoostEmitterBottom` | `chassis_jnt` | `{'type': 'Vector', 'x': -63, 'y': 0, 'z': 13.75}` |
| `Underglow` | `root_jnt` | `{'x': 0, 'y': 0, 'z': 0}` |
| `AntennaSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 8.48368, 'y': -27.2721, 'z': 25}` |
| `AmbBoost_01` | `chassis_jnt` | `{'type': 'Vector', 'x': -61.3888, 'y': -17.4207, 'z': 43.5}` |
| `RocketBoost` | `chassis_jnt` | `{'type': 'Vector', 'x': -63.5723, 'y': 0, 'z': 21.75}` |
| `AmbBoost_02` | `chassis_jnt` | `{'type': 'Vector', 'x': -61.3376, 'y': -12.4894, 'z': 43.5}` |
| `AmbBoost_03` | `chassis_jnt` | `{'type': 'Vector', 'x': -61.3888, 'y': 12.4894, 'z': 43.5}` |
| `AmbBoost_04` | `chassis_jnt` | `{'type': 'Vector', 'x': -61.3888, 'y': 17.4207, 'z': 43.5}` |
| `AmbBoost_05` | `chassis_jnt` | `{'type': 'Vector', 'x': -65.0087, 'y': -11.4054, 'z': 22.25}` |
| `AmbBoost_06` | `chassis_jnt` | `{'type': 'Vector', 'x': -65.0087, 'y': 11.4054, 'z': 22.25}` |

---

## 3. 元数据与原始导出资源

- `metadata/Body_Merc_metadata.json`：整合了 `ProductAsset_Body_TA`、`RB_BodySetup`、前后轴 `VehicleAxleSettings`、`ChassisSpring`、`SkinParameters`、全部 `MaterialInstanceConstant` 参数与骨骼树。
- `metadata/*_scene.json`：UPK 全量导出表 (`ExportTable`) 与导入表 (`ImportTable`) 的递归属性反序列化 JSON。
- `raw/`：按 UPK Group 层级导出的原始 `.gltf`、`.bin`、`.png`、`.mat`、`.props.txt` 资源。
