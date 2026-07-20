# PyCC2 v0.9.0 Wave B-rev 二次共识评估归档

> **评估日期**: 2026-07-20 | **评估方法**: DevSquad V4.1.0 7-Role 并行评估 (4 subagent)
> **评估对象**: 14 项视觉打磨修订版方案 (VISUAL_POLISH_PLAN.md v2.0 + ROADMAP_v0.9.0.md v0.9.0-plan-rev1)
> **首轮参考**: [CONSENSUS_V090_WAVE_B.md](CONSENSUS_V090_WAVE_B.md) — 5 P0 Blocker + 15 P1 修改建议

---

## 一、7-Role 投票汇总

| 角色 | 投票 | 关键证据 | 否决权 |
|------|------|----------|--------|
| Architect | APPROVE_WITH_CONCERNS | 5 P0 中 3 完全解决 / 2 部分解决; V-13 API 与现有签名不匹配 (P0-B) | 无 |
| Security | APPROVE_WITH_CONCERNS | pygame.Color 可变性仅 docstring 缓解; V-14 ROUTING 闪烁 2.5Hz 无安全余量 | 无 |
| PM | APPROVE_WITH_CONCERNS | V-13/V-14 ROI 合理; V-03 calculate_mvp() kills 未归一化 (P0-1) | 无 |
| UI Designer | APPROVE_WITH_CONCERNS | V-06 ease_out_cubic 符合行业标准; V-14 "莫兰迪"色实为 Material Design 高饱和色 (P0-2) | 无 |
| Tester | APPROVE_WITH_CONCERNS | P0-4 check_doc_consistency.sh 实际未修改; V-13/V-14 测试覆盖不足 | 无 |
| DevOps | APPROVE_WITH_CONCERNS | P0-3 requirements-dev.lock 未列入 Wave C; update_perf_baseline.py 不存在 | 无 |
| Coder | APPROVE_WITH_CONCERNS | V-08/V-09/V-13/V-14 API 与现有代码不匹配 (P0-C/D/E) | 无 |

**共识结论**: 7/7 APPROVE_WITH_CONCERNS (无否决) → **通过共识门进入 Wave C**, 附 11 P0 修复条件

---

## 二、首轮 5 P0 Blocker 解决情况

| P0 # | 项目 | 状态 | 证据 |
|------|------|------|------|
| P0-1 | V-07 基线前移 Wave C2 | ✅ 已解决 | VISUAL_POLISH_PLAN.md:532, 1138; ROADMAP_v0.9.0.md:154 |
| P0-2 | F2 e2e 真实玩家旅程扩展 | ✅ 已解决 (4 条缺失旅程, P1) | VISUAL_POLISH_PLAN.md:1185-1195, 8 条旅程 |
| P0-3 | V-04 CI 冗余 + pytest-benchmark | ✅ 设计层解决 (lock 文件未明示, P0-NEW-3) | VISUAL_POLISH_PLAN.md:429-452 |
| P0-4 | check_doc_consistency.sh 扩展 | ❌ 未解决 (脚本实际未修改) | scripts/check_doc_consistency.sh:13-23 仍为 9 项 |
| P0-5 | V-03 BattleResult 类型安全 | ⚠️ 部分解决 (UnitBattleStats 与 UnitBattleRecord 重复, P0-NEW-A) | VISUAL_POLISH_PLAN.md:247, 284, 294 |

---

## 三、新发现的 11 P0 问题 (跨角色去重)

### P0-NEW-1 (PM): V-03 calculate_mvp() kills 未归一化

**位置**: VISUAL_POLISH_PLAN.md:325
**问题**: `score = hit_rate * 0.4 + stats.kills * 0.3 + survival_norm * 0.3`
- `hit_rate` ∈ [0,1] (已归一化)
- `kills` ∈ [0, ∞) (未归一化, 直接计数)
- `survival_norm` ∈ [0,1] (已归一化)
- 反例: 命中率 100% + 击杀 10 + 全程生存 → score = 0.4 + 3.0 + 0.3 = 3.7 (kills 实际权重远大于 0.3)
**影响**: MVP 严重偏向高击杀单位, 违背 CC2 玩家直觉 (支援/压制单位击杀少但贡献大)
**修复**: `kills_normalized = min(stats.kills / max(total_kills_in_battle, 1), 1.0)` 或经验值 `min(stats.kills / 10.0, 1.0)`

### P0-NEW-2 (UI Designer): V-14 "莫兰迪"色彩命名错误

**位置**: VISUAL_POLISH_PLAN.md:843-848
**问题**: 标注 "莫兰迪" 但 RGB 值实为 Material Design 高饱和色:
- WAVERING: `Color(255, 193, 7)` — 饱和度 >90%
- PINNED: `Color(255, 152, 0)` — 饱和度 >90%
- BROKEN: `Color(244, 67, 54)` — 饱和度 >90%
- 真正莫兰迪色特点: 低饱和度 + 灰调
**影响**: 违反 VISUAL_POLISH_PLAN.md:14 用户偏好 "莫兰迪色系 (舒适色彩), 反感刺眼"
**修复**:
```python
MoraleState.WAVERING: Color(212, 184, 120),   # 莫兰迪麦黄
MoraleState.PINNED: Color(196, 138, 110),      # 莫兰迪陶土橙
MoraleState.BROKEN: Color(176, 96, 88),        # 莫兰迪砖红
MoraleState.ROUTING: Color(176, 96, 88),       # 同上 + 闪烁
```

### P0-NEW-3 (Tester/DevOps): requirements-dev.lock 未列入 Wave C 行动项

**位置**: V-04 设计 (VISUAL_POLISH_PLAN.md:446-452)
**问题**: pyproject.toml 新增 `pytest-benchmark>=4.0.0` 到 dev 依赖, 但 `requirements-dev.lock` 未重新生成
**影响**: release.yml:40 和 ci.yml:34 都 `pip install -r requirements-dev.lock`, 不重新生成 CI 直接失败
**修复**: 将 `pip-compile dev > requirements-dev.lock` 列入 V-04 Wave C4 实施步骤

### P0-NEW-4 (Tester/DevOps): scripts/update_perf_baseline.py 不存在但被引用

**位置**: VISUAL_POLISH_PLAN.md:441
**问题**: `python scripts/update_perf_baseline.py --commit` 引用一个未设计的脚本
**影响**: CI 步骤失败 (FileNotFoundError)
**修复**: 补设计文档 (输入参数 / commit 行为 / 回滚机制), 或直接在 ci.yml 中 inline 实现

### P0-NEW-5 (Tester): 测试数量文档内部不一致

**位置**: VISUAL_POLISH_PLAN.md:1174 vs ROADMAP_v0.9.0.md:184, 235
**问题**: VISUAL_POLISH_PLAN 声明 "~105 新增测试", ROADMAP 声明 "N=~95 新增" — 差 10 个
**修复**: 统一为 105 (基于详细测试金字塔计算)

### P0-NEW-6 (Tester): V-13 暴击阈值约束与代码语义不一致

**位置**: VISUAL_POLISH_PLAN.md:752 (注释) vs 794 (约束)
**问题**: 注释 "is_critical: True for critical hits (>= 75% HP)" vs 约束 "暴击 (damage.amount >= 75)"
- 一处指 HP 百分比, 一处指伤害值绝对值
**修复**: 统一为绝对值 `damage.amount >= 75` (与 damage.py:54 `is_critical` property 一致)

### P0-NEW-A (Architect/Coder): V-03 UnitBattleStats 与现有 UnitBattleRecord 字段重复

**位置**: VISUAL_POLISH_PLAN.md:295-303 vs battle_result.py:41-55
**问题**: V-03 新增 `UnitBattleStats` 7 字段中 6 个与现有 `UnitBattleRecord` 重复 (unit_id/shots_fired/hits/kills/damage_dealt/damage_taken)
**影响**: 违反 DDD 单一模型原则, 数据冗余且易不一致
**修复**: V-03 复用 `UnitBattleRecord`, 仅新增 `events: list[BattleEvent]` + `mvp_unit_id: str | None` 挂到 `BattleResult`, 无需新增 `UnitBattleStats` (节省 1-2h)

### P0-NEW-B (Architect/Coder): V-13 API 与现有 CombatPopupManager.add_popup() 签名不匹配

**位置**: VISUAL_POLISH_PLAN.md:759-768 vs combat_popup.py:58-64
**问题**: 文档调用 7 个不存在的参数 (`position`/`lifetime_ms`/`font_size`/`is_damage_number`/`damage_amount`/`damage_type`)
实际签名: `add_popup(self, text: str, world_x: float, world_y: float, color: tuple = (255,255,100))`
**影响**: V-13 `add_damage_number()` 直接调用会 AttributeError, 且需重构 6 个现有调用方
**修复**: V-13 设计章节基于实际 `combat_popup.py:58-64` 签名重写

### P0-NEW-C (Coder): V-08 game_loop.pause()/resume() 方法不存在

**位置**: VISUAL_POLISH_PLAN.md:639, 643
**问题**: 在 `/Users/lin/trae_projects/PyCC2/src/pycc2` 全量搜索 `def pause|def resume` 零匹配; GameLoop 通过 `self.state.paused = True/False` 控制
**影响**: V-08 KeybindingsOverlay.show()/hide() 直接 AttributeError
**修复**: V-08 改为 `self._game_loop.state.paused = True/False` (推荐) 或在 GameLoop 新增 pause()/resume() 方法 (+0.5-1h)

### P0-NEW-D (Coder): V-09 SpriteCacheManager._factions/_unit_types/_generate_sprite 不存在 + 预热已存在

**位置**: VISUAL_POLISH_PLAN.md:689-692 vs sprite_cache_manager.py:28-475
**问题**:
1. 字段 `_factions`/`_unit_types` 不存在 (实际是 `_display_config`/`_sprite_cache` 等)
2. 方法 `_generate_sprite` 不存在 (实际是 `create_unit_sprite` + `_generate_all_sprites`)
3. 预热逻辑已在 `__init__` 中通过 `_generate_all_sprites()` 完成 (line 96)
4. 实际精灵数: 3 阵营 × 11 单位 × 8 方向 = 264 (文档说 4×8×8=256)
**影响**: V-09 prewarm() 设计 AttributeError ×3, 且功能冗余
**修复**:
1. V-09 改为: 把 `_generate_all_sprites()` 的硬编码清单提取为类常量
2. 添加 `prewarm()` 公开方法 (可选, 因为已在 `__init__` 中执行)
3. 添加预热耗时日志 (符合 Wave B-rev P1)
4. 工作量从 5h → 3h (功能已存在)

### P0-NEW-E (Coder): V-14 MoraleSystem.get_state() 类型错误 + ROUTING 状态不可达

**位置**: VISUAL_POLISH_PLAN.md:904 vs morale_system.py:97-108 + morale_types.py:71-80
**问题**:
1. `get_state()` 是 `@staticmethod`, 接受 `morale_value: int`, 不接受 `unit_id: str`
2. `resolve_morale_state()` 永远不返回 `MoraleState.ROUTING` (只返回 RALLYED/WAVERING/PINNED/BROKEN 4 种)
3. ROUTING 只能通过 `getattr(unit.morale, "_is_routing", False)` 获取
**影响**:
- V-14 调用 `morale_system.get_state(unit_id)` 类型错误
- V-14 的 ROUTING 闪烁逻辑永远不会被触发
**修复**:
```python
if getattr(unit.morale, "_is_routing", False):
    morale_state = MoraleState.ROUTING
else:
    morale_state = MoraleSystem.get_state(unit.morale.value)
```

---

## 四、新发现的 P1 问题 (跨角色去重, 13 项)

| # | 问题 | 位置 | 修复 |
|---|------|------|------|
| P1-1 | V-07 基线未覆盖 V-13/V-14 场景 + 缺雪地/水域/森林/沙地/桥梁 5 类地形基线 | VISUAL_POLISH_PLAN.md:538-544 | V-07 扩展到 7 基线 (Wave D6/D7 完成后追加 V-13/V-14 基线) |
| P1-2 | V-08 handler 冲突 (toggle vs on_key_down) + pause 异常未回滚 + resume 幂等性 | VISUAL_POLISH_PLAN.md:631-648 | 单一 handler 职责 + try/except 回滚 + pause_was_triggered_by_overlay 标记 |
| P1-3 | V-12 字体缩放未达 WCAG 2.1 AA 200% (最大 1.5) | VISUAL_POLISH_PLAN.md:1095 | FONT_SCALE_FACTORS = [0.85, 1.0, 1.5, 2.0] (4 档) 或 [0.85, 1.0, 1.25, 1.5, 2.0] (5 档) |
| P1-4 | V-10 淡入淡出 100ms 偏短 (Apple HIG 推荐 200-300ms) | VISUAL_POLISH_PLAN.md:959 | TRANSITION_MS = 200 (总切换 600ms 仍可接受) |
| P1-5 | V-14 ROUTING 闪烁 200ms (2.5Hz) 无安全余量 | VISUAL_POLISH_PLAN.md:856 | ROUTING_FLASH_INTERVAL_MS = 350 (周期 700ms ≈ 1.43Hz, 2 倍安全余量) |
| P1-6 | V-14 默认显示行为未明示 | VISUAL_POLISH_PLAN.md:916 | 默认显示所有非 RALLYED 单位徽章, 配置可关闭 |
| P1-7 | V-09 logger.info 非结构化, CI 日志难解析 | VISUAL_POLISH_PLAN.md:688, 694 | 改为 structured logging `extra={"event": "sprite_cache_prewarm", ...}` |
| P1-8 | V-04 pytest-benchmark pedantic rounds=3 过少 | VISUAL_POLISH_PLAN.md:399 | ≥10 rounds 取中位数 + p95 |
| P1-9 | V-04 perf_baseline.json 持久化策略未明示 | VISUAL_POLISH_PLAN.md:386 | git 提交到 tests/benchmark/baselines/ + 仅 workflow_dispatch 允许更新 |
| P1-10 | V-07 ci.yml 当前无 schedule trigger, 需新增 | ci.yml | 新增 `schedule: - cron: '0 6 * * 1'` |
| P1-11 | F2 缺失 4 条旅程 (V-05/V-06/V-09/V-11) | VISUAL_POLISH_PLAN.md:1187-1194 | 补充第 9 条: 高分辨率屏幕玩家旅程 |
| P1-12 | V-01 ThemeManager register 接口需所有渲染器配合 (+2-3h) | VISUAL_POLISH_PLAN.md:161-179 | 工作量上调 V-01: 10-12h → 12-14h |
| P1-13 | 工作量从 88h 上调到 92-95h | ROADMAP_v0.9.0.md:78 | V-08 +1h / V-13 +2h / V-14 +1-2h / V-01 +2h / V-03 -1-2h / V-09 -2h ≈ +4-7h |

---

## 五、Wave B-rev 行动计划

### Wave C 启动前必修 (24h 内完成, 5 项 P0)

1. ✅ **修复 P0-4**: 修改 `scripts/check_doc_consistency.sh:13-23` 追加 3 项 v0.9.0 文档:
   - `docs/VISUAL_POLISH_PLAN.md`
   - `docs/ROADMAP_v0.9.0.md`
   - `docs/VISUAL_OPTIMIZATION_UNIFIED.md`
2. ✅ **修复 P0-NEW-5**: 同步 VISUAL_POLISH_PLAN.md:1174 与 ROADMAP_v0.9.0.md:184, 235 测试数量为 105
3. ✅ **修复 P0-NEW-6**: 统一 V-13 暴击阈值为绝对值 `damage.amount >= 75` (与 damage.py:54 一致)
4. ✅ **修复 P0-NEW-3**: 将 `pip-compile dev > requirements-dev.lock` 列入 V-04 Wave C4 实施步骤
5. ✅ **修复 P0-NEW-4**: 补 `scripts/update_perf_baseline.py` 设计或 inline 实现

### Wave C5 (V-03) 实施前必修 (2 项 P0)

6. ✅ **修复 P0-NEW-A**: V-03 复用现有 `UnitBattleRecord` 而非新增 `UnitBattleStats` (节省 1-2h)
7. ✅ **修复 P0-NEW-1**: V-03 `calculate_mvp()` kills 归一化

### Wave D3 (V-08) 实施时修复 (1 项 P0 + 1 项 P1)

8. ✅ **修复 P0-NEW-C**: V-08 改用 `game_loop.state.paused = True/False`
9. ✅ **修复 P1-2**: V-08 handler 单一职责 + pause 异常回滚

### Wave D4 (V-09) 实施时修复 (1 项 P0 + 1 项 P1)

10. ✅ **修复 P0-NEW-D**: V-09 复用现有 `_generate_all_sprites()`, 工作量 5h → 3h
11. ✅ **修复 P1-7**: V-09 logger.info 改为结构化日志

### Wave D6 (V-13) 实施前必修 (1 项 P0)

12. ✅ **修复 P0-NEW-B**: V-13 设计章节基于实际 `combat_popup.py:58-64` 签名重写

### Wave D7 (V-14) 实施时修复 (2 项 P0 + 2 项 P1)

13. ✅ **修复 P0-NEW-2**: V-14 色彩改用真正莫兰迪低饱和度色板
14. ✅ **修复 P0-NEW-E**: V-14 新增 ROUTING 检测逻辑
15. ✅ **修复 P1-5**: V-14 ROUTING 闪烁间隔 200ms → 350ms
16. ✅ **修复 P1-6**: V-14 默认显示所有非 RALLYED 单位徽章

### Wave E (V-12) 实施时修复 (1 项 P1)

17. ✅ **修复 P1-3**: V-12 字体缩放 4 档 [0.85, 1.0, 1.5, 2.0] (达 WCAG 2.1 AA 200%)

### Wave E (V-10) 实施时修复 (1 项 P1)

18. ✅ **修复 P1-4**: V-10 TRANSITION_MS = 100 → 200

---

## 六、关键证据链

### V-13 API 不匹配证据 (P0-NEW-B)

实际签名 (combat_popup.py:58-64):
```python
def add_popup(self, text: str, world_x: float, world_y: float,
              color: tuple[int, int, int] = (255, 255, 100)) -> None:
```

文档调用 (VISUAL_POLISH_PLAN.md:759-768):
```python
self.add_popup(
    text=text, position=target_position, color=color,
    lifetime_ms=1200, font_size=font_size,
    is_damage_number=True, damage_amount=damage.amount,
    damage_type=damage.damage_type,
)
```

不匹配参数: `position` (应为 `world_x`/`world_y`), `lifetime_ms` (应为 `duration`), `font_size`, `is_damage_number`, `damage_amount`, `damage_type` (6 个不存在参数)

### V-14 ROUTING 不可达证据 (P0-NEW-E)

`resolve_morale_state()` (morale_types.py:71-80):
```python
def resolve_morale_state(morale_value: int) -> MoraleState:
    if morale_value > RALLYED_THRESHOLD:   # >70
        return MoraleState.RALLYED
    elif morale_value > WAVERING_THRESHOLD:  # >40
        return MoraleState.WAVERING
    elif morale_value > PINNED_THRESHOLD:    # >20
        return MoraleState.PINNED
    else:                                    # ≤20
        return MoraleState.BROKEN
    # 永远不返回 MoraleState.ROUTING
```

### V-14 "莫兰迪"色实为 Material Design 证据 (P0-NEW-2)

VISUAL_POLISH_PLAN.md:843-848:
```python
MoraleState.WAVERING: Color(255, 193, 7),   # 标注 "莫兰迪黄" (实为 Material Yellow 700)
MoraleState.PINNED: Color(255, 152, 0),     # 标注 "莫兰迪橙" (实为 Material Orange 700)
MoraleState.BROKEN: Color(244, 67, 54),     # 标注 "莫兰迪红" (实为 Material Red 500)
```

饱和度计算:
- `Color(255, 193, 7)`: S = 255/255 = 100% (高饱和)
- `Color(255, 152, 0)`: S = 255/255 = 100% (高饱和)
- `Color(244, 67, 54)`: S = 244/244 = 100% (高饱和)

真正莫兰迪色饱和度参考:
- 莫兰迪黄: RGB(193, 168, 100), S ≈ 48%
- 莫兰迪橙: RGB(200, 130, 100), S ≈ 35%
- 莫兰迪红: RGB(180, 100, 90), S ≈ 44%

---

## 七、教训强化 (在首轮 5 条基础上新增 2 条)

### 教训 6 (Wave B-rev): 文档设计的 API 调用必须基于实际代码签名核对

**现象**: V-08/V-09/V-13/V-14 设计文档中调用了 9 个不存在的 API (game_loop.pause/resume, _factions/_unit_types/_generate_sprite, add_popup 6 个不存在参数, get_state(unit_id))
**根因**: 凭记忆/假设设计 API, 未实际读取代码签名
**预防**: 文档设计阶段必须并行 Read 相关源码, API 调用必须引用具体行号作为证据
**强化措施**: Wave C-E 实施时, 每个 V-xx 章节实施前 Coder 角色必须再次核对 API 签名

### 教训 7 (Wave B-rev): 色彩命名需要校验饱和度, 高饱和度色彩不是莫兰迪色

**现象**: V-14 标注 "莫兰迪黄/橙/红" 但实际 RGB 是 Material Design 标准色, 饱和度 100%
**根因**: 对莫兰迪色系特点理解不足 (莫兰迪 = 低饱和度 + 灰调, 不是任意色彩都可命名 "莫兰迪")
**预防**: 莫兰迪色彩设计必须计算饱和度 (S < 50% 才算莫兰迪), 并与 Material Design 标准色比对
**强化措施**: V-14 实施时 UI Designer 角色必须提供 RGB + HSV 双重数值, 验证 S < 50%

---

## 八、下一步

1. ✅ **本归档文档已创建** (CONSENSUS_V090_WAVE_B_REV.md)
2. ⏳ **整合 11 P0 修复清单到 VISUAL_POLISH_PLAN.md** (Wave B-rev 收尾)
3. ⏳ **整合 P1 修改建议到 ROADMAP_v0.9.0.md** (Wave 清单更新)
4. ⏳ **通知用户决策**: 是否进入 Wave C (用户已说"先做方案，让DevSquad团队达成共识后推进", 共识已达成 7/7)

---

**归档完成时间**: 2026-07-20 | **归档人**: DevSquad V4.1.0 7-Role 共识机制 | **共识门状态**: ✅ 通过 (附 11 P0 修复条件)
