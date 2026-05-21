# 🎮 PyCC2 — 近距离作战2：遥远的桥梁 (Python重制版)

**版本**: v1.8 | **测试**: ✅ **1566 通过** | **任务**: **10** | **地图**: **10**

**v0.6-p4w2 | 文档 v1.8 | 2026-05-19**

<p align="center"><em>基于 Python 的二战实时战术战斗模拟器，忠实地重现经典战术游戏</em></p>

[![CI](https://github.com/user/pycc2/actions/workflows/ci.yml/badge.svg)](https://github.com/user/pycc2/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 1566 passed](https://img.shields.io/badge/Tests-1566%20passed-brightgreen.svg)](tests/)
[![Coverage: 92.4%](https://img.shields.io/badge/Coverage-92.4%25-green.svg)](tests/)
[![Missions: 10](https://img.shields.io/badge/Missions-10-blueviolet.svg)](docs/)
[![Maps: 10](https://img.shields.io/badge/Maps-10-informational.svg)](data/)
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
| 🔒 **安全存档** | HMAC-SHA256 校验 + Pydantic 验证的双重防作弊机制 |
| 🗺️ **战役模式（5个任务）** | 贯穿市场花园行动的多关卡战役（教程→桥梁突击→坚守防线→反击→总攻），带持久化进度 |
| 📚 **教程系统** | 为新玩家提供的交互式引导教程 |
| ⚡ **性能优化** | GameLoop 分解（4组件）、改进的帧时序控制 |
| ⚙️ **设置菜单** | 游戏内配置界面（4个标签页：图形/音频/游戏/控制） |

## 技术栈

| 类别 | 技术选型 |
|------|----------|
| **语言** | Python 3.11+（推荐 3.12） |
| **图形引擎** | Pygame 2.2+ |
| **数值计算** | NumPy 1.26+ |
| **架构模式** | DDD 分层 + 六边形架构（Hexagonal Architecture） |
| **测试框架** | pytest + 覆盖率报告 |
| **质量保障** | ruff lint/format + mypy 类型检查 + pre-commit 钩子 |

**当前版本**: `v0.6-p4w2`（文档 v1.7）

### 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.6-p4w2 | 2026-05-19 | **文档 v1.8**: P5/P6/P7完成 — 战役核心(~60%),战斗深度(~85%),内容扩展(M6-M10), CC2还原度~71%, 1566测试通过, 10个任务, 10张地图 |
| v0.6-p4w2 | 2026-05-19 | **文档 v1.7**: CC2差距分析(战役~5%,战斗~65%), 路线图修订为P5 Campaign Core, 夜战机制, 反坦克装甲, 天气渲染, 三语文档(中/英/日), 1377测试通过 |
| v0.6-p4w2 | 2026-05-19 | **P4 Week 2**: 战役扩展至5个任务(M1-M5), 教程系统, 性能优化, 1270测试通过 |
| v0.5-p4w1 | 2026-05-18 | **P4 Week 1**: GameLoop分解(4组件), 设置菜单(4标签页), 安全加固, 1163测试 |
| v1.4 | 2025-05-18 | P3-Fix: 4个关键Bug修复（武器/读档/AI/入口） |
| v1.3 | 2026-05-17 | 完整版基线: 所有P0-P3功能交付, 1088测试通过 |

## 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 弹道引擎 | ✅ 已完成 | 完整的命中/穿透/伤害管线 |
| 行为树 AI | ✅ 已完成 | 包含 Blackboard 与 Selector/Sequence/Decorator |
| 战争迷雾 | ✅ 已完成 | Bresenham LOS + 动态视野更新 |
| 士气系统 | ✅ 已完成 | 多因子加权模型 |
| 存档系统 | ✅ 已完成 | HMAC-SHA256 签名 + Pydantic 校验 |
| 图形渲染 | ✅ 已完成 | 地图渲染 + 单位精灵 + HUD + 像素艺术 |
| 音效系统 | ✅ 已完成 | 程序化音频生成（零外部文件依赖） |
| 战役模式 | ✅ 已完成 | **10个任务**的完整战役系统 (M1-M10) |
| 教程系统 | ✅ 已完成 | 交互式新手引导 |
| 性能优化 | ✅ 已完成 | GameLoop分解 + 设置菜单 |
| 测试套件 | ✅ 通过 | **1566 个测试全部通过** |

## 快速开始

### 环境要求

```bash
# 推荐 Python 3.12
python --version  # >= 3.11
```

### 安装

```bash
# 克隆项目
git clone https://github.com/user/pycc2.git
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
| `鼠标左键` | 选择单位 / 移动到目标位置 |
| `鼠标右键` | 下达攻击/交互命令 |
| `鼠标滚轮` | 缩放视角 |
| `W/A/S/D` 或 方向键 | 平移摄像机 |
| `Space` | 暂停/继续游戏 |
| `Tab` | 切换单位选择 |
| `M` | 打开/关闭小地图 |
| `F1-F4` | 快捷编队选择 |
| `Esc` | 取消当前命令 |

## 项目架构

```
PyCC2/
├── src/pycc2/           # 源代码根目录
│   ├── presentation/    # Layer 1: 表现层 — 渲染/输入/UI
│   │   ├── rendering/   #   摄像机、HUD、小地图、命令栏
│   │   ├── input/       #   输入处理、快捷键、反馈
│   │   └── audio/       #   音效系统
│   ├── services/        # Layer 2: 应用服务层 — 业务编排
│   ├── domain/          # Layer 3: 领域层 — 核心业务逻辑（零外部依赖）
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

1. **领域层零依赖**：`domain/` 不引入任何框架或第三方库，确保核心逻辑纯净可测
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

## 贡献指南

欢迎提交 Issue 和 Pull Request！请遵循以下流程：

1. Fork 本仓库并创建特性分支（`git checkout -b feature/amazing-feature`）
2. 提交更改（`git commit -m 'Add some amazing feature'`）
3. 推送到分支（`git push origin feature/amazing-feature`）
4. 开启 Pull Request

代码提交前请确保通过所有 pre-commit 检查。

## 路线图

- [x] **v0.5** — 完整图形界面（地图渲染 + 单位动画 + HUD）
- [x] **v0.6** — 音效系统 + 环境音效 + 5任务战役 + 教程系统 + 夜战 + 装甲 + 天气 ✅ **当前版本**
- [ ] **v0.7** — **P5 Campaign Core**: 补齐CC2核心体验(连续战役、战略层、兵力持久化、领土控制)
- [ ] **v0.8** — 多人联机对战（本地热座优先，然后网络）
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
