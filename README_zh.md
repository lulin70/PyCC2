# 🎮 PyCC2 — 近距离作战2：遥远的桥梁 (Python重制版)

**版本**: v0.3.0 | **测试**: ✅ **3334 通过** | **地图**: **63** | **战斗**: **29**

**v0.3.0 | 文档 v2.0 | 2026-05-27**

<p align="center"><em>基于 Python 的二战实时战术战斗模拟器，忠实地重现经典战术游戏</em></p>

[![CI](https://github.com/user/pycc2/actions/workflows/ci.yml/badge.svg)](https://github.com/user/pycc2/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 3334 passed](https://img.shields.io/badge/Tests-3334%20passed-brightgreen.svg)](tests/)
[![CC2 Fidelity: ~95%](https://img.shields.io/badge/CC2%20Fidelity-%E2%88%BC95%25-brightgreen.svg)](docs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 关于本项目

PyCC2 是对经典二战战术游戏 **Close Combat 2: A Bridge Too Far** 的 Python 重制版，以 1944 年 **市场花园行动**（Operation Market Garden）为历史背景。你将指挥盟军连排级部队，在荷兰的桥梁、城镇与田野中与德军展开殊死搏斗。

本项目采用 **领域驱动设计（DDD）** 架构，结合 **Behavior Tree AI**、真实弹道计算与动态士气系统，致力于还原原作那令人窒息的战术深度与战场沉浸感。

### 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 **真实弹道系统** | 基于物理的弹道计算，包含距离衰减、掩体穿透与散布模型 |
| 🧠 **AI 行为树** | 完整的 BT 框架驱动敌方战术决策，支持多层级协同 |
| 🌫️ **战争迷雾** | 动态视野系统 + Bresenham 视线算法，所见即所得 |
| ⚔️ **士气系统** | 基于伤亡、指挥官阵亡、侧翼暴露等因子的动态士气模型 |
| 🏢 **建筑驻守** | 单位进入建筑获得防御加成，窗户限制射击弧度 |
| 💥 **桥梁摧毁** | 工兵可炸毁桥梁，形成不可通过的水域缺口 |
| 🏆 **CC2原版胜利条件** | 即时VL占领、20分钟战斗计时器、积分制评分 |
| ⌨️ **7个命令热键** | Z(快速移动)/X(潜行)/S(射击)/C(烟雾)/V(移动)/D(防御)/H(隐藏) |
| 📋 **命令队列** | Shift+右键排队多个命令 |
| 🔭 **部署LOS预览** | 部署时预览视线范围 |
| ⚖️ **阵营难度不对称** | 各阵营不同经验/补给等级(新兵/老兵/精英/尖子) |
| 🗺️ **战役日简报** | 每个战役日开始时的战略地图概览 |
| 🔄 **战斗间单位继承** | 存活单位在战役战斗间持续存在 |
| 📊 **战役结束画面** | 最终战斗后的战役结果总结 |
| 🎨 **增强视觉** | 改进地形纹理、坦克炮塔旋转、受伤视觉、方向性倒下死亡动画、环境光影 |
| 🔒 **安全存档** | HMAC-SHA256 校验 + Pydantic 验证的双重防作弊机制 |
| 📚 **教程系统** | 为新玩家提供的交互式引导教程 |

## 技术栈

| 类别 | 技术选型 |
|------|----------|
| **语言** | Python 3.11+（推荐 3.12） |
| **图形引擎** | Pygame 2.2+ |
| **数值计算** | NumPy 1.26+ |
| **架构模式** | DDD 分层 + 六边形架构（Hexagonal Architecture） |
| **测试框架** | pytest + 覆盖率报告 |
| **质量保障** | ruff lint/format + mypy 类型检查 + pre-commit 钩子 |

**当前版本**: `v0.3.0`

### 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.3.0 | 2026-05-27 | CC2原版胜利条件、7命令热键、命令队列、工兵炸桥、建筑驻守、部署LOS预览、阵营难度不对称、战役日简报、单位继承、战役结束画面、增强视觉(地形纹理/炮塔旋转/死亡动画/光影)、CC2还原度~95%、3334测试通过、63地图、3战区29战斗9天 |
| v0.2.0 | 2026-05-26 | PS-01→PS-12功能里程碑完成、63地图、~90% CC2还原度、3325测试通过 |
| v0.1.1 | 2026-05-23 | M1紧急修复：P0-1/P0-2/P0-3/P0-4已修复，2767测试 |
| v0.6-p4w2 | 2026-05-19 | 战役核心(~60%)、战斗深度(~85%)、内容扩展、CC2还原度~71%、3325测试 |
| v0.5-p4w1 | 2026-05-18 | GameLoop分解、设置菜单、安全加固、1163测试 |

## 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 弹道引擎 | ✅ 已完成 | 完整的命中/穿透/伤害管线 |
| 行为树 AI | ✅ 已完成 | 包含 Blackboard 与 Selector/Sequence/Decorator |
| 战争迷雾 | ✅ 已完成 | Bresenham LOS + 动态视野更新 |
| 士气系统 | ✅ 已完成 | 多因子加权模型 |
| 胜利条件 | ✅ 已完成 | CC2原版：即时VL占领、20分钟计时器、积分制 |
| 命令系统 | ✅ 已完成 | 7个命令热键 (Z/X/S/C/V/D/H) + 命令队列 |
| 建筑驻守 | ✅ 已完成 | 防御加成 + 窗户射击弧度限制 |
| 桥梁摧毁 | ✅ 已完成 | 工兵可炸毁桥梁 |
| 阵营难度 | ✅ 已完成 | 不对称经验/补给等级 |
| 战役继承 | ✅ 已完成 | 战斗间单位持续存在 |
| 战役日简报 | ✅ 已完成 | 战略地图概览 |
| 战役结束画面 | ✅ 已完成 | 战役结果总结 |
| 部署LOS预览 | ✅ 已完成 | 部署时预览视线 |
| 存档系统 | ✅ 已完成 | HMAC-SHA256 签名 + Pydantic 校验 |
| 图形渲染 | ✅ 已完成 | 地图渲染 + 单位精灵 + HUD + 像素艺术 + 阴影 |
| 音效系统 | ✅ 已完成 | 程序化音频生成（零外部文件依赖） |
| 死亡动画 | ✅ 已完成 | 方向性倒下动画 |
| 测试套件 | ✅ 通过 | **3334 个测试全部通过** |

## 快速开始

### 环境要求

```bash
# 推荐 Python 3.12
python --version  # >= 3.11
```

### 安装

```bash
# 克隆项目
git clone https://github.com/lulin70/PyCC2.git
cd pycc2

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖（含开发工具）
pip install -e ".[dev]"
```

### 启动游戏

```bash
pycc2
# 或
python -m pycc2.main
```

### 操作说明

| 按键/操作 | 功能 |
|-----------|------|
| `鼠标左键` | 选择单位 |
| `鼠标右键拖拽` | 命令径向菜单 / 快捷键 (Z/X/S/C/V/D/H) |
| `Shift+左键` | 多选单位 |
| `Shift+右键` | 队列命令 |
| `W/A/S/D` 或 方向键 / 边缘滚动 | 平移摄像机 |
| `鼠标滚轮` | 缩放视角 |
| `ESC`（菜单）/ `Space`（时间控制） | 暂停 |
| `Ctrl`（按住） | 视线检查 |

## 项目架构

```
PyCC2/
├── src/pycc2/           # 源代码根目录
│   ├── presentation/    # Layer 1: 表现层 — 渲染/输入/UI
│   │   ├── rendering/   #   摄像机、HUD、小地图、命令栏
│   │   ├── input/       #   输入处理、快捷键、反馈
│   │   └── audio/       #   音效系统
│   ├── services/        # Layer 2: 应用服务层 — 业务编排
│   ├── domain/          # Layer 3: 领域层 — 核心业务逻辑（基本无框架依赖）
│   │   ├── entities/    #   游戏实体：Squad, Unit, GameMap, Projectile
│   │   ├── components/  #   ECS 组件：Health, Morale, Position, Weapon, Vision
│   │   ├── systems/     #   核心系统：弹道、战斗解析、士气、路径规划
│   │   ├── ai/          #   AI 系统：行为树、感知、战术决策
│   │   └── value_objects/#   值对象：Damage, Direction, TerrainType, Vec2
│   ├── repositories/    # Layer 4: 仓储接口层 — 数据访问抽象
│   └── infra/           # Layer 5: 基础设施层 — 配置、文件 I/O
├── config/              # 引擎配置 (engine.toml) 与日志配置
├── data/                # 游戏数据：地图 JSON、单位定义、音效资源
├── tests/               # 测试套件（pytest）
├── saves/               # 用户存档目录
├── scripts/             # 辅助脚本
└── docs/                # 设计文档（PRD/ADD/DESIGN/DATA_DESIGN 等）
```

### 架构原则

1. **领域层基本无框架依赖**：`domain/` 大部分为纯 Python（少量遗留代码有 numpy/pygame 引用），核心逻辑可测
2. **依赖倒置**：通过 Protocol/ABC 定义仓储接口，具体实现在基础设施层注入
3. **单一职责**：每个模块只做一件事，边界清晰
4. **可测试性**：所有核心逻辑可通过纯单元测试验证，无需 mock 图形层

## 开发指南

### 代码质量检查

```bash
# Lint 检查
ruff check .

# 自动格式化
ruff format .

# 静态类型检查
mypy src/

# 运行测试套件
pytest tests/ -v

# 一键运行所有检查（pre-commit 钩子）
pre-commit run --all-files
```

### 运行测试

```bash
# 全量测试
pytest tests/ -v --cov=src/pycc2 --cov-report=term-missing

# 仅运行弹道相关测试
pytest tests/ -v -k "ballistic"

# 仅运行 AI 相关测试
pytest tests/ -v -k "behavior or ai"
```

## 文档索引

| 文档 | 说明 | 优先级 |
|------|------|--------|
| [PRD.md](docs/PRD.md) | 产品需求规格说明书 | P1 |
| [ADD.md](docs/ADD.md) | 架构设计文档 | P2 |
| [DESIGN.md](docs/DESIGN.md) | 技术设计文档 | P3 |
| [DATA_DESIGN.md](docs/DATA_DESIGN.md) | 数据设计文档 | P4 |
| [SECURITY.md](docs/SECURITY.md) | 安全设计文档 | — |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | 测试计划 | — |
| [VISUAL_SPEC.md](docs/VISUAL_SPEC.md) | 视觉规格说明 | — |
| [CC2_GAP_ANALYSIS_AND_PLAN.md](docs/CC2_GAP_ANALYSIS_AND_PLAN.md) | CC2还原度差距分析 | — |

## 贡献指南

欢迎贡献！请在 GitHub 上提交 Issue 或 Pull Request。

## 路线图

- [x] **v0.5** — 完整图形界面（地图渲染 + 单位动画 + HUD）
- [x] **v0.6** — 音效系统 + 环境音效 + 战役系统 + 教程系统
- [x] **v0.2.0** — PS-01→PS-12里程碑完成、63地图、~90% CC2还原度、3325测试
- [x] **v0.3.0** — CC2原版胜利条件、命令热键/队列、炸桥/驻守、战役继承/简报/结束、增强视觉、~95% CC2还原度、3334测试 ✅ **当前版本**
- [ ] **v0.4** — 视觉打磨（命令队列UI、车辆损伤视觉、烟雾粒子效果）
- [ ] **v0.5** — 架构改进（领域层瘦身、大文件拆分、统一单位定义、清理技术债）
- [ ] **v0.6** — 多人联机对战（本地热座优先，然后网络）
- [ ] **v1.0** — 正式发布版本

## 许可证

本项目基于 [MIT License](LICENSE) 开源发布。

---

## 致谢

> *"在战争游戏中，每一个像素都承载着历史的重量。"*

本项目的灵感源自 Atomic Games 于 1997 年发行的传奇作品 **Close Combat 2: A Bridge Too Far**。那款游戏以其开创性的实时战术机制、真实的士兵行为模拟和令人屏息的战场氛围，深深影响了一代战术游戏开发者。

我们向原作致敬，也向每一位在市场花园行动中英勇作战的士兵致敬——无论是盟军空降兵在阿纳姆的顽强坚守，还是德军装甲部队在菲赫尔的拼死反击。历史不应被遗忘，而最好的纪念方式，就是用代码让那段历史在屏幕上重新鲜活起来。

**特别感谢：**
- Close Combat 系列的原作者团队（Atomic Games）
- Python 社区提供的卓越工具链（Pygame、NumPy、Pydantic……）
- 所有为本项目贡献代码、建议与反馈的开发者

---

*最后更新: 2026-05-27 | 版本: v0.3.0 | CC2还原度: ~95% | 3334 tests passing*
