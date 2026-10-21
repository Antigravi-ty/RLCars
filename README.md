# BMW M4 GT3 EVO (Internal Codename: Topple) (`body-topple`)

本分支包含 **BMW M4 GT3 EVO (Internal Codename: Topple)** (`body_topple_SF, Body_Topple_T_SF`) 的完整 3D 骨骼模型（按平面材质分类拆分的 PBR GLB、原始材质槽位 GLB、白模 GLB）、车体物理参数（Hitbox 尺寸/偏移、前后桥悬挂与车轮参数、骨骼挂点 Socket）以及完整递归反序列化的 UPK 对象属性表。

---

## 1. 模型文件 (`models/`)

| 文件名 | 说明 |
|---|---|
| `models/Body_Topple.glb` / `models/Body_Topple_DetailedSurfaces.glb` | **细分平面材质 PBR 模型**：在保留 100% 原始顶点、UV、法线与骨骼蒙皮权重 (`JOINTS_0`, `WEIGHTS_0`) 的基础上，结合官方遮罩贴图 (`BlankSkin`、`FXMasks`、`Chassis_RGB`) 将车身与底盘的各个平面材质拆分为独立的命名 Primitive，并内嵌完整 PBR 贴图（BaseColor、法线、金属度/粗糙度、车灯自发光） |
| `models/Body_Topple_OriginalSlots.glb` | **原始 UE3 材质槽位 PBR 模型**：严格保留 UPK 内 `SkeletalMesh` 的原始材质 Section 划分与骨骼树 |
| `models/Body_Topple_WhiteModel.glb` | **高精度几何白模**：保留所有细分平面材质槽位名称与法线贴图，统一使用素模材质，便于检视拓朴与二次赋材质 |

### 细分平面材质分类表 (`Body_Topple_DetailedSurfaces.glb`)

| 材质槽位名称 (`material.name`) | 所属分类 | 三角面数 (Triangles) |
|---|---|---|
| `Body_Topple_Chassis_Undercarriage` | `Chassis` | 18,160 |
| `Body_Topple_Chassis_BrushedMetal` | `Chassis` | 979 |
| `Body_Topple_Chassis_Chrome_Accent` | `Chassis` | 67 |
| `Body_Topple_Chassis_Headlight_Emissive` | `Chassis` | 1,068 |
| `Body_Topple_Chassis_Taillight_BoostGlow` | `Chassis` | 24 |
| `MIC_Topple_CarbonFiber` | `DedicatedSlot` | 20,346 |
| `MIC_Topple_Windshield` | `DedicatedSlot` | 676 |
| `MIC_Topple_Lenses` | `DedicatedSlot` | 1,024 |
| `MIC_Topple_Plastic` | `DedicatedSlot` | 6,139 |
| `MAT_Vehicle_Glass_Translucent` | `DedicatedSlot` | 260 |
| `Body_Topple_Body_PrimaryPaint` | `Body` | 38,788 |
| `Body_Topple_Body_Windshield_Glass` | `Body` | 2,417 |

---

## 2. 物理与操控参数 (`metadata/Body_Topple_metadata.json`)

- **操控预设 (`HandlingPreset`)**: `MuscleCar` (`CAR_CONFIG_DOMINUS`)
- **Hitbox 尺寸 (Unreal Units / uu)**: `X = 127.9268, Y = 83.27995, Z = 31.3`
- **Hitbox 偏移 (Unreal Units / uu)**: `X = 9.0, Y = 0.0, Z = 15.75`
- **骨骼节点数量**: `44`

### 骨骼挂载点 (`SkeletalMeshSocket`)

| Socket 名称 | 绑定骨骼 (`BoneName`) | 相对坐标 (`RelativeLocation` in uu) |
|---|---|---|
| `AmbBoost` | `chassis_jnt` | `{'type': 'Vector', 'x': -70, 'y': 0, 'z': 6}` |
| `AntennaSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': -46, 'y': -25, 'z': 11}` |
| `BoostConeMesh` | `chassis_jnt` | `{'type': 'Vector', 'x': -67.0316, 'y': 0, 'z': 2.3}` |
| `FrontSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': 70, 'y': 0, 'z': 0}` |
| `HatSocket` | `chassis_jnt` | `{'type': 'Vector', 'x': -5, 'y': 0, 'z': 24.5}` |
| `RocketBoost` | `chassis_jnt` | `{'type': 'Vector', 'x': -67.5, 'y': 0, 'z': 4.5}` |
| `Underglow` | `chassis_jnt` | `{'type': 'Vector', 'x': 0, 'y': 0, 'z': -16}` |

---

## 3. 元数据与原始导出资源

- `metadata/Body_Topple_metadata.json`：整合了 `ProductAsset_Body_TA`、`RB_BodySetup`、前后轴 `VehicleAxleSettings`、`ChassisSpring`、`SkinParameters`、全部 `MaterialInstanceConstant` 参数与骨骼树。
- `metadata/*_scene.json`：UPK 全量导出表 (`ExportTable`) 与导入表 (`ImportTable`) 的递归属性反序列化 JSON。
- `raw/`：按 UPK Group 层级导出的原始 `.gltf`、`.bin`、`.png`、`.mat`、`.props.txt` 资源。
