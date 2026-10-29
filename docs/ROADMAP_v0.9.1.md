# PyCC2 v0.9.1 Roadmap — 阶段 1 紧急修复（用户体验优先）

> **版本**: v0.9.1 hotfix
> **创建日期**: 2026-08-01
> **状态**: 规划中 → 执行中
> **目标**: 修复 Tier 1 破坏性体验缺陷，达到真正的 Beta Candidate 标准

---

## 一、评审背景（DevSquad 7-Role 共识）

基于 v0.9.0 + E2E 盲区补齐（546→621 tests）后的用户体验评审，识别出 11 个差距，按用户感知影响重新分级为：

- **🔴 Tier 1: 破坏性体验缺陷**（3 个）— 立即修复，否则无法对外宣称 Beta Candidate
- **🟡 Tier 2: 核心玩法完整性缺陷**（4 个）— 1 个月内补齐，达到 85% 还原度
- **🟢 Tier 3: 打磨型差距**（4 个）— 延后决策，用数据驱动

**评审团队**: Product Manager（用户视角）+ Architect（技术可行性）+ Tester（质量保障）

**核心结论**: PyCC2 当前最大问题不是功能不够多，而是已有功能不够健壮（9 张地图渲染失败/音频崩溃/无战斗日志）。应该先把 Beta Candidate 做扎实（阶段 1），再谈扩展（阶段 2+）。

---

## 二、阶段 1 目标（1-2 周，16h）

### 修复范围（Tier 1 破坏性缺陷）

| 缺陷 ID | 缺陷描述 | 用户痛点 | PM 评分 | 修复成本 |
|---------|----------|----------|---------|----------|
| **P0-1** | 地图装饰渲染 bug (`decoration_renderer.py:60`) | 9 张关键地图（arnhem 桥梁战/night_map 夜战）渲染不完整，玩家打开地图直接失败 | ⚠️ 10/10 | 1h |
| **P0-2** | CombatLog 模块缺失（v0.6.x 归档到 `_archive/`） | 玩家无法复盘"为什么我输了"——无法看到伤亡明细/射击记录/命令历史，复玩价值暴降 | ⚠️ 9/10 | 8h |
| **P0-3** | 音频系统 3 个 bug | 射击无声/环境音崩溃，沉浸感归零（CC2 玩家核心诉求是"二战氛围"） | ⚠️ 8/10 | 5h |

**交付标准**: 
- 63/63 张地图 100% 可渲染
- 战斗日志面板正常显示
- 音频系统 E2E 测试 8/8 通过
- 618 E2E 零回归

---

## 三、任务分解（4 个任务）

### Task 1: 地图装饰渲染 bug 修复（1h）

**问题**: `src/pycc2/presentation/rendering/decoration_renderer.py:60` 访问 `enhanced_tile.decorations` 属性，但 9 张含 `tiles_enhanced` 字段的地图（arnhem/bridge_assault/night_map/grave/nijmegen/veghel/tutorial/road_ambush/defense_line）返回的是 **dict**，触发 `AttributeError: 'dict' object has no attribute 'decorations'`。

**方案**: 
```python
# 修复前（L60）
for deco in enhanced_tile.decorations:  # ❌ dict 无 .decorations 属性
    ...

# 修复后
decorations = enhanced_tile.get("decorations", []) if isinstance(enhanced_tile, dict) else enhanced_tile.decorations
for deco in decorations:
    ...
```

**验收标准**:
- `pytest tests/e2e/test_multi_map_gameplay_e2e.py::test_bridge_map_gameplay -x -q` 从 xfail → pass
- `pytest tests/e2e/test_multi_map_gameplay_e2e.py::test_night_map_gameplay -x -q` 从 xfail → pass
- 全量 63 张地图 `test_all_maps_load_without_crash` 零失败

**负责**: Coder
**风险**: 低（修改范围 1 行，E2E 测试覆盖充分）

---

### Task 2: CombatLog 恢复（8h）

**问题**: v0.6.x ghost 模块清理时 `combat_log.py` 归档到 `_archive/`，玩家无法查看战斗事件历史。

**方案**:
1. **不复用 archive 代码**（可能与 v0.9.0 EventBus 不兼容）
2. 新建 `src/pycc2/presentation/ui/combat_log_panel.py`（300 行）:
   - 订阅 EventBus 事件: `UnitAttacked` / `UnitDestroyed` / `CommandIssued` / `MoraleBreak` / `UnitSurrendered`
   - 维护 `_log_entries: list[LogEntry]`（最多 200 条，FIFO）
   - 渲染为 scrollable UI 面板（参考 CC2 右下角日志位置）
3. 接入 `GameLoop`: `game_loop_ui.py` 添加 `combat_log_panel.render(screen)` + `handle_scroll(event)`
4. E2E 测试: `tests/e2e/test_combat_log_e2e.py`（5 测试）:
   - `test_combat_log_records_attack_event`: 攻击事件写入日志
   - `test_combat_log_records_unit_destroyed`: 单位死亡写入日志
   - `test_combat_log_scrollable`: 日志可滚动查看
   - `test_combat_log_max_entries`: 超过 200 条时 FIFO
   - `test_combat_log_renders_without_crash`: 日志面板渲染不崩溃

**验收标准**:
- 右下角日志面板显示伤亡/射击/命令记录
- `pytest tests/e2e/test_combat_log_e2e.py -x -q` 5/5 通过
- `ruff check src/pycc2/presentation/ui/combat_log_panel.py` 0 errors

**负责**: Coder
**风险**: 中（EventBus 集成可能需要调试，但 E2E 测试可快速发现问题）

---

### Task 3: 音频系统 3 bug 修复（5h）

#### Bug 3.1: VoiceCommandSystem + SoundSystem API 不匹配（2h）

**问题**: `src/pycc2/infrastructure/audio/voice_command_system.py:56` 调用 `sound_system.play(str)`，但 `SoundSystem.play()` 期望 `SoundType` 枚举，触发 `AttributeError: 'str' object has no attribute 'name'`。

**方案**:
```python
# 修复前（voice_command_system.py:56）
sound_system.play(command_text)  # ❌ 传 str

# 修复后
from pycc2.presentation.audio.sound_system import SoundType
sound_system.play(SoundType.VOICE_COMMAND)  # ✅ 传枚举
```

#### Bug 3.2: EnvironmentalAudioSystem + stereo mixer 不兼容（2h）

**问题**: `src/pycc2/infrastructure/audio/environmental_audio.py:578` 生成 mono (1D) 数组，但若 mixer 已被 SoundSystem 初始化为 stereo，`mixer.Sound(array=raw_audio)` 抛 `ValueError: Array must be 2-dimensional`。

**方案**:
```python
# 修复前（environmental_audio.py:578）
sound = mixer.Sound(array=raw_audio)  # ❌ 1D array vs stereo mixer

# 修复后
if mixer.get_init()[2] == 2:  # stereo
    raw_audio = np.column_stack([raw_audio, raw_audio])  # mono → stereo
sound = mixer.Sound(array=raw_audio)
```

#### Bug 3.3: Tooltip HIDE_DELAY 死代码（1h）

**问题**: `src/pycc2/presentation/ui/tooltip.py` 的 `on_hover` else 分支 HIDE_DELAY(0.1s) 逻辑不可达——从 unit 切换到 None 时走 `unit != target_unit` 分支立即设 `_visible=False`。

**方案**: 删除死代码（14 行），简化逻辑。

**验收标准**:
- `pytest tests/e2e/test_audio_e2e.py -x -q` 8/8 通过（所有音频 E2E 测试通过）
- `ruff check src/pycc2/infrastructure/audio/ src/pycc2/presentation/audio/ src/pycc2/presentation/ui/tooltip.py` 0 errors

**负责**: Coder
**风险**: 低（修改范围明确，E2E 测试已覆盖）

---

### Task 4: 回归测试（2h）

**验收检查清单**:
- [ ] `pytest tests/e2e/ -q --timeout=300` 全量 E2E 通过（621 + 5 新增 = 626 passed）
- [ ] `ruff check . && ruff format --check .` 0 errors
- [ ] `./scripts/check_doc_consistency.sh` 15/15 PASS
- [ ] 手动烟雾测试: 启动游戏 → 打开 arnhem 地图 → 部署单位 → 战斗 30 秒 → 查看战斗日志 → 验证音效播放

**负责**: Tester
**风险**: 低（修改范围小，回归风险可控）

---

## 四、交付物

### v0.9.1 Hotfix Release

| 交付物 | 内容 |
|--------|------|
| **源码** | 4 个文件修改 + 1 个新文件（combat_log_panel.py） |
| **测试** | 5 个新 E2E 测试（test_combat_log_e2e.py） |
| **文档** | CHANGELOG.md 新增 v0.9.1 条目 + PROJECT_STATUS.md 更新指标 |
| **Git commit** | `fix(ux): Tier 1 用户体验缺陷修复 (P0-1/2/3)` |

### 版本指标对比

| 指标 | v0.9.0 基线 | v0.9.1 目标 |
|------|-------------|-------------|
| 还原度 | 75% | 78%（修复破坏性缺陷） |
| E2E 测试 | 621 passed / 1 skip / 2 xfail | 626 passed / 1 skip / 0 xfail |
| 玩家可玩地图 | 54/63（9 张渲染失败） | 63/63（100%） |
| 战斗日志 | ❌ 缺失 | ✅ 完整 |
| 音频系统 | ⚠️ 3 bug | ✅ 稳定 |

---

## 五、后续规划（v0.10.0）

阶段 1 完成后，进入**阶段 2: 核心补齐（1 个月，64h）**，目标 85% 还原度:

1. 建筑驻守加成（2h）
2. AI 战术深度提升（22h）
3. 战役剧情系统（36h）
4. 单位疲劳系统（4h）

详见 [ROADMAP_v0.10.0.md](ROADMAP_v0.10.0.md)（待创建）。

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| CombatLog EventBus 集成失败 | 中 | 中 | 参考现有 UI 组件（HUD/Minimap）的 EventBus 订阅模式 |
| 音频修复引入新 bug | 低 | 中 | 8 个 E2E 测试覆盖所有音频路径 |
| 地图装饰修复破坏其他地图 | 低 | 高 | 全量 63 张地图回归测试 |

---

**批准**: 待项目组评审
**执行**: DevSquad 项目生命周期模式推进
