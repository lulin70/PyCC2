# PyCC2 技术债清单

> **版本**: v0.3.0 | **日期**: 2026-05-28 | **原则**: 不留技术债，发现即记录，按计划清理
> **上次核查**: 2026-05-28 (v0.3.0 7-dimension review后更新) | **P0未解决**: 0 | **P1未解决**: 3 | **P2未解决**: 10
> **状态**: ✅ P0全部清除 | ✅ TD-045~TD-049已解决 | 🆕 新增3项7-dimension review发现 (TD-050~TD-052)

---

## 一、技术债总览

| 类别 | 数量 | 严重程度 | 清理状态 |
|------|------|---------|---------|
| 🔴 P0 致命（游戏不可玩） | 0 | — | ✅ 全部清除 |
| 🟡 P1 严重（功能受损） | 3 | 🟡 严重 | ❌ 未解决 |
| 🟢 P2 中等（质量/维护） | 10 | 🟢 中等 | ❌ 未解决 |
| ~~M2新增发现 (TD-045~049)~~ | 5 | — | ✅ 已解决 |
| 🆕 7-dimension review新增 | 3 | 🟡 P1+P2 | ❌ 未解决 |
| v2.0旧条目（声称已解决） | 20 | — | ⚠️ 待验证 |
| **合计（活跃）** | **16** | — | **13/34 已解决** |

---

## 二、P0 致命技术债（游戏不可玩）— ✅ 全部已清除

### ~~🔴 TD-021: Unit缺少display_name属性~~ ✅ 已修复 (2026-05-23)

- **描述**: Unit类未定义display_name属性，cc2_bottom_panel渲染时直接访问unit.display_name触发AttributeError
- **影响**: 底部面板渲染崩溃，无法显示任何单位信息，游戏不可玩
- **文件**: `src/pycc2/domain/entities/unit.py`, `src/pycc2/presentation/ui/cc2_bottom_panel.py`
- **状态**: ✅ 已修复 — 在Unit类中添加了display_name属性
- **修复日期**: 2026-05-23

### ~~🔴 TD-022: HealthComponent/MoraleComponent属性名不匹配~~ ✅ 已修复 (2026-05-23)

- **描述**: 组件暴露的属性名（如current_health/morale_value）与调用方期望的属性名（如hp/morale）不一致
- **影响**: 战斗结算崩溃，单位受伤/士气变化无法执行，游戏不可玩
- **文件**: `src/pycc2/domain/components/health_component.py`, `src/pycc2/domain/components/morale_component.py`
- **状态**: ✅ 已修复 — 添加了current/max property别名
- **修复日期**: 2026-05-23

### ~~🔴 TD-023: AttackNearestAI/MoveToObjectiveAI导入失败~~ ✅ 已修复 (2026-05-23)

- **描述**: AI行为类文件路径或类名与import语句不匹配，运行时ImportError
- **影响**: AI系统完全瘫痪，敌方无法行动，游戏不可玩
- **文件**: AI行为模块及引用处
- **状态**: ✅ 已修复 — 修正了import路径和类名
- **修复日期**: 2026-05-23

### ~~🔴 TD-024: set_mode()不支持fast/sneak参数~~ ✅ 已修复 (2026-05-24)

- **描述**: InteractionController.set_mode()仅接受字符串枚举，不接受fast/sneak等CC2原版移动模式参数
- **影响**: 移动模式命令不可操作，玩家无法切换行军/潜行模式
- **文件**: `src/pycc2/presentation/input/interaction_controller.py`
- **状态**: ✅ 已修复 — set_mode()已扩展支持fast/sneak参数
- **修复日期**: 2026-05-24

### ~~🔴 TD-025: 旧UI组件文件未清理~~ ✅ 已修复 (2026-05-25)

- **描述**: 旧版UI组件文件残留在代码库中，与新UI系统冲突，导致渲染冲突和ImportError
- **影响**: UI层不稳定，渲染冲突
- **状态**: ✅ 已修复 — 清理了旧版UI组件文件

---

## 三、P1 严重技术债（功能受损）

### 🟡 TD-026: 29个文件超过500行

- **描述**: 代码库中有29个文件超过500行，最大文件超过1000行，违反单一职责原则
- **影响**: 代码难以维护和理解，修改风险高
- **状态**: ❌ 未解决
- **清理方案**: 按模块拆分大文件，每个文件控制在500行以内

### 🟡 TD-027: infra/infrastructure职责重叠

- **描述**: infra/和infrastructure/两个目录存在职责重叠，模块边界不清晰
- **影响**: 开发者不确定新代码应放在哪个目录，导致代码组织混乱
- **状态**: ❌ 未解决
- **清理方案**: 合并或明确划分infra/和infrastructure/的职责边界

### ~~🟡 TD-028: integration测试仅1个~~ ✅ 已修复 (2026-05-24)

- **描述**: 2762个测试中仅有1个集成测试，其余均为单元测试，无法验证模块间协作
- **影响**: 模块间接口断裂无法被测试发现
- **状态**: ✅ 已修复 — 新增6个集成测试文件(LOS/部署/命令/渲染/胜负/战斗循环)，总计3020+测试通过
- **修复日期**: 2026-05-24

### 🟡 TD-029: 视觉优化文档4个重叠

- **描述**: 存在4个视觉优化相关文档，内容重叠，缺乏统一规划
- **影响**: 视觉优化工作缺乏明确方向，可能重复劳动
- **状态**: ❌ 未解决
- **清理方案**: 合并为1个统一的视觉优化文档

### ~~🟡 TD-030: 音频stereo预生成失败~~ ✅ 已修复 (2026-05-24)

- **描述**: 程序化音效系统的stereo预生成功能失败，导致音效无法正常播放
- **影响**: 游戏实际无声
- **文件**: `src/pycc2/presentation/audio/sound_system.py`
- **状态**: ✅ 已修复 — 添加_make_sound()方法自动mono→stereo转换，添加距离衰减
- **修复日期**: 2026-05-24

### ~~🟡 TD-031: POLISH阵营被排除在友军列表外~~ ✅ 已解决 (v0.3.7)

- **描述**: POLISH阵营（波兰第1独立伞兵旅）被错误地排除在友军列表外
- **影响**: 波兰单位在战役中无法获得友军支援，不符合历史事实
- **状态**: ✅ **已解决** — `skirmish_generator.py:445` 已包含 `Faction.POLISH` 在 `_allied_factions()` 中；`hud_manager.py:355` 也正确识别 POLISH 为友军
- **修复日期**: 2026-05-31 (v0.3.7 技术债清理)

### ~~🟡 TD-032: GameSettings类型注解未导入~~ ✅ 已解决 (v0.3.7)

- **描述**: GameSettings相关模块使用了类型注解但未正确导入，导致类型检查失败
- **影响**: 类型安全受损，IDE提示不正确，可能隐藏运行时错误
- **状态**: ✅ **已解决** — `game_settings.py` 正确使用 `TYPE_CHECKING` 模式（L20, L22-L26），所有类型注解导入均在 `if TYPE_CHECKING:` 块内
- **修复日期**: 2026-05-31 (v0.3.7 审计确认)

---

## 四点五、等距投影新增技术债 (2026-05-24)

### 🟢 TD-042: PixVoxel CC0精灵资源未下载集成

- **描述**: PixVoxel Revised Isometric精灵(CC0, 35单位+7设施)下载脚本已就绪，但网络慢(28.8MB)未完成下载
- **影响**: 等距模式仍使用程序化生成的简单精灵，视觉还原度不足
- **文件**: `scripts/download_pixvoxel_assets.py`, `src/pycc2/presentation/rendering/pixvoxel_loader.py`
- **状态**: ❌ 未解决 (下载脚本就绪，需手动执行)
- **清理方案**: 在网络良好时执行 `python scripts/download_pixvoxel_assets.py`

### 🟢 TD-043: 等距渲染性能未优化

- **描述**: IsometricRenderer每帧重新生成所有可见瓦片，无脏矩形优化，大地图可能卡顿
- **影响**: 100×100地图等距模式帧率可能低于30 FPS
- **文件**: `src/pycc2/presentation/rendering/isometric_renderer.py`
- **状态**: ❌ 未解决
- **清理方案**: 实现瓦片缓存+脏矩形渲染+精灵批处理

### 🟢 TD-044: 等距模式默认仍为ORTHOGRAPHIC

- **描述**: Camera默认projection=ORTHOGRAPHIC，等距模式需手动按I键切换
- **影响**: 用户首次启动看不到等距效果
- **文件**: `src/pycc2/presentation/rendering/camera.py`
- **状态**: ❌ 未解决 (Phase 3计划)
- **清理方案**: 等距渲染稳定后切换默认为ISOMETRIC

---

## 四点七、M2新增技术债 (2026-05-27)

### ~~🟡 TD-045: Domain→Presentation层违规（BUILDING_WINDOWS）~~ ✅ 已修复 (2026-05-28)

- **描述**: `game_map.py`（Domain层）中定义了`BUILDING_WINDOWS`常量，这是Presentation层的渲染概念，违反了DDD分层架构原则。Domain层不应包含与视觉呈现相关的常量。
- **影响**: 层级耦合，Domain层修改可能因Presentation需求而被迫变更，降低可测试性和可维护性
- **文件**: `src/pycc2/domain/entities/game_map.py`
- **状态**: ✅ 已修复 — BUILDING_WINDOWS已移至Presentation层
- **修复日期**: 2026-05-28

### ~~🟡 TD-046: 重复士气模块（morale_sys.py vs morale_system.py）~~ ✅ 已修复 (2026-05-28)

- **描述**: 存在两个士气相关模块：`morale_sys.py`和`morale_system.py`，功能重叠，接口不一致，调用方不确定应使用哪个
- **影响**: 代码重复、维护成本翻倍、接口不一致可能导致行为差异
- **文件**: `src/pycc2/domain/systems/morale_sys.py`, `src/pycc2/domain/systems/morale_system.py`
- **状态**: ✅ 已修复 — 合并为单一士气模块，更新所有引用方
- **修复日期**: 2026-05-28

### ~~🟡 TD-047: 68个bare except块~~ ✅ 已修复 (2026-05-28)

- **描述**: 代码库中存在68个`except:`或`except Exception:`裸捕获块，吞掉所有异常而不记录或处理，隐藏真实Bug
- **影响**: 异常被静默吞掉，Bug难以定位和调试，可能导致数据不一致
- **文件**: 分布于多个模块
- **状态**: ✅ 已修复 — 替换为具体异常类型，添加日志记录
- **修复日期**: 2026-05-28

### ~~🟢 TD-048: quick_implementations.py位于Domain层~~ ✅ 已修复 (2026-05-28)

- **描述**: `quick_implementations.py`文件位于Domain层，包含快速实现的功能代码，这些代码绕过了正常的领域建模流程，缺乏测试和设计文档
- **影响**: Domain层代码质量参差不齐，快速实现代码可能包含未验证的逻辑
- **文件**: `src/pycc2/domain/quick_implementations.py`
- **状态**: ✅ 已修复 — 审查并重构到正式领域模块中，删除临时文件
- **修复日期**: 2026-05-28

### ~~🟢 TD-049: infra/ vs infrastructure/ 包重复~~ ✅ 已修复 (2026-05-28)

- **描述**: 同时存在`src/pycc2/infra/`和`src/pycc2/infrastructure/`两个包，职责重叠，开发者不确定新代码应放在哪个包中
- **影响**: 代码组织混乱，同一类型的功能分散在两个包中，增加维护成本
- **文件**: `src/pycc2/infra/`, `src/pycc2/infrastructure/`
- **状态**: ✅ 已修复 — 合并为单一`infrastructure/`包，更新所有import引用
- **修复日期**: 2026-05-28

---

## 四点八、7-dimension Review新增技术债 (2026-05-28)

### ~~🟡 TD-050: Domain→Infrastructure层违规（morale_system.py导入voice_commands）~~ ✅ 已解决 (v0.3.9 审计确认)

- **描述**: `morale_system.py`（Domain层）原本被认为导入了`voice_commands`模块
- **审计结果**: ✅ **实际已符合架构规范** — 使用回调函数模式 (`voice_callback: Callable`) 解耦，无直接导入
- **文件**: `src/pycc2/domain/systems/morale_system.py`
- **状态**: ✅ **误报清除** — 代码审查确认 Domain 层正确使用依赖注入，未违反分层原则
- **修复日期**: 2026-05-31 (v0.3.9 架构审计)

### ~~🟡 TD-051: Domain→Services层违规（7处导入EventBus/RandomContext）~~ ✅ 已解决 (v0.3.9 审计确认)

- **描述**: 原本认为 Domain 层有 7 处直接导入 Services 层的 EventBus 和 RandomContext
- **审计结果**: ✅ **实际已符合架构规范** — 全面搜索确认 Domain 层**零直接导入** EventBus 或 RandomContext
- **影响范围**: 无（问题不存在）
- **状态**: ✅ **误报清除** — 代码审查确认所有导入均已正确使用 TYPE_CHECKING 或依赖注入
- **修复日期**: 2026-05-31 (v0.3.9 架构审计)

### ✅ TD-052: enhanced_renderer.py过大 (v0.3.9: 2521行, 重构中)

- **描述**: `enhanced_renderer.py`文件原约5975行(v0.3.4)，经v0.3.5-v0.3.9六次提取后降至**2521行(-58%)**，仍超500行上限
- **影响**: 代码维护性持续改善中，已拆分出6个独立模块
- **文件**: `src/pycc2/presentation/rendering/enhanced_renderer.py`
- **状态**: 🔄 **进行中** (v0.3.5: -324行, v0.3.6: -1488行, v0.3.7: -768行, v0.3.8: -409行, 死代码清理: -58行, 阴影系统提取: -456行)
- **清理方案**: 继续按渲染职责拆分（下一步: 光照/色调效果方法组 ~250行）

### ~~🔴 TD-053: TopDownParticleSystem 重复定义~~ ✅ 已修复 (v0.3.8)

- **描述**: `enhanced_renderer.py` L85-L493 重复定义了已存在于 `particle_system.py` 的 `TopDownParticleSystem` 类（436行），与 v0.3.5 TopDownLightingConfig 重复定义问题完全相同模式
- **影响**: DRY 违反，修改 particle_system.py 可能不生效，维护风险高
- **文件**: `src/pycc2/presentation/rendering/enhanced_renderer.py`
- **状态**: ✅ **已修复** — 删除 L85-L494 重复定义（410行），保留 L63 import 语句，2987行 (-12%)
- **修复日期**: 2026-05-31 (v0.3.8)

### ~~🟢 TD-054: EnhancedRenderer 4个未使用粒子方法（死代码）~~ ✅ 已修复 (v0.3.8+)

- **描述**: EnhancedRenderer 类中存在 4 个完全未被外部调用的粒子包装方法：`spawn_hit_marker()`、`spawn_smoke_cloud()`、`spawn_dirt_splash()`、`spawn_blood_pool()`，共 58 行死代码
- **影响**: 代码膨胀，维护者误以为这些方法被使用而浪费时间维护
- **文件**: `src/pycc2/presentation/rendering/enhanced_renderer.py`
- **状态**: ✅ **已删除** — 通过静态分析确认无外部调用方（combat_director.py 仅使用另一组 _sprite_renderer 委托方法），安全删除 58 行
- **修复日期**: 2026-05-31 (v0.3.8+ 死代码清理)
- **验证**: 3371/3372 测试通过（1个已知 flaky），E2E 7/7 通过

### ~~🟡 TD-055: 旧版阴影系统重复代码~~ ✅ 已修复 (v0.3.9)

- **描述**: EnhancedRenderer 存在两套阴影渲染系统：
  - **旧版**（L1341-L1474）：`_draw_building_shadows()` + `_draw_unit_shadows()`，直接 pygame 绘制，133行
  - **新版**（L2105-L2274）：`_render_building_shadows()` + `_render_tree_shadows()` + `_render_unit_shadows()`，委托 ShadowRenderer，265行
  - 问题：旧版被 `_apply_environment_lighting()` 调用，与新版功能重复，造成双重阴影渲染
- **影响**: DRY 违反，性能浪费（重复渲染阴影），维护混乱
- **文件**: `src/pycc2/presentation/rendering/enhanced_renderer.py`
- **状态**: ✅ **已修复**：
  1. 删除旧版 `_draw_building_shadows()` (61行) 和 `_draw_unit_shadows()` (74行)
  2. 重构 `_apply_environment_lighting()` 移除阴影调用（保留暖色调+暗角）
  3. 提取新版4个方法到独立模块 `shadow_rendering_system.py` (~340行)
  4. EnhancedRenderer 通过 `ShadowRenderingSystem` 协调器统一管理阴影
- **修复日期**: 2026-05-31 (v0.3.9 阴影系统重构)
- **验证**: 3372/3372 测试通过（0失败！），enhanced_renderer.py: 2929 → 2521行 (-456行, -15.6%)

### 🟢 TD-033: 缺少E2E（端到端）测试

- **描述**: 没有模拟真实用户使用场景的端到端测试
- **影响**: 发布前无法验证游戏可玩性
- **状态**: ❌ 未解决
- **清理方案**: 创建E2E测试套件，覆盖从启动到完成一场战斗的完整流程

### 🟢 TD-034: 测试中1个失败用例未修复

- **描述**: 3372个测试中有1个失败（test_swiss_cheese.py::test_armor_piercing_increases_kia_wia，随机性断言flaky），暴露了集成断裂点
- **影响**: CI不可靠，真实Bug被掩盖
- **状态**: ❌ 未解决（已从2767个测试增长至3372个，flaky测试待修复）
- **清理方案**: 分析失败测试的随机性断言逻辑，增加容差或改用确定性断言

### 🟢 TD-035: 缺少接口契约测试

- **描述**: 模块间接口没有契约测试（Consumer-Driven Contract），导致属性名不匹配等问题无法被测试发现
- **影响**: P0-002（属性名不匹配）类问题会反复出现
- **状态**: ❌ 未解决
- **清理方案**: 为关键模块接口添加契约测试

### 🟢 TD-036: 缺少性能回归测试

- **描述**: 没有性能回归测试基线，无法检测性能退化
- **影响**: 性能优化可能被后续修改无意中破坏
- **状态**: ❌ 未解决
- **清理方案**: 建立性能基线，添加性能回归测试

### 🟢 TD-037: 缺少AI行为集成测试

- **描述**: AI行为仅有单元测试，没有验证AI在完整游戏循环中的行为
- **影响**: AI导入失败（TD-023）类问题无法被测试发现
- **状态**: ❌ 未解决
- **清理方案**: 添加AI行为集成测试，验证AI在游戏循环中的完整行为链

### 🟢 TD-038: 文档与代码不同步

- **描述**: 多处文档声称功能"已完成"但实际不可用（如v2.5声称还原度~97%）
- **影响**: 决策基于错误信息，资源分配不当
- **状态**: ❌ 未解决（本次v0.1.0已修正PRD，其他文档待同步）
- **清理方案**: 建立文档-代码同步验证机制，每个Phase结束时实际运行验证

### 🟢 TD-039: 缺少错误恢复机制

- **描述**: 关键路径缺少错误恢复机制，一个组件崩溃导致整个游戏崩溃
- **影响**: P0 Bug导致游戏完全不可玩，而非降级运行
- **状态**: ❌ 未解决
- **清理方案**: 为关键组件添加错误恢复和降级机制

### 🟢 TD-040: 缺少运行时健康检查

- **描述**: 没有运行时健康检查机制，无法在启动时检测关键组件是否正常
- **影响**: 游戏启动后才发现Bug，而非启动时即报错
- **状态**: ❌ 未解决
- **清理方案**: 添加启动时健康检查，验证关键组件可正常初始化

### 🟢 TD-041: 缺少变更影响分析流程

- **描述**: 修改一个模块时没有分析对其他模块影响的标准流程
- **影响**: 修改可能无意中破坏其他模块的接口（P0 Bug的根因之一）
- **状态**: ❌ 未解决
- **清理方案**: 建立变更影响分析流程，修改前检查所有引用方

---

## 五、v2.0旧条目验证状态

> **说明**: 以下为v2.0声称已解决的20项技术债。v3.0基于DevSquad批判性Review重新验证。

| ID | 描述 | v2.0声称 | 实际验证结果 |
|----|------|---------|-------------|
| TD-001 | EnhancedRenderer未集成到主游戏循环 | ✅ 已解决 | ⚠️ 代码已集成，但旧UI残留冲突（TD-025）导致渲染不稳定 |
| TD-002 | CombatState(压制+隐蔽)未集成到Unit实体 | ✅ 已解决 | ⚠️ 代码已添加，但属性名不匹配（TD-022）导致实际不可用 |
| TD-003 | CC2武器/单位数据库未替换旧系统 | ⚠️ campaign_four_layer.py替代 | ⚠️ 仍为部分解决，campaign.py仍存在 |
| TD-004 | 部署阶段系统未集成UI | ✅ 已解决 | ⚠️ 代码已集成，但渲染崩溃无法使用 |
| TD-005 | EnhancedTile数据未与地图加载器对接 | ✅ 已解决 | ✅ 验证通过 |
| TD-006 | 旧enhanced_mission_system.py重复 | ✅ 已删除 | ✅ 验证通过 |
| TD-007 | 地图扩展脚本边界区域不自然 | ⚠️ 已记录4个问题 | ⚠️ 未修复，低优先级 |
| TD-008 | PaletteGenerator使用random导致不可复现 | ✅ 已解决 | ✅ 验证通过 |
| TD-009 | cc2_authentic_units.py拼写错误 | ✅ 已修复 | ✅ 验证通过 |
| TD-010 | 测试中4个headless环境失败 | ✅ 已解决 | ⚠️ 现为6个失败（TD-034），问题未完全解决 |
| TD-011 | 武器数据库year_introduced类型不一致 | ✅ 已修复 | ✅ 验证通过 |
| TD-012 | campaign.py中DAY_MISSION_MAP引用不存在 | ✅ 已修复 | ✅ 验证通过 |
| TD-013 | 缺少新系统的单元测试 | ✅ 已解决 | ⚠️ 单元测试有，但集成测试仅1个（TD-028） |
| TD-014 | ProtoRenderer仍存在 | ✅ 已删除 | ✅ 验证通过 |
| TD-015 | 地图JSON文件体积过大 | ✅ 已解决 | ✅ 验证通过 |
| TD-016 | CommanderAI中硬编码魔法数字 | ✅ 已解决 | ✅ 验证通过 |
| TD-017 | 缺少性能基准测试 | ✅ 已解决 | ⚠️ 有benchmark但无回归测试（TD-036） |
| TD-018 | cc2_authentic_units.py错误import | ✅ 已修复 | ⚠️ AI导入仍有问题（TD-023），说明import问题未系统解决 |
| TD-019 | combat_resolver O(n²)目标选择 | ✅ 已解决 | ✅ 验证通过 |
| TD-020 | 15+模块零测试覆盖 | ✅ 核心模块测试已补充 | ⚠️ 测试数增加但集成测试缺失（TD-028） |

**验证总结**: 20项中仅9项完全验证通过，8项部分解决/有新问题，3项未变。v2.0声称"20/20全部清理"严重高估。

---

## 六、清理优先级

### 🔴 P0 必须立即修复（阻塞游戏可玩性）— ✅ 全部已清除

- [x] ~~TD-021: Unit添加display_name属性~~ ✅ 已修复 (2026-05-23)
- [x] ~~TD-022: 统一HealthComponent/MoraleComponent属性名~~ ✅ 已修复 (2026-05-23)
- [x] ~~TD-023: 修复AI行为类导入路径~~ ✅ 已修复 (2026-05-23)
- [x] ~~TD-024: set_mode()支持fast/sneak参数~~ ✅ 已修复 (2026-05-24)
- [x] ~~TD-025: 清理旧UI组件文件~~ ✅ 已修复 (2026-05-25)

### 🟡 P1 应尽快修复（功能受损/架构违规）

- [ ] TD-026: 拆分29个超500行文件
- [ ] TD-027: 明确infra/infrastructure职责
- [x] ~~TD-028: 添加集成测试~~ ✅ 已修复 (2026-05-24, 6个集成测试文件)
- [ ] TD-029: 合并4个视觉优化文档（暂缓：文档用途不同，风险较高）
- [x] ~~TD-030: 修复音频stereo预生成~~ ✅ 已修复 (2026-05-24)
- [x] ~~TD-031: POLISH阵营加入友军列表~~ ✅ 已解决 (v0.3.7)
- [x] ~~TD-032: 补充GameSettings类型注解导入~~ ✅ 已解决 (v0.3.7)
- [x] ~~TD-045: 修复Domain→Presentation层违规（BUILDING_WINDOWS）~~ ✅ 已修复 (2026-05-28)
- [x] ~~TD-046: 合并重复士气模块（morale_sys.py vs morale_system.py）~~ ✅ 已修复 (2026-05-28)
- [x] ~~TD-047: 修复68个bare except块~~ ✅ 已修复 (2026-05-28)
- [ ] TD-050: 修复Domain→Infrastructure层违规（morale_system.py导入voice_commands）
- [ ] TD-051: 修复Domain→Services层违规（7处导入EventBus/RandomContext）

### 🟢 P2 计划修复（质量/维护）

- [ ] TD-033: 创建E2E测试套件
- [ ] TD-034: 修复失败测试用例
- [ ] TD-035: 添加接口契约测试
- [ ] TD-036: 建立性能回归测试基线
- [ ] TD-037: 添加AI行为集成测试
- [ ] TD-038: 建立文档-代码同步验证机制
- [ ] TD-039: 添加关键组件错误恢复机制
- [ ] TD-040: 添加启动时健康检查
- [ ] TD-041: 建立变更影响分析流程
- [ ] TD-042: 下载集成PixVoxel CC0精灵资源
- [ ] TD-043: 优化等距渲染性能
- [ ] TD-044: 等距模式默认切换
- [x] ~~TD-048: 审查并重构quick_implementations.py~~ ✅ 已修复 (2026-05-28)
- [x] ~~TD-049: 合并infra/到infrastructure/~~ ✅ 已修复 (2026-05-28)
- [ ] TD-052: 拆分enhanced_renderer.py（~2521行，目标<2000行）

---

**维护规则**:
1. 每次发现新问题立即添加到此文档
2. 清理完成后标记[已清理]并注明日期
3. 每个Phase结束时review此清单
4. 绝不带着P0技术债进入下一个Phase
5. **v3.0新增规则**: 声称"已解决"的技术债必须通过集成测试验证，单元测试通过不等于问题已解决
