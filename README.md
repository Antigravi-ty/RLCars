# Octane (Body_Octane_SF) — 完整表面材质分类 GLB 与物理/骨骼元数据 (`octane`)

## 1. 导出模型列表 (`models/`)
| 模型文件 | 大小 |
|---|---|
| `models/Octane_DetailedMaterials.glb` | 1458.6 KB |
| `models/Octane_WhiteModel.glb` | 1430.6 KB |
| `models/Octane_SkeletalRigged.glb` | 1920.5 KB |
| `models/Octane_ThreeWheel_Variant.glb` | 1458.6 KB |

- **`*_DetailedMaterials.glb`**：保留并细分各个平面材质分类（车漆与涂装 `Body_PrimaryPaint`、挡风玻璃/车窗 `Windshield_Glass`、保险杠/塑料饰条/碳纤维 `Trim_Plastic / CarbonFiber`、底盘深色金属 `Chassis_DarkMetal`、排气管/悬挂镀铬 `Chassis_Chrome_Exhaust`、车头大灯与尾灯透镜 `Headlights_And_TailLenses`、氮气喷口 `BoostCone_Emissive`），烘培完整 PBR 贴图与法线贴图。
- **`*_WhiteModel.glb`**：保留全部表面分类子网格与法线贴图的纯净白模。
- **`*_SkeletalRigged.glb`**：保留完整 55 骨骼层级 (`JOINTS_0` / `WEIGHTS_0`) 与表面材质分类的骨骼绑定 GLB。
- **`*_ThreeWheel_Variant.glb`**：三蹦子（前轮居中）改装版 GLB。

## 2. 表面材质分类明细 (`glbSurfaceMaterialCategories`)
| 骨骼网格 | 表面材质分类 | GLB Material 名称 | 原始 UE3 材质 | 顶点数 | 三角面数 | Alpha 模式 |
|---|---|---|---|---|---|---|
| `Body_Octane_PremiumSkin_SK` | `Chassis_DarkMetal_Undercarriage` | `Chassis_DarkMetal_Undercarriage__dummy_material_0` | `dummy_material_0` | 13065 | 16107 | `OPAQUE` |
| `Body_Octane_PremiumSkin_SK` | `Chassis_Chrome_Exhaust_Suspension` | `Chassis_Chrome_Exhaust_Suspension__dummy_material_0` | `dummy_material_0` | 71 | 53 | `OPAQUE` |
| `Body_Octane_PremiumSkin_SK` | `Body_PrimaryPaint_And_Decal` | `Body_PrimaryPaint_And_Decal__dummy_material_1` | `dummy_material_1` | 6666 | 10144 | `OPAQUE` |
| `Body_Octane_PremiumSkin_SK` | `Windshield_And_Windows_Glass` | `Windshield_And_Windows_Glass__dummy_material_1` | `dummy_material_1` | 441 | 538 | `BLEND` |
| `Body_Octane_PremiumSkin_SK` | `Trim_Bumper_Rollbar_Plastic` | `Trim_Bumper_Rollbar_Plastic__dummy_material_1` | `dummy_material_1` | 1470 | 1636 | `OPAQUE` |
| `Body_Octane_PremiumSkin_SK` | `BoostCone_Emissive` | `BoostCone_Nozzle__Octane_Boost` | `BoostCone_MAT` | 922 | 928 | `BLEND` |

## 3. 物理碰撞盒与悬挂参数 (`RocketSim` / `RB_BodySetup`)
- **预设映射**: `CAR_CONFIG_OCTANE (Index 0) / CAR_CONFIG_PSYCLOPS (Index 6)`
- **碰撞盒尺寸 (`hitboxSize` UU)**: `[118.0074, 84.19941, 36.15907]`
- **碰撞盒偏移 (`hitboxPosOffset` UU)**: `[13.87566, 0.0, 20.75499]`
- **前轮参数 (`frontWheels`)**: 半径 `12.5` UU, 悬挂静止长度 `38.755` UU, 挂载偏移 `[51.25, 25.9, 20.755]`
- **后轮参数 (`backWheels`)**: 半径 `13.5` UU, 悬挂静止长度 `37.055` UU, 挂载偏移 `[-33.75, 29.5, 20.755]`
- **三蹦子前轮偏移 (`threeWheelFrontOffset`)**: `[51.25, 5.0, 20.755]`

## 4. 元数据与原始资产目录
- `metadata/octane_complete_metadata.json`: 完整提取的 `ProductAsset_Body_TA`、`RB_BodySetup`、所有 `SkeletalMeshSocket`（车轮/氮气/天线/帽子挂点坐标与旋转）、55 根骨骼层级、`AnimTree` 控制器与材质参数。
- `metadata/scene_dumps/`: 原始 `.upk` 全量对象属性转储 JSON。
- `textures/` & `textures/baked_pbr/`: 全部原始贴图与 PBR 合成贴图。
- `raw/`: `umodel` 导出的完整原始资产（`SkeletalMesh3`, `StaticMesh3`, `Texture2D`, `Material3`, `MaterialInstanceConstant`）。
