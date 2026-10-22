# Rocket League `body_thrice_SF` (Body_Thrice_SK) 模型、原始资产与全量材质区域绑定规范仓库

本分支 (`body_thrice_SF`) 为 `body_thrice_SF.upk` 的标准化示范分支，完整包含：
1. **原始数据包与反序列化资产 (`raw/`)**：按 UPK 内部 Group 层级与 Class 分类导出的 `.gltf` + `.bin`、贴图 `.png`、材质 `.mat` 与属性表 `.props.txt`（100% 兼容 UE Viewer / umodel 结构）。
2. **多层级 GLB 模型 (`models/`)**：包含 16 层精细化材质绑定 PBR 模型、**纯白无贴图材质分层白模 (`Body_Thrice_SK_WhiteModel.glb`)**、原始 6 材质槽位白模与 PBR 模型、带尾喷口锥体 (`Thrice_boostconemesh`) 挂载模型。
3. **证据链完备的面片-材质区域绑定指标表 (`metadata/`)**：所有 **90,362 个三角面（57,002 个顶点）** 100% 无遗漏、无重叠地映射到对应的材质图层，并附带遮罩采样、顶点色、骨骼蒙皮权重与空间包围盒证据。
4. **纯 Python 全流程提取与构建脚本 (`scripts/`)**：无需外部闭源工具即可从加密压缩的 `.upk` 直接解密、解压、反序列化并生成所有 GLB 与元数据。

---

## 一、 仓库目录结构

```text
body_thrice_SF/
├── README.md                                       # 分支架构、模型指标与材质区域绑定完整说明
├── models/                                         # 导出的 GLB 模型集合
│   ├── Body_Thrice_SK.glb                          # 主模型（16 个证据确凿的精细材质图层 + 完整骨骼/插槽 + 烘焙 PBR 贴图 + 完整 extras 元数据）
│   ├── Body_Thrice_SK_DetailedSurfaces.glb         # 同上，16 层精细化材质绑定 PBR GLB
│   ├── Body_Thrice_SK_WhiteModel.glb               # 【纯白白模 - 16 层精细材质分类】无任何贴图绑定，纯白色 [1,1,1,1]，不同面片严格绑定到 16 个材质图层
│   ├── Body_Thrice_SK_WhiteModel_OriginalSlots.glb # 【纯白白模 - 原始 6 槽位】无任何贴图绑定，纯白色 [1,1,1,1]，按 UE3 原始 6 个 FSkelMeshSection 分层
│   ├── Body_Thrice_SK_OriginalSlots.glb            # 原始 6 个 UE3 材质槽位 PBR GLB
│   ├── Body_Thrice_SK_WithBoostCone.glb            # 主模型 + 自动挂载至 BoostEmitter 插槽的尾喷口火焰锥静态网格体
│   └── Thrice_boostconemesh.glb                    # 独立导出的尾喷口锥体静态网格体 (UStaticMesh)
├── metadata/                                       # 结构化指标表与全场景元数据
│   ├── Body_Thrice_metadata.json                   # 车辆骨骼、插槽、四轮悬挂接触点、轴距轮距、材质参数与图层汇总
│   ├── Body_Thrice_surface_bindings.json           # 【核心】16 个精细材质图层 & 6 个原始槽位的面片绑定规则、证据链、UV/空间包围盒与蒙皮骨骼表
│   └── Body_Thrice_scene.json                      # UPK 内全部 230 个 Export 对象的完整属性反序列化转储
├── textures/                                       # 提取的原始贴图与烘焙 PBR 贴图
│   ├── *.png                                       # UPK 内置贴图 (Diffuse, Blankskin, FXMasks, Chassis_D/N/RGB, Peaking, Blank_N)
│   ├── shared_dependencies/Body_Thrice_n.png       # 车身主法线贴图
│   └── baked_pbr/                                  # 转换后的切线空间 RGB 法线贴图、BaseColor、MetallicRoughness、Emissive 贴图
├── raw/                                            # 原始数据包与 umodel 兼容分层导出
│   ├── upk/body_thrice_SF.upk                      # 原始加密压缩 UPK 文件
│   └── body_thrice_SF/                             # 按 Group (Body/Materials/Shared/TeamPaint/Textures) 与 Class 导出的 .gltf/.bin/.png/.mat/.props.txt
└── scripts/                                        # 可复用的全套 Python 提取与 GLB 构建工具链
    ├── unpack_upk.py                               # Rocket League UPK AES 解密与 Zlib 块解压工具
    ├── upk_core.py                                 # UPK 名字表/导入导出表/属性树解析器与 DXT1/DXT5/DXT5nm 解码器
    ├── mesh_gltf_builder.py                        # USkeletalMesh / UStaticMesh 二进制反序列化与 glTF 2.0 坐标/骨骼/法线转换核心
    └── extract_and_build.py                        # 一键提取原始资产、分类面片材质区域并生成全部 GLB 与元数据的主脚本
```

---

## 二、 核心几何、骨骼与物理悬挂指标

| 指标项 | 数值 / 详情 |
| :--- | :--- |
| **SkeletalMesh 名称** | `Body_Thrice_SK` (Export `#203`) |
| **顶点总数 / 三角面总数** | **57,002 顶点** / **90,362 三角面** |
| **UV 通道数 / 顶点色** | `NumUVSets = 2` (`TEXCOORD_0`, `TEXCOORD_1`) / `bHasVertexColors = True` (`COLOR_0`) |
| **骨骼数量 (`RefSkeleton`)** | **36 根骨骼** (`SkeletalDepth = 5`)，包含底盘、四轮独立减震器 (`FL/FR/BL/BR_Shock_A/B/c_jnt`)、传动半轴 (`*_axleShaft_jnt`)、转向节 (`FL/FR_Pivot_jnt`)、通风刹车盘 (`*_Disc_geo_jnt`) 与卡钳 (`*_Brakepad_jnt`) |
| **挂载插槽 (`Sockets`)** | **9 个插槽**：`HatSocket`, `AntennaSocket`, `BoostEmitter`, `Headlight_Left`, `Headlight_Right`, `TailLight_Left`, `TailLight_Right`, `LicensePlate`, `EngineAudio` |
| **网格包围盒 (`Bounds` in UU)** | `Min = [-73.32, -45.43, -9.97]`, `Max = [85.83, 45.43, 27.67]`, 尺寸 `159.15 × 90.86 × 37.64 UU` |
| **四轮悬挂接触中心 (`WheelTranslation_jnt`)** | 前左 `[52.9682, -31.8380, 0.2564]` / 前右 `[52.9682, 31.8380, 0.2564]` / 后左 `[-49.8400, -32.2758, 0.8548]` / 后右 `[-49.8400, 32.2758, 0.8548]` |
| **轴距 (`Wheelbase`) / 轮距 (`Track Width`)** | 轴距 **102.8082 UU** (`1.0281 m`) / 前轮距 **63.6760 UU** (`0.6368 m`) / 后轮距 **64.5516 UU** (`0.6455 m`) |

---

## 三、 证据确凿的面片-材质区域绑定表（16 层精细划分 vs 6 个原始槽位）

`Body_Thrice_SK` 在 UE3 中拥有 6 个原始 `FSkelMeshSection`，我们结合 **材质实例参数 (`MIC_Thrice_Chassis`, `MAT_Lens_VertColor`, `MIC_Thrice_Body_T1`)**、**贴图通道遮罩 (`chassis_Thrice_rgb`, `Body_Thrice_Blankskin_Tier_01`, `Body_Thrice_Diffuse_Tier_01`)**、**精确离散顶点色 (`COLOR_0`)** 以及 **骨骼蒙皮权重 (`JOINTS_0`)**，将全部 **90,362 个三角面** 精确划分为 **16 个语义明确的材质图层**：

| 图层 ID | 材质图层名称 (`material.name`) | 中文语义说明 | 原始 Section | 三角面数 | 顶点数 | 判定规则与确凿证据 |
| :---: | :--- | :--- | :---: | ---: | ---: | :--- |
| `0` | `Thrice_Chassis_Headlight_Emissive` | 前大灯发光灯碗与日行灯内腔 (Chassis Headlight Emissive) | Section `0` (`MIC_Thrice_Chassis`) | **508** | 406 | `Section 0 (MIC_Thrice_Chassis) && chassis_Thrice_rgb.R > 80` |
| `1` | `Thrice_Chassis_Taillight_And_BoostGlow` | 尾灯发光灯带与尾喷口内腔发光 (Chassis Taillight & BoostGlow) | Section `0` (`MIC_Thrice_Chassis`) | **366** | 371 | `Section 0 (MIC_Thrice_Chassis) && (chassis_Thrice_rgb.G > 80 || chassis_Thrice_rgb.B > 80)` |
| `2` | `Thrice_Chassis_BrakeDiscs_And_Calipers` | 四轮通风刹车盘与刹车卡钳 (Brake Discs & Calipers) | Section `0` (`MIC_Thrice_Chassis`) | **2,368** | 1,490 | `Section 0 (MIC_Thrice_Chassis) && PrimaryBone in {FL/FR/BL/BR_Disc_geo_jnt, FL/FR/BL/BR_Brakepad_jnt}` |
| `3` | `Thrice_Chassis_Suspension_And_Axles` | 前后桥减震器弹簧与传动半轴 (Suspension Shocks & Axles) | Section `0` (`MIC_Thrice_Chassis`) | **4,142** | 2,687 | `Section 0 (MIC_Thrice_Chassis) && PrimaryBone in {FL/FR/BL/BR_Shock_*_jnt, *_axleShaft_jnt, *_Pivot_jnt}` |
| `4` | `Thrice_Chassis_BrushedMetal_Engine_And_Exhaust` | 中置发动机舱金属构件与中置排气管 (Engine Bay & Exhaust Metal) | Section `0` (`MIC_Thrice_Chassis`) | **3,451** | 3,175 | `Section 0 (MIC_Thrice_Chassis) && Bone==chassis_jnt && (chassis_Thrice_d.Luminance > 95 || VertexColor.R == 255)` |
| `5` | `Thrice_Chassis_Undercarriage_And_CockpitTub` | 底盘护板、扩散器底座与座舱内部结构 (Chassis Undercarriage & Tub) | Section `0` (`MIC_Thrice_Chassis`) | **18,597** | 13,571 | `Section 0 (MIC_Thrice_Chassis) && Bone==chassis_jnt && Dark Matte Chassis Base` |
| `6` | `Thrice_Rear_Engine_Louver_SmokedGlass` | 后部中置引擎盖百叶窗熏黑透明玻璃 (Rear Engine Cover Smoked Glass) | Section `1` (`MAT_Lens_VertColor`) | **852** | 489 | `Section 1 (MAT_Lens_VertColor, Slot 1) && VertexColor == [0, 0, 0, 255] (100% of section)` |
| `7` | `Thrice_Lens_Headlight_CyanWhite` | 前大灯外层透明灯罩 (Front Headlight Clear/Cyan Lenses) | Section `2` (`MAT_Lens_VertColor`) | **275** | 202 | `Section 2 (MAT_Lens_VertColor, Slot 2) && VertexColor == [103, 149, 149, 255]` |
| `8` | `Thrice_Lens_FogLight_Yellow` | 前唇下部黄色雾灯/示廓灯透镜 (Front Lower Yellow Fog Lenses) | Section `2` (`MAT_Lens_VertColor`) | **108** | 86 | `Section 2 (MAT_Lens_VertColor, Slot 2) && VertexColor == [129, 135, 13, 255]` |
| `9` | `Thrice_Lens_TurnSignal_Amber` | 前部琥珀色转向灯/日行灯透镜 (Front Amber Turn Signal Lenses) | Section `2` (`MAT_Lens_VertColor`) | **269** | 241 | `Section 2 (MAT_Lens_VertColor, Slot 2) && VertexColor == [156, 61, 0, 255]` |
| `10` | `Thrice_Lens_Taillight_Red` | 尾部双拱形红色尾灯/刹车灯透镜 (Rear Red Taillight Lenses) | Section `2` (`MAT_Lens_VertColor`) | **704** | 576 | `Section 2 (MAT_Lens_VertColor, Slot 2) && VertexColor == [255, 0, 0, 255]` |
| `11` | `Thrice_Body_Slot3_PrimaryPaint` | 主车身金属车漆与涂装画布层 (Primary Painted Bodywork - Slot 3) | Section `3` (`MIC_Thrice_Body_T1`) | **28,768** | 17,087 | `Section 3 (MIC_Thrice_Body_T1, SkinMaterialIndex=3) && Body_Thrice_Blankskin_Tier_01.R > 128` |
| `12` | `Thrice_Body_Slot3_PanelSeam_Trim` | 主车身钣金接缝与边缘深色饰条 (Body Panel Seam Trim - Slot 3) | Section `3` (`MIC_Thrice_Body_T1`) | **352** | 477 | `Section 3 (MIC_Thrice_Body_T1, SkinMaterialIndex=3) && Body_Thrice_Blankskin_Tier_01.R <= 128` |
| `13` | `Thrice_Body_Slot4_Trim_MattePlastic_And_Carbon` | 前铲、侧裙、进气道与车窗外框哑光黑/碳纤维饰件 (Body Trim & Aero Splitters - Slot 4) | Section `4` (`MIC_Thrice_Body_T1`) | **24,130** | 15,219 | `Section 4 (MIC_Thrice_Body_T1, Slot 4) && Body_Thrice_Blankskin_Tier_01.R <= 128` |
| `14` | `Thrice_Body_Slot4_PaintedAeroAccents` | 空气动力学套件同色车漆点缀区域 (Painted Aero Accents - Slot 4) | Section `4` (`MIC_Thrice_Body_T1`) | **4,886** | 3,883 | `Section 4 (MIC_Thrice_Body_T1, Slot 4) && Body_Thrice_Blankskin_Tier_01.R > 128` |
| `15` | `Thrice_Windshield_Canopy_Glass` | 座舱环绕式前挡风玻璃与侧窗玻璃 (Cockpit Windshield & Side Windows - Slot 5) | Section `5` (`MIC_Thrice_Body_T1`) | **586** | 386 | `Section 5 (MIC_Thrice_Body_T1, Slot 5) && Body_Thrice_Blankskin_Tier_01.B == 255 && VertexColor == [255, 255, 255, 255] (100% of section)` |

> **验证结论**：16 个材质图层的三角面数总和 = **90,362**，与 `Body_Thrice_SK` 原始总面数完全一致（零遗漏、零重叠）。在 `Body_Thrice_SK_WhiteModel.glb` 中，上述 16 个区域作为独立的 glTF Primitive 分别绑定到对应的纯白材质图层（`baseColorFactor = [1.0, 1.0, 1.0, 1.0]`，无任何外部或内嵌贴图），可在 Blender / Three.js / Maya / Unreal 中直接按材质图层选中或单独赋材质。

---

## 四、 复现与使用方法

```bash
# 1. 解密并解压原始 UPK
python3 scripts/unpack_upk.py raw/upk/body_thrice_SF.upk /tmp/body_thrice_SF_unpacked.upk

# 2. 运行全流程提取、纹理烘焙、区域分类与 GLB 构建
python3 scripts/extract_and_build.py
```
