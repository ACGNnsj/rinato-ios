# 《圣灵家族 Rinato》nxnative 式 iOS 原生运行实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在 iPhone 11 Pro Max / iOS 27.2.1 上，以用户自己的 Rinato 1.0.1 游戏数据运行原 Unity IL2CPP 代码，首个交付达到真实标题画面、触屏进入首段可交互剧情、保存并冷启动读档。

**Done means:** M0 探针证明 JIT/PAC/内存可行；M1 有原代码启动轨迹；M2 有游戏自身产生的连续标题帧；M3 有真实输入和存档往返证据。缺任何一类证据都不能宣称对应阶段完成。

**Not doing:** 不支持其他设备，不做免 JIT/App Store，不在 iOS 内解密原始 XCI/NSP，不重写 Unity 工程，不实现完整 Switch 模拟器，不把音视频缺口隐藏为完整移植。

设计依据：`docs/superpowers/specs/2026-11-24-rinato-ios-native-design.md`。

## 阶段总表

| # | Step | Verification | Produces |
|---|---|---|---|
| 1 | 工程边界、完整 RomFS/模块提取与哈希清单 | 独立测试复算提取结果；找到 IL2CPP 元数据和真实依赖 | 可复现输入、依赖清单 |
| 2 | iPhone JIT/PAC/内存/Metal 真机探针 | 真机日志证明测试代码执行、PAC 调用和 Metal 清屏；记录内存预算 | M0 设备结论与未签名 IPA |
| 3 | 可复用 NVN/Metal 与 shader 路线探针 | CI 构建并运行 Metal 三角形；确认组件许可证和 A13 支持 | 图形依赖决策 |
| 4 | 跨平台 NSO 加载器与重定位测试 | 对真实 main 复算段、符号、BSS 和重定位；畸形输入失败 | 不执行游戏的加载器 |
| 5 | 原代码入口与未知导入轨迹 | 真机 trace 到达可定位的 Unity/游戏代码；未知调用明确失败 | M1 调用顺序与服务清单 |
| 6 | 最小 Horizon 服务闭环 | 原代码到达首个 NVN 调用；无假成功关键服务 | M1 完成证据 |
| 7 | 游戏自身 NVN → Metal 标题帧 | 连续真实帧、present/draw 统计、实际 shader 编译记录 | M2 标题画面 |
| 8 | 触控、剧情推进与原子存档 | 标题进入首段剧情；保存后杀进程冷启动读回 | M3 首个交付 |
| 9 | 构建、兼容清单与交付审计 | 从不含游戏数据的源码重建未签名 IPA；证据与限制可复核 | 源码、IPA、说明和证据 |

---

### Task 1: 建立可复现的工程与游戏数据清单

**Files:**
- Create: `.gitignore`, `README.md`, `NOTICE.md`
- Create: `tools/rinato_package.py`
- Create: `tools/test_rinato_package.py`
- Create: `docs/evidence/rinato-1.0.1-manifest.json`
- Reference: `D:\consoles\ns\hayarigami-recomp\tools\extract_exefs.py` 与 `nso.py`

**Steps:**
- [ ] 初始化独立工程；忽略 `game-data/`、`secrets/`、`*.ipa`、临时提取物和日志中的敏感路径。记录复用代码来源与许可证，不复制来源不明的运行时。
- [ ] 以最小改动复用现有 XCI/NSP 提取逻辑，分别处理 APP/UPD；补齐 1.0.1 RomFS 和全部可执行模块，不假设合并 XCI 已受支持。
- [ ] 清单记录原包、模块、RomFS 文件的大小和 SHA-256，定位 `global-metadata.dat`、Unity assets、UniNAS、shader 与媒体。密钥内容不写入清单。
- [ ] 写标准库/assert 测试：合法样本复算一致，截断文件、错误哈希和路径穿越必须失败。

**Verification:** 在 Windows 用现有 Python 环境运行 `tools/test_rinato_package.py`；从原包重新提取得到的清单与已保存清单一致，且确认元数据和 `libunas.nrs` 的实际来源。

**Produces:** 后续步骤唯一允许使用的版本化输入与依赖清单。

### Task 2: 先证明 iPhone 11 Pro Max 的执行环境

**Files:**
- Create: `ios/Rinato/`（最小宿主、Metal 视图、日志）
- Create: `ios/Rinato/NativeProbe.mm`
- Create: `ios/Rinato.xcodeproj/`
- Create: `.github/workflows/ios-probe.yml`
- Create: `docs/evidence/M0-device.md`

**Steps:**
- [ ] 用已选 macOS CI 构建不含任何游戏数据的未签名 IPA；Windows 侧载并辅助启用 JIT，记录实际工具版本和错误原文。
- [ ] 显示 Metal 清屏和本地日志，证明应用、Metal 与文件目录工作。
- [ ] 执行返回固定值的 ARM64 测试函数，并测试宿主 arm64e 函数指针、原代码式间接调用和返回；分别记录 arm64/arm64e、PAC 与 JIT 结果。
- [ ] 使用系统可用内存接口和有界分配探针记录预算，不故意把设备跑到 jetsam。资源采用按需读取，不加载整个 RomFS。

**Verification:** 真机日志含固定返回值、PAC 调用结果、JIT 结果、内存数据；截图是设备上的 Metal 清屏。任一项未测都标为未知，不能用模拟器或 macOS 结果替代。

**Produces:** M0 go/no-go。若 JIT、PAC 或内存模型不成立，停止 Task 4 之后的执行并回到路线选择。

### Task 3: 锁定 NVN/Metal 和 shader 复用路线

**Files:**
- Create: `docs/graphics-dependencies.md`
- Create: `runtime/Metal/ProbeMetal.mm`
- Modify: `NOTICE.md`
- Reference: MeloNX/Ryujinx/nxnative 的实际源码与许可证，不以搜索摘要代替代码审计

**Steps:**
- [ ] 审计可复用 NVN 解码、命令转换和 shader 后端，记录提交哈希、许可证、依赖、ARM64/iOS/A13 限制；优先复用，不另写全栈转换器。
- [ ] 将最小 Metal 三角形接入真机探针，覆盖 render pipeline、shader 编译、command buffer 与 present。
- [ ] 若候选组件依赖不可用的桌面 API或许可证不兼容，保留失败证据并选择更小后端；不得引入无法审计的二进制。

**Verification:** iPhone 上显示非清屏的 Metal 三角形并有 present 计数；CI 日志证明 shader 编译成功，文档明确哪些代码可复用、哪些必须自写。

**Produces:** Task 7 的图形后端决策。没有可用 shader 路线时不扩大 HLE。

### Task 4: 实现可测试的 NSO 加载器，不先执行游戏

**Files:**
- Create: `runtime/Loader/NsoLoader.hpp`, `runtime/Loader/NsoLoader.cpp`
- Create: `runtime/Loader/Relocation.hpp`, `runtime/Loader/Relocation.cpp`
- Create: `tests/nso_loader_tests.cpp`
- Reference: Task 1 的 `main`、`subsdk0`、`sdk` 与清单

**Steps:**
- [ ] 解析 NSO 段、LZ4、MOD0、dynamic/dynsym、BSS/TLS 与模块布局；真实 `main` 使用 Task 1 的哈希防错。
- [ ] 实现真实数据出现的 ABS64、GLOB_DAT、JUMP_SLOT、RELATIVE 与 RELR；未知类型和越界写入明确失败。
- [ ] 测试合法镜像、截断段、坏 MOD0、未知重定位、重叠段与 BSS 清零，并和 Python 侦察工具的结果交叉核对。

**Verification:** 主机测试通过；真实 `main` 的镜像大小、文本段、符号数和重定位计数与清单一致，所有写入都在分配范围内。

**Produces:** 可加载但不能宣称“已启动游戏”的确定性模块。

### Task 5: 获取原代码启动轨迹

**Files:**
- Create: `runtime/Loader/Module.cpp`
- Create: `runtime/HLE/ImportDispatch.cpp`
- Create: `runtime/Diagnostics/Trace.cpp`
- Create: `docs/evidence/M1-boot-trace.md`

**Steps:**
- [ ] 在已通过 M0 的设备上加载真实模块，初始化 BSS/TLS、应用重定位并进入入口；宿主与游戏代码的 trampoline 遵循 Task 2 的 PAC 结论。
- [ ] 所有未绑定导入走统一记录和致命错误，记录符号、模块偏移、调用序号和寄存器证据。不得批量假成功。
- [ ] 只实现 trace 证明必须的安全导入，逐步推进到可定位的 Unity/游戏代码；每次改变后保存新的首个阻断点。

**Verification:** 日志显示已验证的入口、初始化和代码位置；首个未知服务可复现。若停在加载器/重定位，先修根因，不扩大 HLE。

**Produces:** 按真实调用顺序排列的必须实现、可延后和禁止假成功清单。

### Task 6: 完成到达 NVN 的最小 Horizon 服务

**Files:**
- Create: `runtime/HLE/Memory.cpp`, `runtime/HLE/Threading.cpp`
- Create: `runtime/HLE/FileSystem.cpp`, `runtime/HLE/Time.cpp`
- Create: `tests/hle_tests.cpp`
- Modify: `docs/evidence/M1-boot-trace.md`

**Steps:**
- [ ] 按 Task 5 轨迹实现内存、线程、同步、只读游戏文件和时钟；文件映射限制在导入目录，禁止路径穿越。
- [ ] 对线程/同步和文件映射保留小型测试；未知服务继续致命记录，不返回伪造的成功。
- [ ] 驱动原代码到达第一个真实 NVN 初始化调用，保存参数和模块偏移。

**Verification:** HLE 测试通过；真机 trace 从入口连续到达 NVN，无未解释的假成功或重复轮询伪装进展。

**Produces:** M1 完成证据和 Task 7 的首个图形调用点。

### Task 7: 显示游戏自身产生的标题画面

**Files:**
- Create: `runtime/NVN/`
- Create: `runtime/Metal/`
- Create: `docs/evidence/M2-title.md`

**Steps:**
- [ ] 按真实调用实现 device/queue/window、资源池、buffer/texture、command buffer 和同步。
- [ ] 用 Task 3 选定的后端转换本作实际 shader；不支持的指令、格式或特性明确报错并记录 shader 哈希。
- [ ] 完成绘制与 present，逐帧保存真实输出和 draw/present 计数；不使用宿主占位图。

**Verification:** iPhone 连续多帧显示标题，非单纯清屏或三角形；真实 shader 编译与绘制日志、截图相互对应。

**Produces:** M2 完成证据。若实际 shader 路线失败，停止输入/存档扩展并重新评估图形方案。

### Task 8: 完成首段剧情和冷启动读档

**Files:**
- Create: `ios/Rinato/Input.swift`
- Create: `runtime/HLE/Hid.cpp`, `runtime/HLE/Save.cpp`
- Create: `tests/save_tests.cpp`
- Create: `docs/evidence/M3-first-story.md`

**Steps:**
- [ ] 映射确认、取消、方向、菜单、快进和对话推进；需要时接 iOS GameController，不额外设计虚拟手柄体系。
- [ ] 从标题进入首段可交互剧情，记录文本、资源、音频和视频的真实状态；首版允许列出音视频缺口，但不能静默跳过。
- [ ] 存档写入应用 Documents，临时文件 flush 后原子替换并保留一次旧档；测试异常写入不破坏旧档。

**Verification:** 真机操作证据显示从标题到首段交互；保存后终止应用并冷启动，读回相同进度，存档测试通过。

**Produces:** 首个可交付可玩闭环，不代表全游戏完成。

### Task 9: 重建与交付审计

**Files:**
- Create: `docs/BUILD.md`, `docs/COMPATIBILITY.md`
- Modify: `README.md`

**Steps:**
- [ ] 从不含 ROM、密钥和提取素材的干净源码副本重建未签名 IPA。
- [ ] 汇总设备、工具版本、每个里程碑的日志/截图/测试结果，列出音视频和后续剧情未覆盖项。
- [ ] 检查仓库和 CI 产物没有游戏包、密钥、提取素材、账号凭据和不必要的绝对路径。

**Verification:** 干净重建成功；文档中的每条完成声明都能指向实际证据，未验证项明确写未知。

**Produces:** 可审查的首版源码、IPA 和交付说明。

## Risks & tripwires

| Risk | Early signal | Reaction |
|---|---|---|
| iOS 27.2.1 无法获得所需 JIT | M0 固定测试函数不能执行或 entitlement/debug 错误 | 停止动态加载路线，回到 AOT/模拟器选型 |
| A13 PAC/ABI 边界不兼容 | 间接调用、返回或 trampoline 在最小探针失败 | 先修最小 ABI 模型；不能证明则停止 |
| 4GB 内存不足 | M0 可用内存低于原运行时需要，或加载段/资源时持续压力异常 | 按需映射和减峰值；仍不足则停止并重新选型 |
| 944 个未定义符号导致盲目补全 | 启动 trace 出现大量未知服务或间接分发 | 回到加载/重定位与最小调用链，禁止批量假成功 |
| NVN shader 无法转 Metal | 真实 shader 编译失败、关键指令/格式不支持 | 保留哈希和错误，停止扩展并更换后端/路线 |
| CI/侧载链泄露或混入游戏数据 | 构建日志、产物或仓库出现密钥/ROM/素材 | 立即撤回产物、清理历史并重新生成，不发布 |

**Stop conditions:** JIT/PAC/内存前提失败；真实 shader 无可行后端；需要上传用户 ROM/密钥才能构建；必须靠假成功或宿主占位图才能继续；需求变成免 JIT、上架或多设备。任何情况下不得提交 ROM/密钥、伪造运行证据、静默跳过关键剧情或把首屏称作完整移植。

**Est. checkpoints:** Task 2 后决定路线是否继续；Task 5 后审查真实服务规模；Task 7 后决定首版剩余范围；Task 8 后只交付有证据的首段闭环，M4 另立计划。
