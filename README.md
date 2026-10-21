# Merc / Vanquish (Body_Vanquish_SF) — 完整表面材质分类 GLB 与物理/骨骼元数据 (`merc-vanquish`)

## 1. 导出模型列表 (`models/`)
| 模型文件 | 大小 |
|---|---|
| `models/Merc_Vanquish_DetailedMaterials.glb` | 1231.0 KB |
| `models/Merc_Vanquish_WhiteModel.glb` | 1207.9 KB |
| `models/Merc_Vanquish_SkeletalRigged.glb` | 1619.1 KB |
| `models/Merc_Vanquish_ThreeWheel_Variant.glb` | 1231.0 KB |

- **`*_DetailedMaterials.glb`**：保留并细分各个平面材质分类（车漆与涂装 `Body_PrimaryPaint`、挡风玻璃/车窗 `Windshield_Glass`、保险杠/塑料饰条/碳纤维 `Trim_Plastic / CarbonFiber`、底盘深色金属 `Chassis_DarkMetal`、排气管/悬挂镀铬 `Chassis_Chrome_Exhaust`、车头大灯与尾灯透镜 `Headlights_And_TailLenses`、氮气喷口 `BoostCone_Emissive`），烘培完整 PBR 贴图与法线贴图。
- **`*_WhiteModel.glb`**：保留全部表面分类子网格与法线贴图的纯净白模。
- **`*_SkeletalRigged.glb`**：保留完整 55 骨骼层级 (`JOINTS_0` / `WEIGHTS_0`) 与表面材质分类的骨骼绑定 GLB。
- **`*_ThreeWheel_Variant.glb`**：三蹦子（前轮居中）改装版 GLB。

## 2. 表面材质分类明细 (`glbSurfaceMaterialCategories`)
| 骨骼网格 | 表面材质分类 | GLB Material 名称 | 原始 UE3 材质 | 顶点数 | 三角面数 | Alpha 模式 |
|---|---|---|---|---|---|---|
| `Body_Merc_PremiumSkin_SK` | `Chassis_DarkMetal_Undercarriage` | `Chassis_DarkMetal_Undercarriage__VanquishChassis_MIC` | `VanquishChassis_MIC` | 11927 | 16148 | `OPAQUE` |
| `Body_Merc_PremiumSkin_SK` | `Chassis_Chrome_Exhaust_Suspension` | `Chassis_Chrome_Exhaust_Suspension__VanquishChassis_MIC` | `VanquishChassis_MIC` | 236 | 230 | `OPAQUE` |
| `Body_Merc_PremiumSkin_SK` | `Body_PrimaryPaint_And_Decal` | `Body_PrimaryPaint_And_Decal__Body_Vanquish_MIC` | `Body_Vanquish_MIC` | 4262 | 5762 | `OPAQUE` |
| `Body_Merc_PremiumSkin_SK` | `Windshield_And_Windows_Glass` | `Windshield_And_Windows_Glass__Body_Vanquish_MIC` | `Body_Vanquish_MIC` | 1353 | 1437 | `BLEND` |
| `Body_Merc_PremiumSkin_SK` | `Trim_Bumper_Rollbar_Plastic` | `Trim_Bumper_Rollbar_Plastic__Body_Vanquish_MIC` | `Body_Vanquish_MIC` | 517 | 447 | `OPAQUE` |
| `Body_Merc_PremiumSkin_SK` | `BoostCone_Emissive` | `BoostCone_Nozzle__Vanquish_Boost` | `BoostCone_MAT` | 756 | 864 | `BLEND` |

## 3. 物理碰撞盒与悬挂参数 (`RocketSim` / `RB_BodySetup`)
- **预设映射**: `CAR_CONFIG_MERC (Index 5)`
- **碰撞盒尺寸 (`hitboxSize` UU)**: `[120.7202, 76.71031, 41.65999]`
- **碰撞盒偏移 (`hitboxPosOffset` UU)**: `[11.37566, 0.0, 21.50499]`
- **前轮参数 (`frontWheels`)**: 半径 `13.5` UU, 悬挂静止长度 `41.6` UU, 挂载偏移 `[50.0, 26.0, 21.505]`
- **后轮参数 (`backWheels`)**: 半径 `13.5` UU, 悬挂静止长度 `41.6` UU, 挂载偏移 `[-36.0, 26.0, 21.505]`
- **三蹦子前轮偏移 (`threeWheelFrontOffset`)**: `[50.0, 5.0, 21.505]`

## 4. 元数据与原始资产目录
- `metadata/merc_vanquish_complete_metadata.json`: 完整提取的 `ProductAsset_Body_TA`、`RB_BodySetup`、所有 `SkeletalMeshSocket`（车轮/氮气/天线/帽子挂点坐标与旋转）、55 根骨骼层级、`AnimTree` 控制器与材质参数。
- `metadata/scene_dumps/`: 原始 `.upk` 全量对象属性转储 JSON。
- `textures/` & `textures/baked_pbr/`: 全部原始贴图与 PBR 合成贴图。
- `raw/`: `umodel` 导出的完整原始资产（`SkeletalMesh3`, `StaticMesh3`, `Texture2D`, `Material3`, `MaterialInstanceConstant`）。
