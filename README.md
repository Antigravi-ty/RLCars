# Topple / Confidential_ThirdWheel_Test (body_topple_SF + Body_Topple_T_SF) — 完整表面材质分类 GLB 与物理/骨骼元数据 (`topple-tricycle`)

## 1. 导出模型列表 (`models/`)
| 模型文件 | 大小 |
|---|---|
| `models/Topple_DetailedMaterials.glb` | 4162.5 KB |
| `models/Topple_WhiteModel.glb` | 4138.5 KB |
| `models/Topple_SkeletalRigged.glb` | 5468.0 KB |
| `models/Topple_ThreeWheel_Variant.glb` | 4162.5 KB |

- **`*_DetailedMaterials.glb`**：保留并细分各个平面材质分类（车漆与涂装 `Body_PrimaryPaint`、挡风玻璃/车窗 `Windshield_Glass`、保险杠/塑料饰条/碳纤维 `Trim_Plastic / CarbonFiber`、底盘深色金属 `Chassis_DarkMetal`、排气管/悬挂镀铬 `Chassis_Chrome_Exhaust`、车头大灯与尾灯透镜 `Headlights_And_TailLenses`、氮气喷口 `BoostCone_Emissive`），烘培完整 PBR 贴图与法线贴图。
- **`*_WhiteModel.glb`**：保留全部表面分类子网格与法线贴图的纯净白模。
- **`*_SkeletalRigged.glb`**：保留完整 55 骨骼层级 (`JOINTS_0` / `WEIGHTS_0`) 与表面材质分类的骨骼绑定 GLB。
- **`*_ThreeWheel_Variant.glb`**：三蹦子（前轮居中）改装版 GLB。

## 2. 表面材质分类明细 (`glbSurfaceMaterialCategories`)
| 骨骼网格 | 表面材质分类 | GLB Material 名称 | 原始 UE3 材质 | 顶点数 | 三角面数 | Alpha 模式 |
|---|---|---|---|---|---|---|
| `Body_Topple_SK` | `Chassis_DarkMetal` | `Chassis_DarkMetal__MIC_Topple_Chassis` | `MIC_Topple_Chassis` | 19296 | 20298 | `OPAQUE` |
| `Body_Topple_SK` | `CarbonFiber_Trim` | `CarbonFiber_Trim__MIC_Topple_CarbonFiber` | `MIC_Topple_CarbonFiber` | 12906 | 20346 | `OPAQUE` |
| `Body_Topple_SK` | `Windshield_OpaqueVisor` | `Windshield_OpaqueVisor__MIC_Topple_Windshield` | `MIC_Topple_Windshield` | 587 | 676 | `OPAQUE` |
| `Body_Topple_SK` | `Headlights_And_TailLenses` | `Headlights_And_TailLenses__MIC_Topple_Lenses` | `MIC_Topple_Lenses` | 693 | 1024 | `OPAQUE` |
| `Body_Topple_SK` | `Trim_MattePlastic` | `Trim_MattePlastic__MIC_Topple_Plastic` | `MIC_Topple_Plastic` | 4346 | 6139 | `OPAQUE` |
| `Body_Topple_SK` | `Glass_Translucent_Canopy` | `Glass_Translucent_Canopy__MAT_Vehicle_Glass_Translucent` | `MAT_Vehicle_Glass_Translucent` | 219 | 260 | `BLEND` |
| `Body_Topple_SK` | `Body_PrimaryPaint` | `Body_PrimaryPaint__MIC_Topole_Body` | `MIC_Topole_Body` | 23901 | 41205 | `OPAQUE` |
| `Body_Topple_SK` | `BoostCone_Emissive` | `BoostCone_Nozzle__Body_Topple_BoostconeMesh` | `BoostCone_MAT` | 3031 | 1132 | `BLEND` |

## 3. 物理碰撞盒与悬挂参数 (`RocketSim` / `RB_BodySetup`)
- **预设映射**: `CAR_CONFIG_PSYCLOPS (Index 6, threeWheels = true)`
- **碰撞盒尺寸 (`hitboxSize` UU)**: `[118.495, 83.2725, 36.3]`
- **碰撞盒偏移 (`hitboxPosOffset` UU)**: `[13.88, 0.0, 20.75]`
- **前轮参数 (`frontWheels`)**: 半径 `12.5` UU, 悬挂静止长度 `33.0` UU, 挂载偏移 `[51.25, 5.0, 20.755]`
- **后轮参数 (`backWheels`)**: 半径 `13.5` UU, 悬挂静止长度 `31.3` UU, 挂载偏移 `[-33.75, 29.5, 20.755]`
- **三蹦子前轮偏移 (`threeWheelFrontOffset`)**: `[51.25, 5.0, 20.755]`

## 4. 元数据与原始资产目录
- `metadata/topple_tricycle_complete_metadata.json`: 完整提取的 `ProductAsset_Body_TA`、`RB_BodySetup`、所有 `SkeletalMeshSocket`（车轮/氮气/天线/帽子挂点坐标与旋转）、55 根骨骼层级、`AnimTree` 控制器与材质参数。
- `metadata/scene_dumps/`: 原始 `.upk` 全量对象属性转储 JSON。
- `textures/` & `textures/baked_pbr/`: 全部原始贴图与 PBR 合成贴图。
- `raw/`: `umodel` 导出的完整原始资产（`SkeletalMesh3`, `StaticMesh3`, `Texture2D`, `Material3`, `MaterialInstanceConstant`）。
