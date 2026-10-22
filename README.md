# Rocket League `body_tritip_SF` (Body_Tritip_SK / 三轮 Octane "Robin") 模型、原始资产与全量材质区域绑定规范仓库

本分支 (`body_tritip_SF`) 为 `body_tritip_SF.upk` 的标准化示范分支，完整包含：
1. **原始数据包与反序列化资产 (`raw/`)**：按 UPK 内部 Group 层级与 Class 分类导出的 `.gltf` + `.bin`、贴图 `.png`、材质 `.mat` 与属性表 `.props.txt`（100% 兼容 UE Viewer / umodel 结构）。
2. **多层级 GLB 模型 (`models/`)**：包含 11 层精细化材质绑定 PBR 模型、**纯白无贴图材质分层白模 (`Body_Tritip_SK_WhiteModel.glb`)**、原始 3 材质槽位白模与 PBR 模型、带尾喷口静态网格挂载模型。
3. **证据链完备的面片-材质区域绑定指标表与物理碰撞盒参数 (`metadata/`)**：所有 **22,151 个三角面（16,081 个顶点）** 100% 无遗漏、无重叠地映射到对应的材质图层，并完整提取了 `RB_BodySetup_1` 刚体碰撞盒、重心偏移、前后桥悬挂刚度与三轮物理架构参数。
4. **纯 Python 全流程提取与构建脚本 (`scripts/`)**：无需外部闭源工具即可从加密压缩的 `.upk` 直接解密、解压、反序列化并生成所有 GLB 与元数据。

---

## 一、 仓库目录结构

```text
body_tritip_SF/
├── README.md                                       # 分支架构、三轮物理碰撞盒指标与材质区域绑定完整说明
├── models/                                         # 导出的 GLB 模型集合
│   ├── Body_Tritip_SK.glb                          # 主模型（11 个证据确凿的精细材质图层 + 27 骨骼/9 插槽 + 烘焙 PBR 贴图 + 完整 extras 元数据）
│   ├── Body_Tritip_SK_DetailedSurfaces.glb         # 同上，11 层精细化材质绑定 PBR GLB
│   ├── Body_Tritip_SK_WhiteModel.glb               # 【纯白白模 - 11 层精细材质分类】无任何贴图绑定，纯白色 [1,1,1,1]，不同面片严格绑定到 11 个材质图层
│   ├── Body_Tritip_SK_WhiteModel_OriginalSlots.glb # 【纯白白模 - 原始 3 槽位】无任何贴图绑定，纯白色 [1,1,1,1]，按 UE3 原始 3 个 FSkelMeshSection 分层
│   ├── Body_Tritip_SK_OriginalSlots.glb            # 原始 3 个 UE3 材质槽位 PBR GLB
│   ├── Body_Tritip_SK_WithBoostMeshes.glb          # 主模型 + 自动挂载至 BoostEmitter_Left/Right 插槽的尾喷口网格体
│   ├── Octane_Boost.glb                            # 独立导出的尾喷口静态网格体 (Export #412)
│   ├── OctaneAmbientBoost_SM.glb                   # 独立导出的环境尾喷口静态网格体 (Export #413)
│   └── OctaneRibbons_SM.glb                        # 独立导出的尾流缎带静态网格体 (Export #414)
├── metadata/                                       # 结构化指标表与全场景元数据
│   ├── Body_Tritip_metadata.json                   # 车辆 RB_BodySetup 碰撞盒、HandlingPreset、VehicleSim、三轮骨骼坐标、插槽与材质汇总
│   ├── Body_Tritip_surface_bindings.json           # 【核心】11 个精细材质图层 & 3 个原始槽位的面片绑定规则、证据链、UV/空间包围盒与蒙皮骨骼表
│   └── Body_Tritip_scene.json                      # UPK 内全部 423 个 Export 对象的完整属性反序列化转储
├── textures/                                       # 提取的原始贴图与烘焙 PBR 贴图
│   ├── *.png                                       # UPK 内置贴图 (Tritip_BlankSkin, Tritip_Body_D, Body_Tritip_Curvature, Body_Octane_Bevel_RGB, Endo_Chassis_D/RGB 等)
│   ├── shared_dependencies/                        # 共享依赖贴图 (Endo_Chassis_N, Body_Octane_Bevel_N, T_Octane_BodyTextures)
│   └── baked_pbr/                                  # 转换后的切线空间 RGB 法线贴图、BaseColor、MetallicRoughness、Emissive 贴图
├── raw/                                            # 原始数据包与 umodel 兼容分层导出
│   ├── upk/body_tritip_SF.upk                      # 原始加密压缩 UPK 文件
│   └── body_tritip_SF/                             # 按 Group 与 Class 导出的 .gltf/.bin/.png/.mat/.props.txt
└── scripts/                                        # 可复用的全套 Python 提取与 GLB 构建工具链
    ├── unpack_upk.py                               # Rocket League UPK AES 解密与 Zlib 块解压工具
    ├── upk_core.py                                 # UPK 名字表/导入导出表/属性树解析器与 DXT1/DXT5/DXT5nm 解码器
    ├── mesh_gltf_builder.py                        # USkeletalMesh / UStaticMesh 二进制反序列化与 glTF 2.0 坐标/骨骼/法线转换核心
    └── extract_and_build.py                        # 一键提取原始资产、分类面片材质区域并生成全部 GLB 与元数据的主脚本
```

---

## 二、 核心几何、三轮骨骼架构与物理碰撞盒 (`RB_BodySetup`) 指标

| 指标项 | 数值 / 详情 |
| :--- | :--- |
| **SkeletalMesh 名称** | `Body_Tritip_SK` (Export `#398`，愚人节三轮 Octane / Robin 车型) |
| **顶点总数 / 三角面总数** | **16,081 顶点** / **22,151 三角面** |
| **UV 通道数 / 顶点色** | `NumUVSets = 2` (`TEXCOORD_0`, `TEXCOORD_1`) / `bHasVertexColors = True` (`COLOR_0`) |
| **三轮骨骼架构 (`RefSkeleton`, 27 根骨骼)** | 原生三轮骨骼绑定：前部仅设单轮总成 (`FL_WheelTranslation_jnt` 位于纵向中轴线 **`Y = 0.0`**，`[51.2535, 0.0, -3.5750]`，无任何 `FR_*` 骨骼)；后部设左右双轮 (`BL_WheelTranslation_jnt` `[ -33.7603, -32.5179, -2.0750 ]` 与 `BR_WheelTranslation_jnt` `[ -33.7603, 32.5179, -2.0750 ]`) |
| **挂载插槽 (`Sockets`, 9 个)** | `HatSocket`, `AntennaSocket`, `BoostEmitter_Left`, `BoostEmitter_Right`, `Headlight_Left`, `Headlight_Right`, `TailLight_Left`, `TailLight_Right`, `FocusPoint` |
| **刚体碰撞盒尺寸 (`RB_BodySetup_1.AggGeom.BoxElems[0]`)** | **`X = 118.007378 UU`** (长) × **`Y = 84.199409 UU`** (宽) × **`Z = 36.159073 UU`** (高) |
| **碰撞盒局部变换矩阵位移 (`BoxElem.TM`)** | `[13.87566, 0.0, 15.00499] UU`（叠加上 `HandlingPreset_Robin_TA` 偏移 `[0.0, 0.0, 5.75]` 后等效中心为 `[13.87566, 0.0, 20.75499] UU`） |
| **重心与操控预设 (`HandlingPreset_Robin_TA`)** | `CenterOfMassOffset = [0.0, 0.0, -7.25]`, `Offset = [0.0, 0.0, 5.75]` |
| **前后桥悬挂参数 (`FrontAxle` / `BackAxle`)** | 前桥：`WheelOffset = [51.5, 0.0, -0.5]`, `MaxSteerAngle = 30.0°`, `SpringStiffness = 22.0`, `RestLength = 15.8`；后桥：`WheelOffset = [-34.0, 27.5, 0.0]`, `SpringStiffness = 22.0`, `RestLength = 16.5` |

---

## 三、 证据确凿的面片-材质区域绑定表（11 层精细划分 vs 3 个原始槽位）

`Body_Tritip_SK` 在 UE3 中包含 3 个原始 `FSkelMeshSection`（`OctaneChassis_MIC`、`MIC_Body_Octane` 与三轮专属车头材质 `MIC_Body_Tritip`）。我们结合 **贴图通道遮罩 (`Endo_Chassis_RGB`, `Endo_Chassis_D`, `Body_Octane_Bevel_RGB`, `Tritip_BlankSkin`)**、**三轮骨骼蒙皮权重 (`JOINTS_0`)** 与 **几何法线/空间位置**，将全部 **22,151 个三角面** 精确划分为 **11 个语义明确的材质图层**：

| 图层 ID | 材质图层名称 (`material.name`) | 中文语义说明 | 原始 Section | 三角面数 | 顶点数 | 判定规则与确凿证据 |
| :---: | :--- | :--- | :---: | ---: | ---: | :--- |
| `0` | `Tritip_Chassis_Headlight_And_Taillight_Emissive` | 车头大灯发光体与尾灯/喷口发光组件 (Chassis Headlights & Taillights Emissive) | Section `0` (`OctaneChassis_MIC`) | **187** | 226 | `Section 0 (OctaneChassis_MIC) && (Endo_Chassis_RGB.R > 80 || G > 80 || B > 80)` |
| `1` | `Tritip_Chassis_FrontSingleWheel_Suspension` | 前部中置单轮转向叉、减震器与前轴总成 (Centerline Single Front Wheel Suspension) | Section `0` (`OctaneChassis_MIC`) | **81** | 65 | `Section 0 (OctaneChassis_MIC) && PrimaryBone in {FL_axleShaft_jnt, FL_Shock_c_jnt, FL_Pivot_jnt}` |
| `2` | `Tritip_Chassis_RearWheels_Suspension` | 后桥双轮独立悬挂减震器与传动半轴 (Rear Left/Right Suspension & Axles) | Section `0` (`OctaneChassis_MIC`) | **1,652** | 1,292 | `Section 0 (OctaneChassis_MIC) && PrimaryBone in {BL/BR_Shock_A/B/c_jnt, BL/BR_axleShaft_jnt, BL/BR_WheelTranslation_jnt}` |
| `3` | `Tritip_Chassis_ThreeWheel_BrakeDiscs_And_Calipers` | 三轮刹车盘与卡钳总成（前单轮 + 后双轮） (Three-Wheel Brake Discs & Calipers) | Section `0` (`OctaneChassis_MIC`) | **1,184** | 996 | `Section 0 (OctaneChassis_MIC) && PrimaryBone in {FL_Disc_geo_jnt, FL_Brakepad_jnt, BL_Disc_geo_jnt, BL_Brakepad_jnt, BR_Disc_geo_jnt, BR_Brakepad_jnt}` |
| `4` | `Tritip_Chassis_BrushedMetal_Engine_And_Exhaust` | 外露后置引擎缸体、排气管与防滚架金属件 (Exposed Engine Block & Exhaust Metal) | Section `0` (`OctaneChassis_MIC`) | **3,251** | 3,029 | `Section 0 (OctaneChassis_MIC) && Bone==chassis_jnt && Endo_Chassis_D.MeanRGB > 45` |
| `5` | `Tritip_Chassis_Frame_Undercarriage` | 钢管车架、底盘护板与散热器格栅 (Tubular Frame & Undercarriage) | Section `0` (`OctaneChassis_MIC`) | **5,720** | 5,282 | `Section 0 (OctaneChassis_MIC) && Bone==chassis_jnt && Endo_Chassis_D.MeanRGB <= 45` |
| `6` | `Tritip_OctaneBody_PrimaryPaint` | 主车壳与尾翼金属车漆涂装层 (Octane Main Body Primary Paint - Slot 1) | Section `1` (`MIC_Body_Octane`) | **4,839** | 3,524 | `Section 1 (MIC_Body_Octane) && Body_Octane_Bevel_RGB.A > 128 && Body_Octane_Bevel_RGB.B <= 128` |
| `7` | `Tritip_OctaneBody_Windshield_And_WindowVisor` | 座舱前挡风玻璃与侧窗深色玻璃面罩 (Cockpit Windshield & Side Window Visors - Slot 1) | Section `1` (`MIC_Body_Octane`) | **2,332** | 1,646 | `Section 1 (MIC_Body_Octane) && Body_Octane_Bevel_RGB.B > 128` |
| `8` | `Tritip_OctaneBody_Trim_BlackPlastic` | 车窗边框、侧进气口与深色塑料饰件 (Octane Body Black Plastic Trim - Slot 1) | Section `1` (`MIC_Body_Octane`) | **1,453** | 1,294 | `Section 1 (MIC_Body_Octane) && Body_Octane_Bevel_RGB.A <= 128 && Body_Octane_Bevel_RGB.B <= 128` |
| `9` | `Tritip_NoseCone_PrimaryPaint` | 三轮改装版前部收窄车头鼻锥与单轮整流罩车漆层 (Tritip Three-Wheel Nose Cone Primary Paint - Slot 2) | Section `2` (`MIC_Body_Tritip`) | **945** | 596 | `Section 2 (MIC_Body_Tritip, Slot 2) && Tritip_BlankSkin.R == 255 && Exterior Shell (Z >= -1.5 && Normal.Z >= -0.45)` |
| `10` | `Tritip_NoseCone_LowerTrim_And_WheelWell` | 三轮车头下部前唇与中央单轮轮拱内衬饰件 (Tritip Nose Cone Lower Trim & Single-Wheel Well - Slot 2) | Section `2` (`MIC_Body_Tritip`) | **507** | 368 | `Section 2 (MIC_Body_Tritip, Slot 2) && (Z < -1.5 || Normal.Z < -0.45) (TrimColor=[0.08, 0.08, 0.08])` |

> **验证结论**：11 个材质图层的三角面数总和 = **22,151**，与 `Body_Tritip_SK` 原始总面数完全一致（零遗漏、零重叠）。在 `Body_Tritip_SK_WhiteModel.glb` 中，上述 11 个区域作为独立的 glTF Primitive 分别绑定到对应的纯白材质图层（`baseColorFactor = [1.0, 1.0, 1.0, 1.0]`，无任何外部或内嵌贴图），方便在任何 3D 工具中直接查看或重赋予不同区域的材质。

---

## 四、 复现与使用方法

```bash
# 1. 解密并解压原始 UPK
python3 scripts/unpack_upk.py raw/upk/body_tritip_SF.upk /tmp/body_tritip_SF_unpacked.upk

# 2. 运行全流程提取、纹理烘焙、区域分类与 GLB 构建
python3 scripts/extract_and_build.py
```
