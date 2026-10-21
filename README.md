# Dominus / MuscleCar (Body_MuscleCar_SF) — 完整表面材质分类 GLB 与物理/骨骼元数据 (`dominus-musclecar`)

## 1. 导出模型列表 (`models/`)
| 模型文件 | 大小 |
|---|---|
| `models/Dominus_MuscleCar_DetailedMaterials.glb` | 1546.5 KB |
| `models/Dominus_MuscleCar_WhiteModel.glb` | 1529.4 KB |
| `models/Dominus_MuscleCar_SkeletalRigged.glb` | 2004.9 KB |
| `models/Dominus_MuscleCar_ThreeWheel_Variant.glb` | 1546.5 KB |
| `models/Dominus_PremiumSkin_DetailedMaterials.glb` | 3094.1 KB |
| `models/Dominus_PremiumSkin_WhiteModel.glb` | 3071.2 KB |
| `models/Dominus_PremiumSkin_SkeletalRigged.glb` | 4321.9 KB |
| `models/Dominus_PremiumSkin_ThreeWheel_Variant.glb` | 3094.1 KB |

- **`*_DetailedMaterials.glb`**：保留并细分各个平面材质分类（车漆与涂装 `Body_PrimaryPaint`、挡风玻璃/车窗 `Windshield_Glass`、保险杠/塑料饰条/碳纤维 `Trim_Plastic / CarbonFiber`、底盘深色金属 `Chassis_DarkMetal`、排气管/悬挂镀铬 `Chassis_Chrome_Exhaust`、车头大灯与尾灯透镜 `Headlights_And_TailLenses`、氮气喷口 `BoostCone_Emissive`），烘培完整 PBR 贴图与法线贴图。
- **`*_WhiteModel.glb`**：保留全部表面分类子网格与法线贴图的纯净白模。
- **`*_SkeletalRigged.glb`**：保留完整 55 骨骼层级 (`JOINTS_0` / `WEIGHTS_0`) 与表面材质分类的骨骼绑定 GLB。
- **`*_ThreeWheel_Variant.glb`**：三蹦子（前轮居中）改装版 GLB。

## 2. 表面材质分类明细 (`glbSurfaceMaterialCategories`)
| 骨骼网格 | 表面材质分类 | GLB Material 名称 | 原始 UE3 材质 | 顶点数 | 三角面数 | Alpha 模式 |
|---|---|---|---|---|---|---|
| `Body_MuscleCar_SK` | `Body_PrimaryPaint` | `Body_PrimaryPaint__Body_MuscleCar_MIC` | `Body_MuscleCar_MIC` | 5558 | 8896 | `OPAQUE` |
| `Body_MuscleCar_SK` | `Trim_WindowSurround_Plastic` | `Trim_WindowSurround_Plastic__MIC_Vehicle_Trim_MuscleCar` | `MIC_Vehicle_Trim_MuscleCar` | 3996 | 6086 | `OPAQUE` |
| `Body_MuscleCar_SK` | `Chassis_DarkMetal` | `Chassis_DarkMetal__MuscleCar_Chassis_MIC` | `MuscleCar_Chassis_MIC` | 11911 | 14310 | `OPAQUE` |
| `Body_MuscleCar_SK` | `Chassis_Chrome_Exhaust_Engine` | `Chassis_Chrome_Exhaust_Engine__MuscleCar_Chassis_MIC` | `MuscleCar_Chassis_MIC` | 1051 | 1215 | `OPAQUE` |
| `Body_MuscleCar_SK` | `Windshield_Glass` | `Windshield_Glass__MIC_Vehicle_Windshield_MuscleCar` | `MIC_Vehicle_Windshield_MuscleCar` | 188 | 264 | `BLEND` |
| `Body_MuscleCar_SK` | `BoostCone_Emissive` | `BoostCone_Nozzle__MuscleCar_Boost` | `BoostCone_MAT` | 1470 | 984 | `BLEND` |
| `Body_Dominus_PremiumSkin_SK` | `Chassis_DarkMetal_Undercarriage` | `Chassis_DarkMetal_Undercarriage__Body_MuscleCar_MIC` | `Body_MuscleCar_MIC` | 11898 | 8779 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Chassis_Chrome_Exhaust_Suspension` | `Chassis_Chrome_Exhaust_Suspension__Body_MuscleCar_MIC` | `Body_MuscleCar_MIC` | 192 | 117 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Body_PrimaryPaint_And_Decal` | `Body_PrimaryPaint_And_Decal__MIC_Vehicle_Trim_MuscleCar` | `MIC_Vehicle_Trim_MuscleCar` | 8974 | 5169 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Windshield_And_Windows_Glass` | `Windshield_And_Windows_Glass__MIC_Vehicle_Trim_MuscleCar` | `MIC_Vehicle_Trim_MuscleCar` | 807 | 496 | `BLEND` |
| `Body_Dominus_PremiumSkin_SK` | `Trim_Bumper_Rollbar_Plastic` | `Trim_Bumper_Rollbar_Plastic__MIC_Vehicle_Trim_MuscleCar` | `MIC_Vehicle_Trim_MuscleCar` | 675 | 421 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Chassis_DarkMetal_Undercarriage` | `Chassis_DarkMetal_Undercarriage__MuscleCar_Chassis_MIC` | `MuscleCar_Chassis_MIC` | 30068 | 14306 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Chassis_Chrome_Exhaust_Suspension` | `Chassis_Chrome_Exhaust_Suspension__MuscleCar_Chassis_MIC` | `MuscleCar_Chassis_MIC` | 2439 | 1219 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Body_PrimaryPaint_And_Decal` | `Body_PrimaryPaint_And_Decal__MIC_Vehicle_Windshield_MuscleCar` | `MIC_Vehicle_Windshield_MuscleCar` | 360 | 208 | `OPAQUE` |
| `Body_Dominus_PremiumSkin_SK` | `Windshield_And_Windows_Glass` | `Windshield_And_Windows_Glass__MIC_Vehicle_Windshield_MuscleCar` | `MIC_Vehicle_Windshield_MuscleCar` | 72 | 56 | `BLEND` |
| `Body_Dominus_PremiumSkin_SK` | `BoostCone_Emissive` | `BoostCone_Nozzle__MuscleCar_Boost` | `BoostCone_MAT` | 1470 | 984 | `BLEND` |

## 3. 物理碰撞盒与悬挂参数 (`RocketSim` / `RB_BodySetup`)
- **预设映射**: `CAR_CONFIG_DOMINUS (Index 1)`
- **碰撞盒尺寸 (`hitboxSize` UU)**: `[127.9268, 83.27995, 31.3]`
- **碰撞盒偏移 (`hitboxPosOffset` UU)**: `[9.0, 0.0, 15.75]`
- **前轮参数 (`frontWheels`)**: 半径 `12.5` UU, 悬挂静止长度 `36.65` UU, 挂载偏移 `[55.0, 26.5, 15.75]`
- **后轮参数 (`backWheels`)**: 半径 `13.5` UU, 悬挂静止长度 `33.8` UU, 挂载偏移 `[-37.2, 33.0, 15.75]`
- **三蹦子前轮偏移 (`threeWheelFrontOffset`)**: `[55.0, 5.0, 15.75]`

## 4. 元数据与原始资产目录
- `metadata/dominus_musclecar_complete_metadata.json`: 完整提取的 `ProductAsset_Body_TA`、`RB_BodySetup`、所有 `SkeletalMeshSocket`（车轮/氮气/天线/帽子挂点坐标与旋转）、55 根骨骼层级、`AnimTree` 控制器与材质参数。
- `metadata/scene_dumps/`: 原始 `.upk` 全量对象属性转储 JSON。
- `textures/` & `textures/baked_pbr/`: 全部原始贴图与 PBR 合成贴图。
- `raw/`: `umodel` 导出的完整原始资产（`SkeletalMesh3`, `StaticMesh3`, `Texture2D`, `Material3`, `MaterialInstanceConstant`）。
