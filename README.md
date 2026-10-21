# Three-Wheeler Octane (`body-tritip-threewheel` / `CAR_CONFIG_PSYCLOPS`)

本分支包含愚人节三轮车限时模式 (`GameInfo_LTM_AprilFool_SF.upk` 中的 `Mutator_Loadout_TA'GameInfo_LTM_AprilFool.Mutators.Tritip'`) 所使用的三轮八角车 (`body_tritip` / `CAR_CONFIG_PSYCLOPS`) 模型、细分平面材质 GLB 与完整物理参数。

- **核心物理特性 (`CAR_CONFIG_PSYCLOPS`)**：
  - 基底 Hitbox 与 Octane 相同：`size = (118.0074, 84.19941, 36.15907)`，`offset = (13.87566, 0, 20.75499)`。
  - **单前轮居中**：前轮挂载点从双侧 `Y = ±25.89` 合并至正中央 `(X = 49.0, Y = 0.0, Z = 20.75)`，有效接地车轮数 `numWheels = 3`（1 前轮 + 2 后轮）。
  - **高侧倾摩擦曲线 (`Car_Test` `Wheel_TA`)**：侧向抓地系数 `LatFrictionCurve` 提升至 `0 -> 2.0, 1 -> 0.4`（标准车为 `0 -> 1.0, 1 -> 0.2`），手刹侧向摩擦降至 `0.05`，使得急转弯时三角支撑结构极易产生剧烈侧倾与翻滚。
