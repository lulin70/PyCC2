# 安装指南 — PyCC2 **v0.5.0**

> **本文档已更新至 v0.5.0，早期版本信息见 Git 历史**

> **本指南将帮助你从零开始搭建 PyCC2 的完整开发环境。** 请按照以下步骤依次操作，遇到问题时请参考「常见问题排查」章节。

### 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.0 | 2026-06-14 | 更新至v0.4.0: 测试数~3513, 核心运行时依赖(pygame/numpy/pydantic), 启动方式 `pycc2` |
| v1.8 | 2026-05-19 | P5/P6/P7完成: 战役核心(~60%),战斗深度(~85%),内容扩展(M6-M10), CC2还原度~71%, 1566测试, 10个任务, 10张地图 |
| v1.7 | 2026-05-19 | CC2差距分析, 路线图修订为P5 Campaign Core, 夜战机制, 反坦克装甲, 天气渲染, 三语文档, 1377测试 |
| v1.6 | 2026-05-19 | P4 Week 2: 战役扩展至5个任务, 教程系统, 性能优化, 1270测试 |
| v1.5 | 2026-05-18 | P4 Week 1: GameLoop分解, 设置菜单, 安全加固, 1163测试 |
| v1.4 | 2025-05-18 | P3-Fix: 4个关键Bug修复 |
| v1.3 | 2026-05-17 | 完整版基线 |

---

## 目录

- [系统要求](#系统要求)
- [第一步：安装 Python](#第一步安装-python)
- [第二步：克隆项目仓库](#第二步克隆项目仓库)
- [第三步：创建虚拟环境](#第三步创建虚拟环境)
- [第四步：安装依赖包](#第四步安装依赖包)
- [第五步：验证安装](#第五步验证安装)
- [第六步：启动游戏](#第六步启动游戏)
- [开发环境配置（可选）](#开发环境配置可选)
- [常见问题排查](#常见问题排查)
- [平台特定说明](#平台特定说明)

---

## 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | macOS 12+ / Ubuntu 20.04+ / Windows 10+ | macOS 14+ / Ubuntu 22.04+ / Windows 11 |
| **Python** | 3.11 或更高版本 | 3.12（已充分测试） |
| **内存 (RAM)** | 4 GB | 8 GB 或以上 |
| **磁盘空间** | 500 MB（含虚拟环境与依赖） | 1 GB |
| **显示器** | 1280×720 分辨率 | 1920×1080 或更高 |

### Python 版本确认

```bash
python --version
# 输出示例: Python 3.12.3
```

> ⚠️ **注意**：PyCC2 使用了 Python 3.11 引入的 `tomllib` 模块以及 `TypeAlias` 等语法特性，因此 **不支持 Python 3.10 及更早版本**。

---

## 第一步：安装 Python

### macOS

推荐使用 [Homebrew](https://brew.sh/) 安装：

```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.12
brew install python@3.12
```

或从 [Python 官网](https://www.python.org/downloads/) 下载安装包。

### Linux (Ubuntu/Debian)

```bash
# 更新包管理器
sudo apt update

# 安装 Python 3.12 及相关工具
sudo apt install -y python3.12 python3.12-venv python3-pip python3.12-dev
```

### Windows

从 [Python 官网](https://www.python.org/downloads/) 下载安装器，安装时务必勾选 **"Add Python to PATH"** 选项。

---

## 第二步：克隆项目仓库

```bash
# 使用 Git 克隆仓库
git clone https://github.com/user/pycc2.git

# 进入项目目录
cd pycc2
```

> 如果你没有安装 Git，请先从 [git-scm.com](https://git-scm.com/) 下载安装。

---

## 第三步：创建虚拟环境

使用 Python 内置的 `venv` 模块创建隔离的虚拟环境，避免污染全局 Python 环境。

### macOS / Linux

```bash
# 创建名为 .venv 的虚拟环境
python -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

激活成功后，终端提示符前会出现 `(.venv)` 前缀：

```
(.venv) user@machine:~/pycc2$
```

### Windows (CMD)

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> ⚠️ **Windows PowerShell 用户提示**：如果执行上述命令时出现「无法加载文件」的错误，请先运行：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## 第四步：安装依赖包

PyCC2 使用 `pyproject.toml` 管理所有依赖项。我们提供两种安装模式：

### 基础安装（仅运行游戏所需）

```bash
pip install -e .
```

**核心运行时依赖**（自动安装）：

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| `pygame` | >=2.2 | 2D游戏框架（渲染、输入、SDL2音频） |
| `numpy` | >=1.26 | 数值运算（地图网格、向量计算） |
| `pydantic` | >=2.0 | 数据验证（存档文件、配置模式） |

### 开发安装（包含测试、lint、类型检查等工具）

```bash
pip install -e ".[dev]"
```

`[dev]` 额外依赖包括：

| 包名 | 用途 |
|------|------|
| `pytest` | 测试框架 |
| `pytest-cov` | 测试覆盖率报告 |
| `coverage` | 覆盖率数据收集 |
| `ruff` | 极速 Lint 与格式化工具 |
| `mypy` | 静态类型检查器 |
| `pre-commit` | Git 提交前自动检查钩子 |

### 安装过程示例输出

```
Obtaining file:///Users/lin/trae_projects/pycc2
  Installed build dependencies: ...
  Checking if build backend supports build_editable: Got requirements: ...
  Installing collected packages: numpy, pygame, pydantic, ... pycc2
Successfully installed pycc2-0.5.0 numpy-1.26.4 pygame-2.5.2 ...
```

---

## 第五步：验证安装

运行以下命令确认所有组件就绪：

```bash
# 1. 确认 PyCC2 可被正确导入
python -c "import pycc2; print(f'PyCC2 v{pycc2.__version__} 导入成功')"

# 2. 运行测试套件（需要 dev 依赖，~3513 测试）
pytest tests/ -v --tb=short

# 3. 运行代码质量检查
ruff check .
mypy src/
```

全部通过后，你的环境就已经准备就绪了！🎉

---

## 第六步：启动游戏

```bash
# 方式一：直接使用入口命令
pycc2

# 方式二：以模块方式运行
python -m pycc2.main
```

游戏窗口弹出后，你就可以开始指挥你的部队了！

---

## 开发环境配置（可选）

### 配置 VS Code（推荐）

在项目根目录下已包含 `.vscode/` 配置（如有），确保安装以下 VS Code 扩展：

- **Python** (Microsoft) — Python 语言支持
- **Pylance** — 高级代码智能提示
- **Ruff** — 实时代码检查

### 配置 pre-commit 钩子

```bash
# 安装 Git 钩子，每次提交前自动运行检查
pre-commit install
```

安装后，每次 `git commit` 时会自动执行 ruff lint、格式化、mypy 检查等操作，确保提交代码质量。

---

## 常见问题排查

### ❌ `ModuleNotFoundError: No module named 'pygame'`

**原因**：未成功安装依赖或虚拟环境未激活。

**解决方法**：
```bash
# 确认虚拟环境已激活（提示符应有 .venv 前缀）
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows

# 重新安装依赖
pip install -e ".[dev]"
```

---

### ❌ `Python version < 3.11 is not supported`

**原因**：当前 Python 版本过低。

**解决方法**：请升级到 Python 3.11+（推荐 3.12），参见[第一步](#第一步安装-python)。

---

### ❌ `SDL2 video backend not available`（macOS）

**原因**：macOS 上 Pygame 需要 SDL2 库支持。

**解决方法**：
```bash
brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf
```

---

### ❌ `Permission denied` 或 `EACCES` 错误

**原因**：尝试在没有虚拟环境的全局 Python 中安装包。

**解决方法**：始终在虚拟环境中操作。请先激活虚拟环境再执行 pip 命令。

---

### ❌ `ruff command not found`

**原因**：ruff 未安装在当前环境中，或使用了错误的终端会话。

**解决方法**：
```bash
# 确认在 .venv 环境中
which ruff
# 应输出: /path/to/pycc2/.venv/bin/ruff

# 如果没有，重新安装 dev 依赖
pip install -e ".[dev]"
```

---

### ❌ `mypy` 报告大量类型错误

**原因**：首次运行 mypy 时可能缺少类型存根（stubs）。

**解决方法**：
```bash
# 安装常用类型存根
pip install types-PyYAML types-requests

# 再次运行 mypy
mypy src/
```

---

### ❌ 游戏窗口闪退无报错

**原因**：可能是显示驱动兼容性问题或资源文件缺失。

**解决方法**：
1. 检查 `data/` 目录下的地图和单位数据文件是否完整
2. 尝试设置 SDL 驱动：
   ```bash
   export SDL_VIDEODRIVER=x11  # Linux
   export SDL_VIDEODRIVER=cocoa  # macOS
   ```
3. 在 `config/engine.toml` 中降低渲染分辨率后重试

---

## 平台特定说明

### 🍎 macOS 特别注意事项

1. **Xcode Command Line Tools** 是编译某些 Python 包的前置条件：
   ```bash
   xcode-select --install
   ```

2. **Homebrew Python vs 系统 Python**：强烈建议使用 Homebrew 安装的 Python，而非 macOS 自带的旧版系统 Python。

3. **Retina 显示屏**：Pygame 在 Retina 屏上可能出现模糊问题，可在 `config/engine.toml` 中启用高 DPI 模式。

### 🐧 Linux (Ubuntu/Debian) 特别注意事项

1. **系统依赖**：部分 Python 包需要系统级库支持：
   ```bash
   sudo apt install -y libsdl2-dev libsdl2-image-dev \
       libsdl2-mixer-dev libsdl2-ttf-dev libportaudio2 \
       libjpeg-dev libpng-dev
   ```

2. **Wayland vs X11**：如果你的桌面环境使用 Wayland，可能需要设置 `SDL_VIDEODRIVER=x11` 来避免兼容性问题。

3. **权限问题**：不要使用 `sudo pip install`，这会导致权限混乱。始终使用虚拟环境。

### 🪟 Windows 特别注意事项

1. **路径分隔符**：Windows 使用 `\` 作为路径分隔符，但在 Git Bash 或 WSL 中应使用 `/`。

2. **长路径限制**：如果项目路径过长可能导致文件操作失败，请在 PowerShell（管理员）中启用长路径支持：
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
       -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```

3. **杀毒软件干扰**：部分杀毒软件可能会误拦截 Pygame 的 DLL 文件。如遇此情况，请将项目目录加入白名单。

---

## 下一步

安装完成后，建议阅读：

- 📖 [用户手册](MANUAL_zh.md) — 学习游戏玩法与战术技巧
- 🏗️ [架构文档](docs/DESIGN.md) — 了解项目技术架构
- 📋 [需求规格](docs/PRD.md) — 查看完整功能规划

祝你指挥愉快，将军！🎖️
