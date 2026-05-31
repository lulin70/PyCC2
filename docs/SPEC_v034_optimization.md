# PyCC2 v0.3.4 Optimization SPEC

> **文档版本**: v1.0 | **日期**: 2026-05-30 | **状态**: 待审批
> **基准版本**: v0.3.3 (`e64d2b5`) | **审核轮次**: 第3轮7维度评判性审核
> **方法**: DevSquad 多角色协作 (Architect + Tester + Coder)

---

## 1. 问题定义

### 1.1 发现的问题总览

| ID | 严重度 | 问题 | 根因 | 影响范围 |
|----|--------|------|------|---------|
| **P0-1** | 🔴 致命 | HUD 三面板未集成渲染管线 | 实现-集成链条断裂 | V01 功能完全失效 |
| **P0-2** | 🔴 致命 | CC2色调分级默认关闭 | 半成品 `hasattr` 守卫 | V05 功能完全失效 |
| **D1-1** | 🟡 重要 | enhanced_renderer.py 5961行/7类/135方法 | 职责堆积，v0.3.3增强回增1361行 | 可维护性下降 |
| **D5-1** | 🟡 重要 | 文档滞后(v0.3.2) + 保真度高估(91%→85%) | 发布后未同步 | 用户误导 |
| **D4-1** | 🟡 重要 | E2E测试无法检测"集成缺失"类bug | 测试策略缺陷 | 质量保证盲区 |
| **D6-1** | 🟢 低 | __pycache__ 污染(25目录+312文件) | 测试运行重建 | 目录整洁 |

### 1.2 幽灵功能根因分析（Architect 视角）

```
正常流程:  需求 → 设计 → 实现 → 集成 → 验证 → 发布
实际流程:  需求 → 设计 → 实现 → [断裂] → 单元验证 → 发布
                              ↑
                         缺少集成步骤
```

**具体原因**:
1. **HUD**: 子agent独立完成 cc2_hud.py 编码，但无人负责将其 `import` 并调用到 `EnhancedRenderer.render()` 流程中
2. **色调**: `_apply_cc2_color_grading` 方法编写时使用了防御性 `hasattr`，但忘记在 `__init__` 中初始化对应属性和 setter

---

## 2. 优化方案

### 2.1 P0-1: HUD 渲染管线集成

**目标**: 将 CC2HUD 集成到 EnhancedRenderer 主渲染循环

**修改清单**:

| # | 文件 | 行号 | 修改内容 |
|---|------|------|----------|
| 1 | `enhanced_renderer.py` | L3093 `__init__` | 新增 `self._hud = None` + `self._hud_enabled = False` |
| 2 | `enhanced_renderer.py` 新增方法 | L3190后 | `def set_hud(self, hud: CC2HUD) -> None` |
| 3 | `enhanced_renderer.py` 新增方法 | 后续 | `def enable_hud(self, enabled: bool = True) -> None` |
| 4 | `enhanced_renderer.py` | L3191 `render()` 方法末尾 | 在地形/单位/粒子渲染后、final blit前添加 `if self._hud_enabled and self._hud: self._hud.render(surface)` |

**代码片段预览**:

```python
# enhanced_renderer.py __init__ 中新增:
self._hud: CC2HUD | None = None
self._hud_enabled: bool = True

# 新增方法:
def set_hud(self, hud: 'CC2HUD') -> None:
    self._hud = hud

def enable_hud(self, enabled: bool = True) -> None:
    self._hud_enabled = enabled

# render() 末尾（L3290区域）新增:
if self._hud_enabled and self._hud:
    self._hud.render(surface)
```

**风险**: 低 — 仅追加调用，不影响现有渲染路径

---

### 2.2 P0-2: CC2 色调分级默认启用

**目标**: 移除 `hasattr` 守卫，改为显式配置

**修改清单**:

| # | 文件 | 行号 | 修改内容 |
|---|------|------|----------|
| 1 | `enhanced_renderer.py` | L3093 `__init__` | 新增 `self._enable_cc2_color_grading: bool = True` |
| 2 | `enhanced_renderer.py` | L3155后 | 新增 `def set_cc2_color_grading(self, enable: bool) -> None` |
| 3 | `enhanced_renderer.py` | L2863 | `if hasattr(...) and self._enable_cc2_color_grading:` → `if self._enable_cc2_color_grading:` |

**代码片段预览**:

```python
# __init__ 中新增:
self._enable_cc2_color_grading: bool = True

# 新增方法:
def set_cc2_color_grading(self, enable: bool) -> None:
    self._enable_cc2_color_grading = enable

# L2863 修改前:
if hasattr(self, '_enable_cc2_color_grading') and self._enable_cc2_color_grading:
    self._apply_cc2_color_grading(surface)

# 修改后:
if self._enable_cc2_color_grading:
    self._apply_cc2_color_grading(surface)
```

**风险**: 极低 — 纯配置变更，向后兼容

---

### 2.3 D1-1: EnhancedRenderer 二次拆分计划

**目标**: 5961行 → 分离为 4 个模块

**当前类分布**:

| 类 | 行数(约) | 应归属模块 |
|----|---------|-----------|
| TopDownLightingConfig | 73 | `lighting_system.py` ✅ 已拆 |
| PaletteGenerator | ~90 | `palette_generator.py` (新) |
| ProceduralTextureGenerator | ~1480 | `texture_generator.py` (新) |
| SpriteGenerator | ~500 | `sprite_generator.py` ✅ 已拆 |
| TerrainTileCache | ~160 | `terrain_cache.py` (新) |
| TopDownParticleSystem | ~400 | `particle_system.py` ✅ 已拆 |
| EnhancedRenderer (主类) | ~3300 | `enhanced_renderer.py` (精简后) |

**执行优先级**:
1. **v0.3.4** (本次): P0-1 + P0-2 修复 + 文档同步 — **不拆分**
2. **v0.3.5**: 提取 PaletteGenerator + TerrainTileCache → 减少约250行
3. **v0.3.6**: 提取 ProceduralTextureGenerator → 减少约1480行
4. **最终目标**: EnhancedRenderer 主类 < 2000行

**理由**: v0.3.3 刚完成弹坑/VP增强，立即拆分可能引入回归。先修复幽灵功能稳定功能集。

---

### 2.4 D5-1: 文档同步 + 保真度修正

**修改清单**:

| 文件 | 修改项 |
|------|--------|
| README.md | v0.3.2→v0.3.3, fidelity 91%→**85%(诚实)**, 更新changelog |
| README_zh.md | 同上 |
| GAP_ANALYSIS.md | 版本更新, 视觉91%→**85%**, 新增幽灵功能说明, 综合分修正 |

**保真度重算依据**:
```
V01 HUD:     0%   (幽灵, 未集成)  权重 15% → 0
V02 VP显示:  95%  (38px+脉冲)      权重 10% → 9.5
V03 弹坑:    90%  (5层真实实现)    权重 20% → 18
V04 爆炸:    92%  (多边形火焰)      权重 25% → 23
V05 色调:    0%   (幽灵, 默认关)    权重 30% → 0
─────────────────────────────────────────────
加权视觉分:  50.5 / 60 可用分 = 84.2% ≈ **85%**
```

---

### 2.6 D4-1: E2E 测试增强策略

**问题**: 当前 E2E 只检查 API 存在性（`hasattr`, `isinstance`, 方法可调用），不检查运行时行为

**新增测试维度**:

| 维度 | 当前 | 增强 |
|------|------|------|
| 类存在性 | ✅ | 保持 |
| 接口签名 | ✅ | 保持 |
| **渲染管线集成** | ❌ | **新增**: mock surface → 调用 render → 检查 hud.render 是否被调用 |
| **配置默认值** | ❌ | **新增**: 检查 `_enable_cc2_color_grading` 默认为 True |
| **端到端可见性** | ❌ | **新增**: 截图对比（可选，需pygame display） |

**新增 E2E 测试用例**:

```python
class TestGhostFeatureDetection:
    def test_hud_integrated_in_render_pipeline(self):
        """P0-1 regression: HUD must be callable from render()"""
        renderer = EnhancedRenderer()
        hud = CC2HUD(screen_size=(1024, 768))
        renderer.set_hud(hud)
        renderer.enable_hud(True)
        
        surface = pygame.Surface((1024, 768))
        with patch.object(hud, 'render', wraps=hud.render) as mock_render:
            renderer.render(surface)
            mock_render.assert_called_once()

    def test_cc2_color_grading_enabled_by_default(self):
        """P0-2 regression: Color grading must default to ON"""
        renderer = EnhancedRenderer()
        assert renderer._enable_cc2_color_grading is True
```

---

## 3. 执行计划

### Phase A: P0 修复（预计 45min）

| 步骤 | 任务 | 文件 | 风险 |
|------|------|------|------|
| A1 | P0-2: 色调分级启用 | enhanced_renderer.py | 极低 |
| A2 | P0-1: HUD 集成 | enhanced_renderer.py (+ import) | 低 |
| A3 | D6: 清理 __pycache__ | shell command | 无 |
| A4 | 运行全量测试 | pytest | — |
| A5 | Git commit + tag v0.3.4 | git | — |

### Phase B: 文档同步（预计 15min）

| 步骤 | 任务 | 文件 |
|------|------|------|
| B1 | README.md 更新 | README.md |
| B2 | README_zh.md 更新 | README_zh.md |
| B3 | GAP_ANALYSIS.md 更新 | docs/GAP_ANALYSIS.md |
| B4 | Git commit | git |

### Phase C: E2E 增强测试（预计 20min）

| 步骤 | 任务 | 文件 |
|------|------|------|
| C1 | 编写幽灵功能检测测试 | scripts/e2e_v034_ghost_feature_test.py |
| C2 | 运行验证 | pytest |
| C3 | Git commit | git |

### Phase D: 文件拆分（v0.3.5，不在本次范围）

---

## 4. 风险评估矩阵

| 修复项 | 概率 | 影响 | 缓解措施 | 总风险 |
|--------|------|------|----------|--------|
| P0-2 色调启用 | 极低 | 低 | 有 git 回滚 | **极低** |
| P0-1 HUD 集成 | 低 | 低 | 条件开关控制 | **低** |
| 文档修正 | 无 | 无 | 纯文本 | **无** |
| E2E 新增 | 低 | 低 | 不影响现有测试 | **低** |

---

## 5. 验收标准

- [ ] `EnhancedRenderer()._enable_cc2_color_grading` 默认值为 `True`
- [ ] `EnhancedRenderer.set_hud(CC2HUD(...))` 不抛异常
- [ ] `EnhancedRenderer.enable_hud(True)` 后 render() 调用 hud.render()
- [ ] 全量 3372 测试通过 (0 failures)
- [ ] E2E 新增测试 ≥ 3 个用例覆盖幽灵功能检测
- [ ] README/GAP_ANALYSIS 声明版本 v0.3.4，保真度 85%
- [ ] Git clean working tree, tag v0.3.4

---

## 6. 回滚方案

```bash
git revert HEAD --no-edit    # 回滚 v0.3.4
git tag -d v0.3.4           # 删除 tag
# 或:
git reset --hard v0.3.3     # 强制回到 v0.3.3
```

---

*文档结束。等待用户审批后进入 Phase 4 执行阶段。*
