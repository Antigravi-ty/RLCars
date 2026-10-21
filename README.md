# RLCars — Rocket League 车辆模型、细分平面材质 GLB 与物理参数仓库

本仓库保存《Rocket League》各车辆的 3D 模型（保留各个平面细节材质分类的 PBR GLB、原始槽位 GLB、白模 GLB）、车体物理参数（Hitbox 尺寸/偏移、前后车轴 `VehicleAxleSettings`、悬挂弹簧 `ChassisSpring`、骨骼挂点 `SkeletalMeshSocket`）以及完整递归反序列化的 UPK 元数据。

**每一个车辆模型均保存在各自独立的分支 (`branch`) 中：**

| 分支名称 (`branch`) | 车辆名称 | 对应 UPK 包 | 物理操控预设 (`HandlingPreset`) | 细分材质面与三角面数 |
|---|---|---|---|---|
| `body-topple` | **BMW M4 GT3 EVO (Internal Codename: Topple)** | `body_topple_SF, Body_Topple_T_SF` | `MuscleCar` | 12 个细分材质面 (89,948 tris) |
| `body-octane` | **Octane (八角车 / 标准默认载具)** | `Body_Octane_SF` | `Octane` | 6 个细分材质面 (28,478 tris) |
| `body-dominus` | **Dominus (Internal Codename: MuscleCar)** | `Body_MuscleCar_SF` | `MuscleCar` | 10 个细分材质面 (30,771 tris) |
| `body-breakout` | **Breakout (Internal Codename: Force / LongCar)** | `Body_Force_SF` | `LongCar` | 7 个细分材质面 (27,438 tris) |
| `body-merc` | **Merc (Internal Codename: Vanquish)** | `Body_Vanquish_SF` | `Merc` | 8 个细分材质面 (24,024 tris) |
| `body-scarab` | **Scarab (圣甲虫)** | `Body_Scarab_SF` | `Octane` | 8 个细分材质面 (33,120 tris) |

---

## `_T_SF.upk` 与 `_SF.upk` 的区别（以 `Body_Topple_T_SF.upk` 与 `body_topple_SF.upk` 为例）

在《Rocket League》的 CookedPCConsole 资源包命名体系中：
1. **`_SF.upk`（例如 `body_topple_SF.upk`）**：
   - 后缀 `_SF` 代表 **SeekFree / Scaleform 完整资产包**。
   - 包含该车体在对局与车库 3D 渲染中所需的**全部核心 3D 与物理资产**：高精度骨骼网格 (`SkeletalMesh3'Body_Topple_SK'`)、氮气喷口静态网格 (`StaticMesh3'Body_Topple_BoostconeMesh'`)、动画树 (`AnimTree'Body_AT'`)、物理碰撞体 (`PhysicsAsset'body_Topple_physics'`)、粒子特效 (`FXActor_TA`)、材质实例 (`MaterialInstanceConstant`)、法线/漫反射/曲率/遮罩贴图以及核心车辆属性资产 (`ProductAsset_Body_TA`)。
2. **`_T_SF.upk`（例如 `Body_Topple_T_SF.upk`）**：
   - 中间的 `_T` 代表 **Thumbnail（车库 UI 缩略图包）**。
   - 这是一个极度轻量化的独立包（例如 `Body_Topple_T_SF.upk` 仅 42 KB，仅含 5 个导出项），里面**只存放一张 256×256 的 2D 车库列表预览图** (`Texture2D'Body_Topple_T.Body_Topple_TThumbnail'`)。
   - **设计目的**：当玩家打开车库浏览上百辆车身列表时，游戏引擎只需异步加载几십 KB 的 `*_T_SF.upk` 即可瞬间渲染出所有车辆的 2D 图标，而无需把几十 MB 的 3D 网格和贴图 (`*_SF.upk`) 全部载入内存；只有当玩家真正选中某辆车时，才会按需加载对应的 `*_SF.upk`。

---

## 汇总元数据

- `metadata/vehicles_summary.json`：包含全部 6 款车型的分支索引、RocketSim 物理预设参数对比（包括三轮车 `CAR_CONFIG_PSYCLOPS` 变体）、骨骼与 Socket 统计以及细分材质面统计。
