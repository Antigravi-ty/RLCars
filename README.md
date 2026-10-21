# RLCars — Rocket League 车辆多材质 GLB 模型与物理/骨骼元数据仓库

本仓库按要求为**每一个车辆模型建立独立的分支（Branch）**，每个分支均包含细分保留各个平面细节材质的 GLB 模型（车漆、挡风玻璃、塑料/碳纤维饰条、底盘金属、镀铬排气管/悬挂、车灯透镜、氮气喷口）、白模 GLB、55 骨骼绑定 GLB、三蹦子改装版 GLB，以及完整提取的物理碰撞盒、车轴悬挂、骨骼挂点（Sockets）与材质参数 JSON。

## 独立车辆分支一览

| 独立分支 (`branch`) | 车辆名称 | 源 UPK 文件 | RocketSim 预设 | 碰撞盒尺寸 `[X, Y, Z]` (UU) | 碰撞盒偏移 `[X, Y, Z]` (UU) |
|---|---|---|---|---|---|
| **`octane`** | Octane (Body_Octane_SF) | `Body_Octane_SF.upk` | `CAR_CONFIG_OCTANE (Index 0) / CAR_CONFIG_PSYCLOPS (Index 6)` | `[118.0074, 84.19941, 36.15907]` | `[13.87566, 0.0, 20.75499]` |
| **`dominus-musclecar`** | Dominus / MuscleCar (Body_MuscleCar_SF) | `Body_MuscleCar_SF.upk` | `CAR_CONFIG_DOMINUS (Index 1)` | `[127.9268, 83.27995, 31.3]` | `[9.0, 0.0, 15.75]` |
| **`breakout-force`** | Breakout / Force (Body_Force_SF) | `Body_Force_SF.upk` | `CAR_CONFIG_BREAKOUT (Index 3)` | `[131.4924, 80.521, 30.3]` | `[12.5, 0.0, 11.75]` |
| **`scarab`** | Scarab (Body_Scarab_SF) | `Body_Scarab_SF.upk` | `CAR_CONFIG_OCTANE (Index 0)` | `[118.0074, 84.19941, 36.15907]` | `[13.87566, 0.0, 20.75499]` |
| **`merc-vanquish`** | Merc / Vanquish (Body_Vanquish_SF) | `Body_Vanquish_SF.upk` | `CAR_CONFIG_MERC (Index 5)` | `[120.7202, 76.71031, 41.65999]` | `[11.37566, 0.0, 21.50499]` |
| **`topple-tricycle`** | Topple / Confidential_ThirdWheel_Test (body_topple_SF + Body_Topple_T_SF) | `body_topple_SF.upk` | `CAR_CONFIG_PSYCLOPS (Index 6, threeWheels = true)` | `[118.495, 83.2725, 36.3]` | `[13.88, 0.0, 20.75]` |

## `*_T_SF.upk` 与 `*_SF.upk` 的区别说明

在解包 `body_topple_SF.upk` 与 `Body_Topple_T_SF.upk` 时可以清晰看到两者的职责差异：

1. **`*_T_SF.upk`（其中 `_T` 代表 `Thumbnail` 缩略图包，例如 `Body_Topple_T_SF.upk`，仅 79 KB）**：
   - 仅包含 `ProductThumbnailAsset_TA` 对象以及一张 256×256 的 2D 物品栏预览缩略图 `Texture2D`（`Body_Topple_TThumbnail.png`），用于在车库/背包 UI 中快速加载图标，**不包含任何 3D 网格、骨骼或物理参数**。
2. **`*_SF.upk`（其中 `_SF` 代表 `Scaleform / Cooked Standalone SeekFree Package` 完整资产包，例如 `body_topple_SF.upk`，2.74 MB）**：
   - 包含完整的 3D 车辆骨骼网格 (`SkeletalMesh`：`Body_Topple_SK`)、静态附加网格 (`StaticMesh`：`Body_Topple_BoostconeMesh`)、物理碰撞盒资产 (`PhysicsAsset` / `RB_BodySetup`)、车辆配置与前后桥悬挂参数 (`ProductAsset_Body_TA`：`FrontAxle`, `BackAxle`, `ChassisSpring`)、动画控制树 (`AnimTree`：`CarWheelControl_TA`, `SkelControlSingleBone`, `SkelControlLookAt`)、特效配置 (`FXActor_Body_TA`) 以及全套高分辨率 PBR 贴图与材质实例 (`MaterialInstanceConstant`)。
