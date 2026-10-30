# Rocket League `body_ryzarevt1_SF` (`Body_RyzaRevT1_SK`) 模型、原始资产与全量材质区域绑定规范仓库

本分支 (`body_ryzarevt1_SF`) 为 `body_ryzarevt1_SF.upk` (`ProductID = 12798`) 的完整资产与模型分支，包含原始数据包中的所有几何、纹理、材质静态开关、骨骼控制链、物理碰撞盒及特效挂载细节：
1. **原始数据包与反序列化资产 (`raw/`)**：包含原始加密压缩包 `raw/upk/body_ryzarevt1_SF.upk` 以及按 UPK 内部 Group 层级与 Class 分类导出的 `.gltf` + `.bin`、24 张贴图 `.png`、13 个材质/材质实例 `.mat` 与属性表 `.props.txt`（100% 兼容 UE Viewer / umodel 结构）。
2. **多层级 GLB 模型 (`models/`)**：包含 **21 层精细化材质绑定 PBR 模型 (`Body_RyzaRevT1_SK.glb` / `Body_RyzaRevT1_SK_DetailedSurfaces.glb`)**、**纯白无贴图材质分层白模 (`Body_RyzaRevT1_SK_WhiteModel.glb`)**、原始 8 材质槽位白模与 PBR 模型、带双喷口氮气锥体 (`Body_RyzaRevT1_BoostConeMesh`) 挂载模型及独立静态网格模型。
3. **证据链完备的面片-材质区域绑定指标表与物理碰撞盒参数 (`metadata/`)**：所有 **91,993 个三角面（61,521 个顶点）** 100% 无遗漏、无重叠地映射到对应的材质图层，并完整提取了 `RB_BodySetup_0` 刚体碰撞盒、`ProductAsset_Body_TA` (`HandlingPreset = Octane`, `HandlingPresetZOffset = 2.2`, `FrontAxle`, `BackAxle`, `ChassisSpring`)、`ProductAttribute_PaintSettings_TA` 涂装部位规则、`Body_RyzaRevT1_AT` 动画树 23 路骨骼控制器以及 `body_RyzaRevT1_FXActor` 特效绑定。
4. **纯 Python 全流程提取与构建脚本 (`scripts/`)**：无需外部闭源工具即可从加密压缩的 `.upk` 直接解密、解压、反序列化并生成所有 GLB 与元数据。

---

## 一、 仓库目录结构

```text
body_ryzarevt1_SF/
├── README.md                                          # 分支架构、物理碰撞盒/悬挂指标与 21 层材质区域绑定完整说明
├── models/                                            # 导出的 GLB 模型集合
│   ├── Body_RyzaRevT1_SK.glb                          # 主模型（21 个证据确凿的精细材质图层 + 36 骨骼/9 插槽 + 烘焙 PBR 贴图 + 完整 extras 元数据）
│   ├── Body_RyzaRevT1_SK_DetailedSurfaces.glb         # 同上，21 层精细化材质绑定 PBR GLB
│   ├── Body_RyzaRevT1_SK_WhiteModel.glb               # 【纯白白模 - 21 层精细材质分类】无任何贴图绑定，纯白色 [1,1,1,1]，不同面片严格绑定到 21 个材质图层
│   ├── Body_RyzaRevT1_SK_WhiteModel_OriginalSlots.glb # 【纯白白模 - 原始 8 槽位】无任何贴图绑定，纯白色 [1,1,1,1]，按 UE3 原始 8 个 FSkelMeshSection 分层
│   ├── Body_RyzaRevT1_SK_OriginalSlots.glb            # 原始 8 个 UE3 材质槽位 PBR GLB
│   ├── Body_RyzaRevT1_SK_WithBoostCone.glb            # 主模型 + 自动挂载至 BoostConeMesh 插槽的尾喷口氮气锥静态网格体
│   └── Body_RyzaRevT1_BoostConeMesh.glb               # 独立导出的尾喷口氮气锥静态网格体 (UStaticMesh, 2,360 顶点 / 4,184 三角面)
├── metadata/                                          # 结构化指标表与全场景元数据
│   ├── Body_RyzaRevT1_metadata.json                   # 车辆 RB_BodySetup_0 碰撞盒、ProductAsset_Body_TA、四轮悬挂坐标、动画树、插槽与材质汇总
│   ├── Body_RyzaRevT1_surface_bindings.json           # 【核心】21 个精细材质图层 & 8 个原始槽位的面片绑定规则、证据链、UV/空间包围盒与蒙皮骨骼表
│   └── Body_RyzaRevT1_scene.json                      # UPK 内全部 243 个 Export 对象与 105 个 Import 对象的完整属性及静态材质开关转储
├── textures/                                          # 提取的 24 张原始贴图与 17 张烘焙 PBR 贴图
│   ├── *.png                                          # UPK 内置全部 24 张贴图 (Body_RyzaRevT1_*, Chassis_RyzaRevT1_*, Trim_RyzaRevT1_*, Lenses_RyzaRevT1_N 等)
│   └── baked_pbr/                                     # 转换后的切线空间 RGB 法线贴图、BaseColor、MetallicRoughness、Emissive 贴图
├── raw/                                               # 原始数据包与 umodel 兼容分层导出
│   ├── upk/body_ryzarevt1_SF.upk                      # 原始加密压缩 UPK 文件 (2,730,532 bytes)
│   └── body_ryzarevt1_SF/                             # 按 Group 与 Class 导出的 .gltf/.bin/.png/.mat/.props.txt
└── scripts/                                           # 可复用的全套 Python 提取与 GLB 构建工具链
    ├── unpack_upk.py                                  # Rocket League UPK AES 解密与 Zlib 块解压工具
    ├── upk_core.py                                    # UPK 名字表/导入导出表/属性树/静态开关解析器与 DXT1/DXT5/A8R8G8B8/DXT5nm 解码器
    ├── mesh_gltf_builder.py                           # USkeletalMesh / UStaticMesh 二进制反序列化与 glTF 2.0 坐标/骨骼/插槽/法线转换核心
    └── extract_and_build.py                           # 一键提取原始资产、分类面片材质区域并生成全部 GLB 与元数据的主脚本
```

---

## 二、 核心几何、骨骼、悬挂与物理碰撞盒 (`RB_BodySetup_0` & `ProductAsset_Body_TA`) 指标

| 指标项 | 数值 / 详情 |
| :--- | :--- |
| **SkeletalMesh 名称** | `Body_RyzaRevT1_SK` (Export `#208`, `ProductID = 12798`) |
| **顶点总数 / 三角面总数** | **61,521 顶点** / **91,993 三角面** (`NumUVSets = 2`, `bHasVertexColors = True`) |
| **StaticMesh 附加网格** | `Body_RyzaRevT1_BoostConeMesh` (Export `#218`, **2,360 顶点** / **4,184 三角面**, 材质 `Master_Octane_Nitrous_Boost_MIC`, 挂载于 `BoostConeMesh` 插槽) |
| **原始材质槽位 (`Materials`, 8 个)** | `[0] MIC_RyzaRevT1_Chassis`, `[1] MIC_RyzaRevT1_Plastic`, `[2] MIC_RyzaRevT1_Body (SkinMaterialIndex=2)`, `[3] MIC_RyzaRevT1_Body`, `[4] MIC_RyzaRevT1_Windshield`, `[5] MIC_RyzaRevT1_Lenses`, `[6] MIC_RyzaRevT1_Trim (Painted Slot)`, `[7] MIC_RyzaRevT1_TrimMetal` |
| **骨骼数量 (`RefSkeleton`)** | **36 根骨骼** (`SkeletalDepth = 5`)，包含底盘 `chassis_jnt`、四轮独立减震器 (`FL/FR/BL/BR_Shock_A/B/c_jnt`)、传动半轴 (`*_axleShaft_jnt`)、前轮转向节 (`FL/FR_Pivot_jnt`)、通风刹车盘 (`*_Disc_jnt` / `*_Disc_geo_jnt`) 与刹车卡钳 (`*_Brakepad_jnt`) |
| **动画控制树 (`Body_RyzaRevT1_AT`)** | **23 路骨骼控制器**（12 个 `SkelControlLookAt` + 11 个 `SkelControlSingleBone`）+ `SuperSonic` 超音速动画序列组 (`boost_start`, `boost_idle`) |
| **挂载插槽 (`Sockets`, 9 个)** | `AmbBoost` `[-53.5, 0.0, 17.75]`, `AntennaSocket` `[-36.0, -25.0, 24.0]`, `BoostConeMesh` `[-48.9956, 0.0, 15.5]` (Scale `[1.0, 1.1, 1.0]`), `FrontSocket` `[72.0704, 0.0, 4.75]`, `HatSocket` `[-5.0, 0.0, 36.0]` (Pitch `-3.999°`), `RocketBoost` `[-58.0, 0.0, 13.5]`, `Underglow` `[4.6099, 0.0, -10.0]`, `BoostEmitterLeft` `[-57.0, -8.0, 15.5]`, `BoostEmitterRight` `[-57.0, 8.0, 15.5]` |
| **操控预设 (`HandlingPreset`)** | `HandlingPresets.Presets.Octane` (`CAR_CONFIG_OCTANE`) + `HandlingPresetZOffset = 2.2` |
| **刚体碰撞盒 (`RB_BodySetup_0.AggGeom.BoxElems[0]`)** | 尺寸 **`X = 148.925232 UU` × `Y = 83.279953 UU` × `Z = 33.799999 UU`**，局部变换中心位移 **`[9.0, 0.0, 4.25] UU`** |
| **前后桥车轮参数 (`FrontAxle` / `BackAxle`)** | 前桥：`WheelMeshRadius = 13.0 UU`, `WheelWidth = 10.5 UU`, `WheelMeshOffsetSide = 1.0 UU`；后桥：`WheelWidth = 12.5 UU`, `WheelMeshOffsetSide = 2.0 UU`；底盘弹簧最大位移：`[50.0, 25.0, 50.0] UU` |
| **四轮悬挂基准坐标 (`WheelTranslation_jnt`)** | 前左 `[55.3142, -26.8510, -6.6534]` / 前右 `[55.3142, 26.8510, -6.6534]` / 后左 `[-35.6027, -26.8474, -5.0727]` / 后右 `[-35.6027, 26.8474, -5.0727]` |
| **轴距 (`Wheelbase`) / 轮距 (`Track Width`)** | 轴距 **90.9169 UU** (`0.9092 m`) / 前轮距 **53.7020 UU** (`0.5370 m`) / 后轮距 **53.6948 UU** (`0.5369 m`) |

---

## 三、 证据确凿的面片-材质区域绑定表（21 层精细划分 vs 8 个原始槽位）

`Body_RyzaRevT1_SK` 在 UE3 中拥有 8 个原始 `FSkelMeshSection`。我们结合 **材质实例参数与静态开关 (`MIC_RyzaRevT1_*`)**、**贴图通道遮罩 (`Chassis_RyzaRevT1_RGB`, `Chassis_RyzaRevT1_M`, `Body_RyzaRevT1_Blankskin`, `Body_RyzaRevT1_D.A`, `Trim_RyzaRevT1_N.R`, `Trim_RyzaRevT1_D`)**、**精确离散顶点色 (`COLOR_0`)** 以及 **骨骼蒙皮权重 (`JOINTS_0`)**，将全部 **91,993 个三角面** 精确划分为 **21 个语义明确的材质图层**：

| 图层 ID | 材质图层名称 (`material.name`) | 中文语义说明 | 原始 Section | 三角面数 | 顶点数 | 判定规则与确凿证据 |
| :---: | :--- | :--- | :---: | ---: | ---: | :--- |
| `0` | `RyzaRevT1_Chassis_Headlight_Emissive` | 前大灯内腔发光灯碗与日行灯发光体 (Chassis Headlight Emissive) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **262** | 218 | `Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.R > 30` |
| `1` | `RyzaRevT1_Chassis_Taillight_Emissive` | 贯穿式/环绕尾灯与刹车灯发光体 (Chassis Taillight & Brake Emissive) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **1,685** | 1,242 | `Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.G > 30` |
| `2` | `RyzaRevT1_Chassis_BoostGlow_CyanEmissive` | 双尾喷口内腔青蓝色氮气发光环 (Chassis BoostGlow Cyan Emissive) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **120** | 152 | `Section 0 (MIC_RyzaRevT1_Chassis) && Chassis_RyzaRevT1_RGB.B > 30` |
| `3` | `RyzaRevT1_Chassis_AdditionalEmissive_OrangeAmber` | 底盘附加发光灯带（红/绿双通道橙珀色氛围光） (Chassis Additional Emissive Map) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **171** | 181 | `Section 0 (MIC_RyzaRevT1_Chassis) && (Chassis_RyzaRevT1_M.R > 20 || Chassis_RyzaRevT1_M.G > 20)` |
| `4` | `RyzaRevT1_Chassis_BrakeDiscs_And_Calipers` | 四轮通风打孔刹车盘与高性能刹车卡钳 (Brake Discs & Calipers) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **2,784** | 2,224 | `Section 0 (MIC_RyzaRevT1_Chassis) && PrimaryBone in {FL/FR/BL/BR_Disc_geo_jnt, FL/FR/BL/BR_Brakepad_jnt}` |
| `5` | `RyzaRevT1_Chassis_Suspension_And_Axles` | 前后桥独立悬挂减震器、转向节与传动半轴 (Suspension Shocks, Pivots & Axles) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **4,062** | 3,192 | `Section 0 (MIC_RyzaRevT1_Chassis) && PrimaryBone in {FL/FR/BL/BR_Shock_A/B_jnt, *_axleShaft_jnt, *_Pivot_jnt, *_WheelTranslation_jnt}` |
| `6` | `RyzaRevT1_Chassis_EngineBay_And_Exhaust_Metal` | 后置涡轮引擎舱、双出排气管与底盘高亮金属件 (Engine Bay, Twin Exhaust & Bright Chassis Metal) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **15,550** | 11,750 | `Section 0 (MIC_RyzaRevT1_Chassis) && Bone==chassis_jnt && Chassis_RyzaRevT1_D.MeanRGB > 75` |
| `7` | `RyzaRevT1_Chassis_Undercarriage_And_CockpitTub` | 底盘护板、轮拱内衬与座舱内部暗色结构 (Chassis Undercarriage & Cockpit Tub) | Section `0` (`MIC_RyzaRevT1_Chassis`) | **14,644** | 12,511 | `Section 0 (MIC_RyzaRevT1_Chassis) && Bone==chassis_jnt && Chassis_RyzaRevT1_D.MeanRGB <= 75` |
| `8` | `RyzaRevT1_Plastic_FrontGrille_And_Splitter` | 前脸进气格栅蜂窝网、前唇与大灯外框哑光黑塑料 (Front Grille, Splitter & Headlight Bezel Plastic - Slot 1) | Section `1` (`MIC_RyzaRevT1_Plastic`) | **4,344** | 2,978 | `Section 1 (MIC_RyzaRevT1_Plastic, UseAsPlastic=True) && Centroid.X >= 0.0` |
| `9` | `RyzaRevT1_Plastic_RearDiffuser_And_Vents` | 尾部下扩散器格栅、散热网孔与后保险杠哑光黑塑料 (Rear Diffuser, Exhaust Surround & Vents Plastic - Slot 1) | Section `1` (`MIC_RyzaRevT1_Plastic`) | **2,468** | 1,506 | `Section 1 (MIC_RyzaRevT1_Plastic, UseAsPlastic=True) && Centroid.X < 0.0` |
| `10` | `RyzaRevT1_Body_Slot2_PrimaryPaint` | 主车身金属车漆与涂装画布层 (Primary Painted Bodywork & Decal Canvas - Slot 2) | Section `2` (`MIC_RyzaRevT1_Body`) | **11,705** | 7,074 | `Section 2 (MIC_RyzaRevT1_Body, SkinMaterialIndex=2) && Body_RyzaRevT1_D.A > 128` |
| `11` | `RyzaRevT1_Body_Slot2_RecessedPanelSeams_And_Accents` | 主车身钣金凹槽接缝与深色嵌入式饰条 (Recessed Body Panel Seams & Dark Accents - Slot 2) | Section `2` (`MIC_RyzaRevT1_Body`) | **2,795** | 2,037 | `Section 2 (MIC_RyzaRevT1_Body, SkinMaterialIndex=2) && Body_RyzaRevT1_D.A <= 128` |
| `12` | `RyzaRevT1_Body_Slot3_RoofLouver_SecondaryPaint` | 后部车顶与中置引擎盖百叶窗双遮罩副色车漆面板 (Rear Roof & Engine Decklid Louver Secondary Paint - Slot 3) | Section `3` (`MIC_RyzaRevT1_Body`) | **3,112** | 1,775 | `Section 3 (MIC_RyzaRevT1_Body, Slot 3) && Body_RyzaRevT1_Blankskin.G > 128 (99.71% of Section 3)` |
| `13` | `RyzaRevT1_Windshield_Canopy_Glass` | 座舱前挡风玻璃与左右侧窗深色玻璃 (Cockpit Windshield & Side Windows Glass - Slot 4) | Section `4` (`MIC_RyzaRevT1_Windshield`) | **940** | 545 | `Section 4 (MIC_RyzaRevT1_Windshield, Slot 4, Parent=MAT_Vehicle_Windshield_Base / SPMF_OldWindow_v2022)` |
| `14` | `RyzaRevT1_Lenses_FrontHeadlight_ClearGlass` | 前大灯外层透明折射灯罩透镜 (Front Headlight Clear Translucent Lenses - Slot 5) | Section `5` (`MIC_RyzaRevT1_Lenses`) | **946** | 581 | `Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 255, 255, 255] && Centroid.X > 0.0` |
| `15` | `RyzaRevT1_Lenses_RearTaillight_RedGlass` | 尾部高位红色刹车灯/尾灯透明透镜 (Rear Red Taillight Translucent Lenses - Slot 5) | Section `5` (`MIC_RyzaRevT1_Lenses`) | **40** | 32 | `Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 0, 0, 255] && Centroid.X < 0.0` |
| `16` | `RyzaRevT1_Lenses_RearReverse_ClearGlass` | 尾部白色倒车灯/转向灯透明透镜 (Rear Clear Reverse/Indicator Lenses - Slot 5) | Section `5` (`MIC_RyzaRevT1_Lenses`) | **24** | 20 | `Section 5 (MIC_RyzaRevT1_Lenses) && VertexColor == [255, 255, 255, 255] && Centroid.X <= 0.0` |
| `17` | `RyzaRevT1_Trim_PaintableExteriorAero_Slot6` | 可涂装认证版侧裙、轮眉与空气动力学外饰条 (Paintable Exterior Aero Trim & Fender Arches - Slot 6) | Section `6` (`MIC_RyzaRevT1_Trim`) | **11,194** | 7,057 | `Section 6 (MIC_RyzaRevT1_Trim, Slot 6, ProductAttribute_PaintSettings_TA MaterialGroups[6], PaintParameterName='TrimColor')` |
| `18` | `RyzaRevT1_TrimMetal_AnodizedAccent_Masked` | 法线红通道遮罩阳极氧化钛灰金属饰件 (Anodized Titanium Trim Accent - Normal.R Masked - Slot 7) | Section `7` (`MIC_RyzaRevT1_TrimMetal`) | **1,802** | 1,332 | `Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R > 64` |
| `19` | `RyzaRevT1_TrimMetal_BrushedSteel_Bright` | 高亮拉丝不锈钢外露机械与排气尾喉饰件 (Bright Brushed Steel Trim & Exhaust Tips - Slot 7) | Section `7` (`MIC_RyzaRevT1_TrimMetal`) | **4,318** | 2,921 | `Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R <= 64 && Trim_RyzaRevT1_D.MeanRGB > 50` |
| `20` | `RyzaRevT1_TrimMetal_DarkGunmetal_Structural` | 深色枪灰金属结构件、紧固件与进气道金属网框 (Dark Gunmetal Structural Trim & Fasteners - Slot 7) | Section `7` (`MIC_RyzaRevT1_TrimMetal`) | **9,027** | 6,542 | `Section 7 (MIC_RyzaRevT1_TrimMetal, Slot 7) && Trim_RyzaRevT1_N.R <= 64 && Trim_RyzaRevT1_D.MeanRGB <= 50` |

> **验证结论**：21 个材质图层的三角面数总和 = **91,993**，与 `Body_RyzaRevT1_SK` 原始总面数完全一致（零遗漏、零重叠）。在 `Body_RyzaRevT1_SK_WhiteModel.glb` 中，上述 21 个区域作为独立的 glTF Primitive 分别绑定到对应的纯白材质图层（`baseColorFactor = [1.0, 1.0, 1.0, 1.0]`，无任何外部或内嵌贴图），可在 Blender / Three.js / Maya / Unreal 中直接按材质图层选中或单独赋材质。

---

## 四、 复现与使用方法

```bash
# 1. 解密并解压原始 UPK
python3 scripts/unpack_upk.py raw/upk/body_ryzarevt1_SF.upk /tmp/body_ryzarevt1_SF_unpacked.upk

# 2. 运行全流程提取、纹理烘焙、区域分类与 GLB 构建
python3 scripts/extract_and_build.py
```
