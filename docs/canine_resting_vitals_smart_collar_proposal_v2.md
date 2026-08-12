# Project Proposal - MVP Plan v2

# Canine Resting Vitals Smart Collar

狗狗静息健康趋势项圈 - IMU-BCG + 订阅式 App MVP 项目计划书

本项目目标是在 12 周内验证一个长期佩戴式智能项圈原型。它不做医疗诊断，而是在狗狗安静休息或睡眠时，自动捕捉静息呼吸率、静息心率趋势、活动/睡眠状态和温度趋势，并通过 App 建立个人 baseline、趋势提醒和健康报告，为后续 startup 产品化和订阅式服务建立技术与实验基础。

## 0. v2 修改摘要

| 主题 | v1 想法 | v2 修改 |
|---|---|---|
| 心率路线 | piezo + MEMS mic 作为主要探索 | BMI270 高采样率 IMU-BCG/SCG 作为第一候选 |
| 呼吸路线 | IMU/piezo | 保持 IMU + piezo，piezo 主要服务呼吸和辅助微振动 |
| 麦克风 | 心率探索通道 | 降级为低优先级辅助通道，可暂缓购买 |
| 产品形态 | 原型验证为主 | 明确未来订阅式 App 和健康趋势服务 |
| 商业模型 | 未展开 | 硬件 + 订阅，第一代不做 GPS/cellular |
| 预算 | 第一轮约 $600 | 推荐第一轮约 $630-$680，主要增加数据记录和机械贴合预算 |

## 1. 项目定位

本项目面向宠物健康趋势监测场景。传统胸带或背心式设备更容易获得高质量生理信号，但日常佩戴时长不足；项圈更符合狗狗长期佩戴习惯，但生理信号更弱、噪声更多。因此，本项目采用项圈本体加下方贴合模块的结构：用项圈解决佩戴时长，用贴合模块改善颈部微振动和呼吸信号质量。

第一代产品不应被定义为医疗器械或诊断设备，而应被定义为长期佩戴的健康趋势监测设备。它关注静息窗口、个人 baseline、趋势变化和信号置信度，而不是承诺运动中每秒精准心率或疾病诊断。

一句话产品定位：

> 不是找狗，而是看狗每天安静时身体状态有没有变化。

## 2. MVP 范围

| 包含在 MVP 中 | 暂不包含 |
|---|---|
| 静息呼吸率估算 | 医疗诊断或疾病判断 |
| 静息心率趋势探索 | 运动中心率准确测量 |
| IMU-BCG/SCG 心率候选验证 | 心律失常诊断 |
| 活动/睡眠/静息窗口识别 | 血氧 SpO2 准确检测 |
| 温度趋势记录 | 真实核心体温判断 |
| BLE/USB/SD 数据记录 | 第一代 GPS、蜂窝通信 |
| 信号质量评分 | 云端商业系统完整上线 |
| App dashboard 原型 | 兽医级 clinical claim |

## 3. 推荐传感器策略

v2 的关键调整是：心率探索不再把 piezo + MEMS mic 作为主路线，而是把 IMU-BCG/SCG 作为第一候选。原因是狗项圈场景中，心搏引发的颈部微小运动可以被高精度运动传感器捕捉；公开竞品路线和 BCG 文献都支持这种方向。piezo 和麦克风仍有价值，但更适合作为补充通道，而不是第一优先级。

| 功能 | 第一选择 | 辅助选择 | 目的 |
|---|---|---|---|
| 静息窗口识别 | BMI270 IMU | 规则 + 标签 | 判断狗是否处于 resting/sleeping，过滤运动伪影 |
| 呼吸趋势 | IMU + piezo ribbon/disk | 视频人工计数 | 捕捉胸颈部低频周期性运动或压力变化 |
| 心率趋势 | BMI270 high-rate IMU-BCG/SCG | piezo 接触微振动 | 在静息窗口内寻找心搏周期性微振动 |
| 声学探索 | 暂缓或低优先级 MEMS mic | 外壳声学耦合实验 | 作为可选辅助，不作为第一代核心 |
| 温度趋势 | MCP9808 或同类温度传感器 | MCU 内置温度仅作参考 | 记录接触区域温度趋势，不等同于体温 |
| 参考验证 | ADS1292R ECG/Respiration | 人工视频标注 | 建立对照数据，验证算法误差 |

## 4. 技术架构

| 层级 | 推荐方案 | 说明 |
|---|---|---|
| 主控 | nRF52840 | BLE、USB、低功耗、开发生态成熟 |
| 运动传感 | BMI270 | 同时用于活动识别、呼吸趋势、IMU-BCG 心率探索 |
| 接触传感 | piezo ribbon/disk | 呼吸和辅助微振动通道 |
| 温度 | MCP9808 | 接触区域温度趋势 |
| 本地记录 | USB CSV + 可选 microSD | 高采样率 IMU 数据建议优先保证完整记录 |
| App 原型 | 手机 App 或本地 dashboard | 展示状态、趋势、信号质量和实验数据 |
| 云端原型 | 可延后 | 12 周内可先用本地/手动同步数据验证算法 |

IMU 采样建议：

| 用途 | 建议采样率 | 说明 |
|---|---|---|
| 活动识别 | 25-50 Hz | 足够区分走动、趴着、睡眠 |
| 呼吸趋势 | 25-100 Hz | 呼吸频率低，重点是滤波和窗口选择 |
| 心率 BCG 探索 | 100-400 Hz 起步 | 优先看 SNR 和轴向，必要时测试更高采样率 |
| 原始数据验证 | 尽量保留 raw | 早期不要只存算法输出，否则难以复盘 |

## 5. 从零采购预算 - v2

以下按美国采购、第一台原型从零开始估算。价格会随库存、税和运费变化。

| 类别 | 建议采购 | 数量 | 预算 |
|---|---|---:|---:|
| 主控 | Adafruit Feather nRF52840 Express | 1 | $25 |
| 运动传感 | SparkFun BMI270 IMU | 2 | $37-$50 |
| 呼吸/微振动 | Piezoelectric ribbon sensor | 1 | $20-$30 |
| 微振动备选 | Small enclosed piezo sensors | 2-3 | $5-$15 |
| 温度趋势 | MCP9808 temperature sensor | 1 | $5 |
| 数据记录 | microSD breakout + card 或可靠 USB logger | 1 | $10-$25 |
| 电源 | 3.7V LiPo 500-1200mAh + charger | 1-2 | $15-$30 |
| 连接 | Qwiic/STEMMA cables, JST, silicone wire | 若干 | $20-$35 |
| 机械 | BioThane/TPU 项圈带、小外壳、硅胶片、neoprene、固定件 | 若干 | $80-$150 |
| 参考验证 | ADS1292R ECG/Respiration kit + electrodes | 1 | $80-$130 |
| 可选声学 | I2S MEMS microphone breakout | 0-1 | $0-$7 |
| 工具 | 焊台、万用表、焊锡、手工具、面包板等 | 1 套 | $160-$260 |

建议第一轮准备约 $630-$680。少于 $500 也能启动，但会更容易卡在线材、外壳、备用件、数据记录和工具上。工具不计入单台原型 BOM，因为后续样机可以复用。

预算变化总结：

| 项目 | 变化 |
|---|---|
| BMI270 | 建议买 2 块，便于做不同安装位置和备用测试 |
| MEMS mic | 可以暂缓，节省小额预算 |
| piezo | 数量减少，定位为呼吸和辅助通道 |
| microSD/数据记录 | 建议新增，避免高采样率 IMU 数据丢失 |
| 机械贴合 | 预算上调，这是 BCG 信号质量的关键 |

## 6. 产品化成本判断

原型预算不等于量产成本。$600 左右的第一台原型主要贵在开发板、工具、备用件、运费和实验验证。真正产品化后，使用定制 PCB 和集成结构，硬件 BOM 会显著下降。

第一代建议产品形态：

| 决策 | 建议 |
|---|---|
| GPS | 第一代不做 |
| 蜂窝通信 | 第一代不做 |
| 连接方式 | BLE 为主 |
| 核心价值 | 静息健康趋势和个人 baseline |
| 医疗定位 | 不做诊断，只做 wellness/trend |
| 订阅价值 | 趋势解释、提醒、报告、数据历史 |

量产成本粗估：

| 模块 | 量产成本粗估 |
|---|---:|
| nRF52 BLE SoC/MCU | $3-$8 |
| IMU | $1-$4 |
| 温度传感器 | <$1 |
| piezo 辅助通道 | $0.5-$3 |
| 电池 | $2-$5 |
| 充电/电源管理 | $1-$3 |
| PCB + assembly | $4-$10 |
| 外壳 + 硅胶贴合 + 项圈结构 | $6-$15 |
| 测试、包装、损耗 | $5-$12 |

目标 COGS：

| 产品版本 | 目标 COGS | 可行售价 |
|---|---:|---:|
| BLE 健康趋势版 | $25-$45 | $99-$149 |
| GPS/LTE 健康安全版 | $40-$80+ | $149-$249 + subscription |
| 兽医/高风险犬版本 | $60-$120+ | $299+ + subscription |

本项目第一代应优先做 BLE 健康趋势版，避免 GPS/LTE 把成本、功耗、认证、通信费和售后责任同时拉高。

## 7. 订阅式 App 策略

订阅式 App 是合理方向，但订阅价值不应是“查看原始传感器数据”，而应是持续解释、提醒、趋势、照护建议和安心感。

推荐定价探索：

| 层级 | 内容 | 价格假设 |
|---|---|---:|
| 免费版 | 当天状态、近 7 天趋势、基础活动/睡眠 | $0 |
| Plus | 长期 baseline、异常趋势提醒、每周健康报告 | $6.99-$12.99/mo |
| Care | 老年犬/心脏风险犬、数据导出、护理摘要、多狗档案 | $14.99-$19.99/mo |

App 第一版核心页面：

| 页面 | 内容 |
|---|---|
| Today | 当前状态、最近静息心率/呼吸率、信号质量 |
| Trends | 7/30/90 天 resting HR/RR baseline 和变化 |
| Sleep/Rest | 静息时间、睡眠片段、活动/休息分布 |
| Alerts | 趋势异常、连续升高、数据质量不足 |
| Report | 每周健康摘要，可导出给 vet |
| Device | 电池、佩戴质量、同步状态 |

12 周 MVP 阶段不需要完整商业 App。可以先做一个本地 dashboard 或轻量 mobile prototype，只要能展示订阅价值的核心逻辑即可。

## 8. 材料到齐后的启动步骤

| Day | 任务 | 产出 |
|---:|---|---|
| 1 | 整理材料、拍照归档、建立项目文件夹和实验日志 | 采购记录、材料编号、项目结构 |
| 2 | 主控板通电，跑通串口日志或 BLE 基础通信 | hello log / BLE advertising |
| 3 | BMI270 读取加速度和陀螺仪，测试 25/100/200/400 Hz | IMU raw CSV |
| 4 | MCP9808 读取温度 | 温度数据流 |
| 5 | Piezo 接 ADC，做敲击、弯曲、贴身呼吸测试 | 原始波形和噪声底 |
| 6 | 统一 data logger，保证 IMU 高采样率数据不丢包 | 多传感器 CSV |
| 7 | 做第一份人体/桌面 BCG 试验报告 | Week 1 notes + waveform plots |

## 9. 12 周 MVP Schedule - v2

| 周 | 目标 | 主要任务 | 产出 |
|---|---|---|---|
| Week 1 | 模块跑通 | 主控、BMI270、温度、piezo、logger | 单模块数据和测试记录 |
| Week 2 | 高采样率 IMU logging | 统一时间戳，测试 FIFO/USB/SD，避免丢包 | IMU raw dataset |
| Week 3 | 台架与人体 BCG | 桌面噪声、敲击、胸口/颈部/手腕 IMU BCG | 噪声底、轴向、频响初判 |
| Week 4 | 机械结构 V1 | 项圈 + 下方贴合模块，测试 IMU 固定刚性 | 可佩戴样机 V1 |
| Week 5 | 狗狗短时佩戴 | 5-10 分钟安静佩戴，观察舒适性和信号质量 | 第一批真实佩戴数据 |
| Week 6 | 静息窗口识别 | 用 IMU 区分走动、趴着、睡眠/静息 | resting/not resting 标签 |
| Week 7 | 呼吸算法 V1 | IMU/piezo 滤波、峰值检测、breaths/min 输出 | 呼吸率估算脚本 |
| Week 8 | 心率 BCG V1 | IMU 频域、峰值、模板匹配，piezo 辅助对比 | 心率可行性报告 |
| Week 9 | 对照实验 | 人工数呼吸、视频、ADS1292R 参考数据同步 | 误差表和图表 |
| Week 10 | 原型 V2 | 优化贴合压力、外壳、线材和佩戴稳定性 | 样机 V2 |
| Week 11 | 小样本数据 | 至少 5-10 次静息测试，每次 5-30 分钟 | 可展示数据集 |
| Week 12 | Demo 和总结 | dashboard、视频、图表、订阅 App story | MVP demo package |

## 10. 实验设计

| 实验 | 条件 | 目的 | 记录 |
|---|---|---|---|
| 空载噪声 | 设备放桌上 10-30 分钟 | 确认 IMU/piezo 噪声底和漂移 | CSV、环境温度、设备位置 |
| 人体 BCG | IMU 贴胸口/颈部/手腕 | 快速确认心搏能否出现在 IMU 波形中 | CSV、手动脉搏、姿势 |
| 人体呼吸 | IMU/piezo 贴胸口/腹部附近 | 快速确认呼吸波形和滤波参数 | CSV、人工呼吸节奏 |
| 狗狗短时佩戴 | 狗安静趴着或睡觉，5-10 分钟 | 检查舒适性、晃动、信号质量 | CSV、视频、人工数呼吸 |
| 狗狗长时佩戴 | 30-120 分钟，含活动和休息 | 验证静息窗口识别和数据连续性 | CSV、电池记录、状态标签 |
| 参考对照 | ADS1292R 或人工/视频计数同步 | 计算呼吸率误差，探索心率趋势可靠性 | 误差表、同步时间戳 |

## 11. 成功标准

| 指标 | MVP 目标 |
|---|---|
| 佩戴舒适性 | 狗狗 30 分钟内不明显抗拒，下方模块不明显勒脖子 |
| 数据完整性 | 连续记录 30 分钟不掉线，时间戳稳定 |
| 静息识别 | 能区分走动和趴着/睡眠，减少运动时误报 |
| 呼吸率 | 静息状态下目标误差控制在 +/- 3-5 breaths/min |
| 心率趋势 | 优先验证 IMU-BCG 是否在部分静息窗口可见稳定周期性信号 |
| 信号质量 | 每个输出值必须附带 Good/Medium/Poor 或置信度 |
| 电池 | 第一版至少 4-8 小时，后续再优化低功耗 |
| 结构 | 模块不大幅晃动，线材不外露，狗狗不能轻易咬到 |
| App story | 能展示 baseline、趋势提醒、每周报告的订阅价值 |

## 12. 风险和应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 毛发和贴合不稳定 | BCG/呼吸信号弱或噪声大 | 增加软硅胶接触面，调整模块重量、曲率和贴合压力 |
| 运动伪影太强 | 呼吸/心率误判 | 只在静息窗口输出结果，并显示信号质量 |
| BMI270 BCG 信号不足 | 心率功能缩水 | 引入更低噪声 IMU 或 ADXL355 类参考传感器做对照 |
| 心率信号不可用 | MVP 功能缩水 | 先主打呼吸率、活动/睡眠趋势和温度趋势 |
| 狗狗不愿佩戴 | 产品不可持续 | 先用轻量外壳和柔软贴合材料，缩短模块高度 |
| 防水不足 | 日常使用风险 | MVP 仅生活防水；产品化再做 IP 设计 |
| App 做太重 | 拖慢 MVP | 12 周内先做 dashboard，App 只做交互原型 |
| 订阅价值不清晰 | 用户不愿续费 | 把重点放在 baseline、异常趋势、报告和照护建议 |
| OPT 合规不清晰 | 身份和就业记录风险 | 提前咨询 DSO 和移民律师，保留工作日志和专业相关证据 |

## 13. 文件和记录结构

建议从第一天开始保留工程证据。这不仅帮助技术复盘，也能支持创业叙事、导师沟通和未来 OPT self-employment documentation。

| 文件夹 | 内容 |
|---|---|
| hardware/ | 接线图、外壳草图、BOM、结构照片 |
| firmware/ | 主控代码、传感器驱动、BLE/USB/SD logger |
| data/raw/ | 原始 CSV、音频、传感器日志 |
| data/processed/ | 滤波后数据、峰值检测结果、误差表 |
| experiments/ | 每次实验目的、条件、狗狗状态、视频链接、结论 |
| docs/ | proposal、weekly report、pitch notes、合规说明 |

记录项建议：

| 记录项 | 建议做法 |
|---|---|
| 工作时间 | 每周记录至少 20 小时相关工作，注明任务和产出 |
| 工程证据 | GitHub commits、原型照片、数据文件、实验日志 |
| 商业证据 | BOM、发票、市场调研、顾问沟通、用户访谈 |
| 专业相关性 | 每月写一段说明：本月工作如何对应 EE 专业训练 |
| 合规确认 | 保留 DSO/律师沟通记录，避免自行假设规则 |

本文档不构成法律意见。

## 14. Demo 形态

第 12 周的 demo 不需要商业 App。一个简单 dashboard 就足够：显示当前状态、信号质量、呼吸率、心率趋势置信度、活动状态和温度趋势，同时展示原始波形、滤波后波形和人工计数对照。

| Dashboard 字段 | 示例 |
|---|---|
| Status | Resting |
| Signal quality | Good / Medium / Poor |
| Respiratory rate | 22 breaths/min |
| Heart trend | Tentative / Low confidence |
| Activity | Sleeping / Resting / Moving |
| Temperature trend | Stable |
| Baseline | 30-day resting trend |
| Subscription story | Weekly health report |

## 15. 参考来源

- USCIS - Optional Practical Training (OPT) for F-1 Students: https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students
- Study in the States - International Students and Entrepreneurship: https://studyinthestates.dhs.gov/international-students-and-entrepreneurship
- Invoxia - Monitoring Your Dog's Health with the Minitailz: https://www.invoxia.com/pet-app-blog/en-US/monitoring-dog-health
- Invoxia - Assessing the Accuracy of the Minitailz on a Large-Scale Dataset: https://www.invoxia.com/blog/petcare/assessing-the-accuracy-of-the-invoxia-smart-dog-collar-on-a-large-scale-dataset/
- Jarkoff, Lorre, Humbert - Assessing the Accuracy of a Smart Collar for Dogs, bioRxiv: https://doi.org/10.1101/2023.06.09.544347
- Gardner et al. - Wearable Ballistocardiography Device for Estimating Heart Rate During PAP Therapy: https://cardio.jmir.org/2021/1/e26259/
- Bosch Sensortec - BMI270 IMU: https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi270/
- SparkFun BMI270 Breakout Documentation: https://sparkfun.github.io/SparkFun_Qwiic_6DoF_BMI270/
- Adafruit Feather nRF52840 Express: https://www.adafruit.com/product/4062
