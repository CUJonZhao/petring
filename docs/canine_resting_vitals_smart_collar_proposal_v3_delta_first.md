# Project Proposal - Stage 1 Engineering Plan v3

# Delta Rest & Activity Smart Collar Prototype

Delta-first 狗狗睡眠/活动记录智能项圈 - ESP32 + IMU + Wi-Fi Dashboard 第一阶段工程计划书

本项目的真实目标不是先做一个完整产业化设备，而是先发明并做出一款 Delta 能舒服佩戴、能在家中真实使用的智能项圈原型。第一阶段聚焦几个小时的无线睡眠/活动实验记录：用现有 ESP32 Feather/HUZZAH32 V2、Feather OLED、IMU、电池和浏览器 dashboard，验证佩戴舒适性、无线数据链路、活动/休息识别和实验日志。后续再逐步扩展呼吸、心率趋势、手机 App 和订阅式服务。

## 0. 当前需求理解

| 维度 | 已确认决策 |
|---|---|
| 第一目标 | 做出真实可用的产品原型，先给家里的狗 Delta 使用 |
| 使用对象 | Delta，4 个月喜乐蒂犬，约 7.5 kg，长毛，愿意戴项圈，暂无健康问题 |
| 第一优先功能 | 睡眠/活动记录，而不是先做心率/呼吸 |
| 实验尺度 | 先做几个小时实验记录，再升级优化 |
| 佩戴原则 | 舒适和安全优先，数据质量第二 |
| 模块位置 | 倾向项圈下方贴合，为后续呼吸/心率预留条件 |
| 外壳方式 | 第一版手工原型，不先做 3D 打印 |
| 数据方式 | 不能插线拖电脑，优先无线实时监控 |
| 电脑端 | 先做浏览器网页 dashboard，后续再迁移手机 App |
| 无线通信 | 第一版用 ESP32 连接家里 Wi-Fi |
| 现有硬件 | ESP32 Feather/HUZZAH32 V2、Feather monochrome 128x32 OLED |
| 电池 | 暂无 LiPo，第一阶段可接受 400-800 mAh 小电池 |
| 第一阶段传感器 | 推荐 IMU + 电池 + OLED，预留 piezo/温度/呼吸/心率扩展 |

## 1. 项目定位

本项目第一阶段定位为 Delta-first engineering prototype。它不是医疗诊断设备，也不是一开始就面向大规模销售的量产项圈，而是一款面向真实家庭使用的实验型智能项圈模块。

第一阶段的产品定义：

> 一个 Delta 愿意佩戴几个小时、能无线显示并记录活动/休息状态的下方贴合式项圈模块。

第一阶段不追求漂亮外壳、长期续航、完整手机 App 或医疗级准确性。真正要验证的是：

- Delta 是否愿意佩戴；
- 下方贴合模块是否安全、轻、不可轻易啃咬；
- IMU 数据是否能区分走动、玩耍、趴下、睡觉/休息；
- Wi-Fi dashboard 是否能稳定实时显示并保存 CSV；
- 这个硬件结构是否能为后续呼吸/心率扩展留下空间。

## 2. 第一阶段范围

| 第一阶段包含 | 第一阶段不包含 |
|---|---|
| ESP32 Feather V2 无线数据采集 | GPS 或蜂窝通信 |
| IMU 活动/休息记录 | 医疗诊断 |
| OLED 本地状态显示 | 准确心率测量 |
| Wi-Fi 浏览器 dashboard | 准确呼吸率测量 |
| CSV 实验日志保存 | 长期无人值守续航 |
| 电池供电佩戴测试 | 防水量产外壳 |
| 手工下方贴合结构 | 3D 打印或注塑外壳 |
| 后续传感器接口预留 | App Store 级手机 App |

## 3. 第一阶段系统架构

| 模块 | 第一阶段方案 | 理由 |
|---|---|---|
| 主控 | 现有 ESP32 Feather/HUZZAH32 V2 | 已拥有，支持 Wi-Fi，开发快，适合第一版 |
| 显示 | 现有 Feather monochrome 128x32 OLED | 显示 IP、电池、状态、连接状态 |
| 传感器 | 6-DoF IMU，推荐 LSM6DSOX | 轻、小、便宜、I2C 连接，足够做活动/睡眠 |
| 电源 | 3.7V LiPo 500 mAh 起步 | 小型、轻量、Feather 生态兼容 |
| 连接 | STEMMA QT/Qwiic I2C cable | 少焊接，方便快速迭代 |
| 电脑端 | 浏览器 dashboard | 最快做实时曲线、状态和 CSV 保存 |
| 外壳 | 手工小盒 + 泡棉/硅胶/Velcro | 低成本验证舒适性和固定方式 |

第一阶段数据流：

| 步骤 | 数据流 |
|---|---|
| 1 | IMU 采集 ax, ay, az, gx, gy, gz |
| 2 | ESP32 计算 motion score 和当前状态 |
| 3 | ESP32 通过 Wi-Fi 推送实时数据 |
| 4 | 电脑浏览器 dashboard 显示曲线和状态 |
| 5 | dashboard 保存 CSV 实验日志 |
| 6 | 人工记录 Delta 的实际行为用于对照 |

## 4. 推荐采购清单

因为你已经有 ESP32 Feather 和 OLED，第一阶段不建议购买新主控。预算应集中在 IMU、电池、连接线和舒适固定材料。

| 优先级 | 物品 | 数量 | 估算价 | 作用 |
|---|---|---:|---:|---|
| 必买 | Adafruit LSM6DSOX 6-DoF IMU - STEMMA QT/Qwiic | 1 | $11.95 | 活动/休息识别第一传感器 |
| 必买 | 3.7V LiPo 500 mAh，JST-PH | 1 | $7.95 | 佩戴实验电源 |
| 必买 | STEMMA QT/Qwiic 4-pin cable，50 mm 或 100 mm | 2-3 | $0.95-$1.25 each | IMU 连接，便于返工 |
| 必买 | 小塑料盒/热缩管/泡棉/软硅胶片/Velcro | 若干 | $15-$30 | 手工下方贴合结构 |
| 建议买 | JST-PH 延长线、硅胶线、双面胶、扎带 | 若干 | $10-$20 | 电池和线材整理 |
| 建议买 | 备用 LiPo 350-500 mAh | 1 | $6-$8 | 多轮测试备用 |
| 暂缓 | BMI270 IMU | 0-1 | $18-$25 | 后续 BCG/心率路线对比 |
| 暂缓 | piezo ribbon/disk | 0 | $10-$30 | 后续呼吸/贴合微振动 |
| 暂缓 | 温度传感器 MCP9808 | 0 | $5 | 后续温度趋势 |
| 暂缓 | microSD module | 0 | $5-$15 | Wi-Fi dashboard 不稳定后再加 |
| 暂缓 | nRF52840 | 0 | $25 | 第二阶段低功耗/BLE 迁移 |

推荐第一阶段预算：

| 版本 | 预算 | 适用情况 |
|---|---:|---|
| 最低开工 | $35-$50 | 只买 IMU、电池、线和简单固定材料 |
| 推荐启动 | $60-$90 | 加备用线材、电池和更舒服的手工结构材料 |
| 过度采购 | 不建议超过 $150 | 第一阶段还没验证佩戴和数据，不要先买太多 |

## 5. 为什么第一阶段不先买 BMI270/nRF/piezo

BMI270、nRF52840 和 piezo 都有价值，但它们更适合第二阶段。第一阶段最重要的问题不是心率，而是 Delta 是否愿意戴、无线链路是否稳定、活动/睡眠数据是否可用。

| 物品 | 暂缓原因 | 后续何时购买 |
|---|---|---|
| BMI270 | 更贴近 IMU-BCG 心率探索，但第一阶段活动/休息不需要 | 当第一版佩戴和 dashboard 跑通后，用于心率/BCG 对比 |
| nRF52840 | 更接近低功耗 BLE 产品，但开发会拖慢第一版 | 当 Wi-Fi 原型证明有价值后，做低功耗版本 |
| piezo | 对呼吸和贴合微振动有价值，但增加机械复杂度 | 当下方贴合结构稳定后再加 |
| 温度传感器 | 容易加，但不是第一优先功能 | 当活动/休息记录稳定后再加 |
| microSD | 可靠性好，但第一版可由电脑 dashboard 保存 CSV | Wi-Fi 丢包明显时再加 |

## 6. 佩戴结构方案

Delta 是 4 个月、7.5 kg、长毛喜乐蒂。长毛会降低贴合信号质量，但第一阶段只做活动/睡眠，不需要强压贴合。结构设计应优先舒适、安全、低晃动和防啃咬。

第一版结构原则：

- 模块尽量接近吊牌大小，但允许略大于吊牌，因为 Feather 本身不小；
- 位置在项圈下方靠近喉咙，但只轻贴，不压迫；
- 外表面平滑，无裸露线材、硬边或可咬凸起；
- 模块和 IMU 要固定在一起，避免 IMU 在盒内松动；
- 用泡棉或软硅胶接触项圈/毛发区域，减少硬物压迫；
- 先用 Velcro/弹性带可拆卸固定，不做永久固定。

建议装配：

| 部位 | 做法 |
|---|---|
| ESP32 + OLED | 放入小盒或热缩保护层，保留 USB-C 充电入口 |
| IMU | 固定在盒内靠近项圈一侧，和盒体刚性连接 |
| 电池 | 放在盒内或盒背，用泡棉隔开，不能被挤压或折弯 |
| 线材 | 全部收进盒内或热缩管内，外部不留可咬线 |
| 接触面 | 加软泡棉/硅胶垫，轻贴毛发，不追求压紧皮肤 |
| 固定 | Velcro 穿过项圈或绕项圈固定，便于快速拆卸 |

安全底线：

- 第一次佩戴只做 5-10 分钟；
- 佩戴时必须有人观察；
- 不在无人看管时给幼犬长时间佩戴；
- 不让 Delta 睡觉时佩戴尚未验证过的硬件；
- 电池不能被咬到、刺穿、弯折或压迫；
- 模块不能勒脖子，不能影响吞咽、呼吸和转头。

## 7. 固件计划

ESP32 固件第一版使用 Arduino/PlatformIO 路线，优先快跑通。

| 固件模块 | 功能 |
|---|---|
| imu_reader | 读取 ax, ay, az, gx, gy, gz |
| feature_extractor | 计算 accel magnitude、gyro magnitude、motion score |
| state_classifier | 输出 Active / Resting / Unknown |
| wifi_server | 连接家里 Wi-Fi，提供 dashboard 页面或数据接口 |
| websocket_stream | 实时发送 IMU 和状态数据 |
| oled_status | 显示 IP、电池、Wi-Fi、当前状态 |
| battery_monitor | 读取电池电压，估算电量 |
| config | Wi-Fi 名称、密码、采样率、阈值 |

第一版采样建议：

| 用途 | 采样率 |
|---|---:|
| 活动/休息识别 | 25-50 Hz |
| 实时 dashboard 曲线 | 10-25 Hz 显示即可 |
| 原始 CSV 保存 | 25-50 Hz |
| 后续呼吸探索 | 25-100 Hz |
| 后续心率/BCG | 100-400 Hz，再升级传感器/结构 |

第一版状态规则：

| 状态 | 判断逻辑 |
|---|---|
| Active | motion score 连续高于阈值 |
| Resting | motion score 连续低于阈值 2-5 分钟 |
| Unknown | 刚切换、数据不足、信号异常或中间状态 |

## 8. 浏览器 Dashboard 计划

第一版 dashboard 运行在电脑浏览器中。ESP32 连接家里 Wi-Fi 后，OLED 显示 IP 地址，电脑访问该 IP 即可查看页面。

第一版页面内容：

| 区域 | 内容 |
|---|---|
| Header | Delta Collar Prototype、连接状态、设备 IP |
| Current State | Active / Resting / Unknown |
| Live Motion | motion score 实时曲线 |
| Raw IMU | ax, ay, az, gx, gy, gz 可选显示 |
| Battery | 电池电压和估算电量 |
| Session Controls | Start Recording / Stop / Export CSV |
| Notes | 手动输入实验备注，如 sleeping, walking, playing |

CSV 字段：

| 字段 | 说明 |
|---|---|
| timestamp_ms | ESP32 时间戳 |
| host_time | 电脑记录时间 |
| ax, ay, az | 加速度 |
| gx, gy, gz | 角速度 |
| accel_mag | 加速度模长 |
| gyro_mag | 角速度模长 |
| motion_score | 活动强度分数 |
| state | Active / Resting / Unknown |
| battery_v | 电池电压 |
| note | 人工备注 |

## 9. 第一周开工计划

| Day | 任务 | 成功标准 |
|---:|---|---|
| 1 | 确认 ESP32 Feather V2 可烧录，OLED 可显示文字 | OLED 显示 hello 和板子状态 |
| 2 | 接 IMU，跑 I2C scan | 能识别 OLED 和 IMU 地址 |
| 3 | 读取 IMU 数据并输出串口 CSV | 静止/移动时数据变化合理 |
| 4 | ESP32 连接家里 Wi-Fi，显示 IP | 电脑浏览器能访问设备 |
| 5 | dashboard 显示实时 motion score | 移动模块时曲线明显变化 |
| 6 | 电池供电测试 30-60 分钟 | 不插 USB 也能稳定运行 |
| 7 | Delta 5-10 分钟佩戴舒适性测试 | 无抗拒、无啃咬、无压迫、数据可记录 |

第一周不需要追求漂亮算法。重点是把硬件、无线、dashboard、CSV 和佩戴安全打通。

## 10. 第一阶段实验 Protocol

实验 1 - 桌面静止噪声：

| 条件 | 记录 | 目的 |
|---|---|---|
| 模块放桌上 10 分钟 | CSV、环境备注 | 确认静止 motion score 噪声底 |

实验 2 - 手持运动：

| 条件 | 记录 | 目的 |
|---|---|---|
| 人手拿起、旋转、轻晃、放下 | CSV、动作时间备注 | 确认 active/resting 阈值可分离 |

实验 3 - 项圈空载：

| 条件 | 记录 | 目的 |
|---|---|---|
| 模块固定在项圈上，不戴狗 | CSV、视频/照片 | 检查晃动、线材、固定方式 |

实验 4 - Delta 短佩戴：

| 条件 | 记录 | 目的 |
|---|---|---|
| 5-10 分钟，有人观察 | CSV、视频、人工备注 | 检查舒适、安全、是否啃咬 |

实验 5 - Delta 室内活动/休息：

| 条件 | 记录 | 目的 |
|---|---|---|
| 30-60 分钟，包含走动、趴下、休息 | CSV、人工行为备注 | 验证活动/休息识别 |

实验 6 - 几小时记录：

| 条件 | 记录 | 目的 |
|---|---|---|
| 2-3 小时，有人间歇观察 | CSV、电池、舒适度备注 | 验证第一阶段目标 |

## 11. 第一阶段成功标准

| 指标 | 目标 |
|---|---|
| 舒适性 | Delta 愿意佩戴 30 分钟以上，无明显抓挠、抗拒或啃咬 |
| 安全性 | 无裸露线材，无压迫喉咙，无电池暴露 |
| 无线稳定性 | Wi-Fi dashboard 连续接收 30 分钟以上 |
| 数据完整性 | 能导出 CSV，时间戳连续，字段完整 |
| 活动区分 | 走动/玩耍与趴下/休息的 motion score 明显不同 |
| OLED 可用性 | 能显示 IP、电池、Wi-Fi 和当前状态 |
| 结构可迭代 | 能方便拆卸、充电、更换固定材料 |

第一阶段完成标准不是“准确识别睡眠医学指标”，而是“Delta 可佩戴 + 数据链路可用 + 活动/休息可分”。

## 12. 第二阶段扩展路线

当第一阶段稳定后，再进入第二阶段。

| 方向 | 触发条件 | 下一步 |
|---|---|---|
| 更小硬件 | Feather 模块太大但功能有效 | 迁移到更小 ESP32/nRF 板或自制 PCB |
| 更长续航 | Wi-Fi 续航不足 | 降采样、睡眠模式、BLE/nRF52840 |
| 呼吸趋势 | 下方贴合结构舒适稳定 | 加 piezo 或用 IMU 低频呼吸信号 |
| 心率探索 | 呼吸/静息窗口识别稳定 | BMI270/更高性能 IMU 做 BCG/SCG |
| 温度趋势 | 基础活动数据稳定 | 加 MCP9808 接触温度趋势 |
| 手机 App | dashboard 逻辑有效 | 迁移到 Web App / mobile app |
| 订阅服务 | 数据能形成长期 baseline | 每周报告、趋势提醒、历史数据 |

## 13. 文件结构

建议当前项目文件夹按以下结构推进：

| 文件夹 | 内容 |
|---|---|
| hardware/ | 接线图、BOM、结构照片、外壳草图 |
| firmware/ | ESP32 固件、IMU 驱动、Wi-Fi server |
| dashboard/ | 浏览器 dashboard 前端 |
| data/raw/ | 原始 CSV |
| data/processed/ | 分析结果、阈值实验、图表 |
| experiments/ | 每次实验记录、视频链接、Delta 行为备注 |
| docs/ | proposal、采购清单、weekly notes |

建议每次实验命名：

| 类型 | 示例 |
|---|---|
| 原始数据 | data/raw/2026-08-01_delta_short_wear_001.csv |
| 实验记录 | experiments/2026-08-01_delta_short_wear_001.md |
| 结构照片 | hardware/photos/2026-08-01_module_mount_v1.jpg |

## 14. 风险和应对

| 风险 | 影响 | 应对 |
|---|---|---|
| Delta 啃咬模块 | 电池和线材安全风险 | 线材全收纳，模块平滑，短时有人观察 |
| 下方贴合不舒服 | Delta 不愿佩戴 | 降低贴合压力，换侧面位置或更软材料 |
| 长毛导致信号弱 | 后续呼吸/心率困难 | 第一阶段只做活动/休息，后续再优化贴合 |
| Feather 模块偏大 | 吊牌大小目标难达成 | 第一阶段接受略大，第二阶段小型化 |
| Wi-Fi 续航短 | 几小时实验受限 | 先接受手动充电，后续 BLE/低功耗 |
| dashboard 丢数据 | CSV 不完整 | 降采样、浏览器端缓存，必要时加 microSD |
| 算法误判休息 | 睡眠记录不可信 | 先输出 Resting/Active/Unknown，不急着叫 Sleep |
| 过早加太多传感器 | 项目复杂度失控 | 第一阶段只装 IMU，接口预留 |

## 15. 后续产品化方向

如果第一阶段成功，长期产品可以走硬件 + App + 订阅路线。但第一代商业化产品不应从 GPS/cellular 开始，而应从健康趋势和活动/休息 baseline 开始。

长期产品愿景：

| 层级 | 内容 |
|---|---|
| 硬件 | 轻量项圈下方模块，BLE，低功耗，IMU + 温度 + 可选 piezo |
| App | 今日状态、休息趋势、活动趋势、佩戴质量 |
| 订阅 | 长期 baseline、每周报告、异常趋势提醒、数据导出 |
| 扩展 | 呼吸趋势、静息心率趋势、老年犬健康观察 |

产品定位仍应保持克制：

> 不做疾病诊断，先做 Delta 和普通家庭真正愿意长期使用的健康趋势记录工具。

## 16. 参考来源

- Adafruit ESP32 Feather V2: https://learn.adafruit.com/adafruit-esp32-feather-v2
- Adafruit OLED FeatherWing: https://learn.adafruit.com/adafruit-oled-featherwing/overview
- Adafruit LSM6DSOX 6-DoF IMU: https://www.adafruit.com/product/4438
- Adafruit 500 mAh LiPo Battery: https://www.adafruit.com/product/1578
- Adafruit STEMMA QT / Qwiic Cables: https://www.adafruit.com/category/619
- SparkFun BMI270 Qwiic Hookup Guide: https://docs.sparkfun.com/SparkFun_Qwiic_6DoF_BMI270/single_page/
