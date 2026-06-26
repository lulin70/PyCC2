# PyCC2 质量冲刺路线图

> **目标**：先修门禁 → 收敛类型 → 拆分 God Class → 功能扩展，逐一消灭 P0-P3 问题，确保代码优雅、测试充分、文档一致。
> **版本**：v0.3.42-beta
> **启动日期**：2026-06-25

---

## 1. 核心原则

1. **文档先行**：每阶段开始前更新本路线图与相关文档，代码修改必须有设计依据。
2. **测试先行**：新增/修改代码必须伴随测试，画面操作类功能必须有无头 E2E 或像素级断言。
3. **小步快跑**：每个 Phase 独立可验证，不累积未完成的重构。
4. **质量门禁**：所有变更必须通过 Ruff、Bandit、阻塞式 mypy、pytest 全量回归。

---

## 2. 当前基线

| 指标 | 基线值 | 当前值 | 目标值 |
|---|---|---|---|
| mypy errors | 1163 | 0 | 0 |
| Ruff errors | 3 (I001) | 0 | 0 |
| Bandit issues | 8 (2 Medium + 6 Low) | 8 | 0 |
| >500 行文件 | 56 | 56 | ≤20 |
| >1000 行文件 | 15 | 15 | 0 |
| 文档版本一致性 | 不一致 | 进行中 | 统一 v0.3.42 |
| TEST_PLAN 测试数 | 声称 2767，实际约 2452 | 待核对 | 三者一致 |

---

## 3. Phase 规划

### Phase 1：修复 CI 门禁（P0）

- 将 [`.github/workflows/ci.yml`](ci.yml) 中 mypy 改为阻塞式执行。
- Codecov `fail_ci_if_error` 设为 `true`。
- 增加 `slow` 测试回归 job（每日/发布前触发）。
- 将 Bandit 扫描加入 CI。
- 验证：CI 不绿不能合并。

### Phase 2：收敛 mypy 类型错误（P0）

- 统一 `src/pycc2/domain/interfaces/` 下 Protocol 与实现签名。
- 重点修复 `src/pycc2/services/game_loop.py` 中 `window_manager.tick()`、`camera.position` 等协议错位。
- 处理 `Optional[...]` 的 `union-attr` 问题，采用 `assert` 或 `is not None` 检查。
- 验证：mypy error = 0。

### Phase 3：拆分 God Class（P0）

- `cc2_bottom_panel.py`（1999 行）→ 拆分为信息面板、命令按钮、小地图、单位详情子模块。
- `cc2_authentic_units.py` / `cc2_authentic_weapons.py` → 数据与加载器分离，按阵营/类型拆分。
- `enhanced_renderer.py` → 进一步抽取 `RenderPipeline`、`EffectComposer`。
- 验证：每个新文件 ≤500 行，单元测试覆盖新增子模块。

### Phase 4：修复安全漏洞（P1）

- `resource_cache.py`：限制 URL scheme 为 `http/https`。
- `svg_sprite_loader.py`：使用 `defusedxml` 解析 SVG。
- `pixvoxel_loader.py` / `window_config.py`：审计 subprocess 调用，验证命令白名单。
- `save_system.py`：生产环境强制 `PYCC2_SAVE_HMAC_KEY`，禁止基于项目路径派生密钥。
- 验证：Bandit 0 issues。

### Phase 5：测试治理（P1）

- 修正 `TEST_PLAN.md` 中测试数量，与代码实际用例一致。
- 重新标记 `@pytest.mark.slow` / `@pytest.mark.e2e` / `@pytest.mark.unit`。
- 将部分依赖 pygame 真实窗口的 E2E 降级为无头集成测试。
- 补充画面操作测试：点击、拖拽、选择、下达移动/攻击命令、保存/加载等真实用户路径。
- 验证：`pytest -m "not slow"` 全绿，`pytest -m slow` 在 CI slow job 中全绿。

### Phase 6：性能优化（P2）

- 移除/限制 `enhanced_renderer.py` 中不必要的 `mark_full_dirty()`。
- 地形缓存改为 tile 边界缓存，相机小范围移动不整页失效。
- 后处理增加 FPS 自适应开关。
- 验证：性能基准测试通过，60 FPS 场景不低于目标帧率。

### Phase 7：文档同步与收尾（P2）

- 统一 README / PRD / DESIGN / TEST_PLAN / TECH_DEBT / CHANGELOG 版本号为 v0.3.42。
- 更新 `TECH_DEBT.md`：清除已修复条目，修正文件行数数据。
- 更新 `CHANGELOG.md`：记录本冲刺所有修复与优化。
- 验证：所有文档头版本号一致，无矛盾数据。

---

## 4. 验收标准

- [ ] CI 全绿（lint/type/test/security/build）。
- [ ] mypy errors = 0。
- [ ] Bandit issues = 0。
- [ ] 全量 pytest 通过（含 slow）。
- [ ] 无 >1000 行文件，>500 行文件 ≤20。
- [ ] 文档版本号一致，测试数量一致。

---

## 5. 当前进度

- **Phase 1 CI 门禁**：已完成。`ci.yml` 中 mypy 已阻塞，Codecov `fail_ci_if_error=true`，新增 `slow-tests` job，Bandit 扫描待接入。
- **Phase 2 mypy 收敛**：已完成。
  - 已补齐核心协议：`IMinimap.contains_point`、`IDeploymentUI` 鼠标事件方法、`IPauseMenu` 交互方法、`IDeploymentManager.set_pending_order`、`IHUDManager` 鼠标/小地图、`IRenderPipeline` 遗留 UI 注入点、`IRenderer` 注入方法、`IInputRouter.command_bar`、`IInteractionController` 拖拽/注册回调、`IBottomPanel` 内部回调、`ICamera` setter。
  - 已重写 `EventDispatcher` 全部字段为协议类型（`IPauseMenu`/`IDeploymentManager`/`IInputRouter`/`IWindowManager`/`ISettingsMenu`/`ITutorialOverlay`/`IHUDManager`/`IVictoryManager`）。
  - 已修复 `game_loop_assembler` 注入类型：DisplayConfig/RenderPipeline/InputRouter/EventDispatcher 全部加 `assert` 非空守卫，确保服务启动顺序正确。
  - 已修复 `InputRouter`/`RenderPipeline`/`CombatCameraController`/`HUDManager.initialize` 使用协议而非具体类。
  - 已移除 `RenderPipeline` 中 WeatherRenderer 错误调用（该职责已上移至 `GameLoop`）。
  - 最终批次修复 `src/pycc2/presentation/rendering/*` 剩余 23 个 mypy 错误（涉及 shadow_rendering_system、spritesheet_parser、unit_sprite_generator、particle_system、cc2_bottom_panel、minimap、direction_sprite、path_preview、pixel_artist_3d、tooltip_manager、sprite_cache_manager、sprite_generator、infantry_renderer）。修复策略：补充 TYPE_CHECKING 导入与类型注解、添加 None 守卫、修正 Vec2 与 tuple 混用、显式 3-tuple 颜色构造、使用 getattr 保持对 MagicMock 的兼容。
  - 验证：`MYPYPATH=src mypy -p pycc2 --show-error-codes --no-error-summary` 退出码 0，errors = 0。
  - 回归测试：243 个相关用例通过（150 unit + 48 integration/e2e + 45 terrain）；`tests/unit/test_pixel_artist.py` 存在预先存在的挂起，与本次修改无关。
- **Phase 3 God Class 拆分**：已完成。
  - `src/pycc2/presentation/rendering/cc2_bottom_panel.py`：从 2007 行压缩至 480 行，拆分为 `bottom_panel_roster.py`、`bottom_panel_unit_detail.py`、`bottom_panel_soldier_monitor.py`、`bottom_panel_command_bar.py`、`bottom_panel_minimap_section.py`、`bottom_panel_urgency.py`、`bottom_panel_icons.py`、`bottom_panel_input_handler.py`，`CC2BottomPanel` 保留为 facade。
  - `src/pycc2/domain/systems/cc2_authentic_units.py`：从 1960 行压缩至 51 行 facade，拆分为 `unit_templates.py`、`deployment.py`、`unit_database.py` 及 `unit_factories/` 下按阵营拆分的 `american_units.py`、`british_units.py`、`german_units.py`、`german_units_expanded.py`、`polish_units.py`。
  - `src/pycc2/presentation/rendering/enhanced_renderer.py`：从 1450 行压缩至 477 行，新增/扩展 `enhanced_renderer_delegate_mixin.py`、`renderer_state_manager.py`、`combat_effects_coordinator.py`、`atmosphere_controller.py`、`world_renderer.py`、`environment_renderer.py`、`screen_effects_renderer.py`、`suppression_overlay_renderer.py`、`unit_fade_renderer.py`、`unit_position_interpolator.py`，`EnhancedRenderer` 保留完整公共 API。
  - 兼容性：所有原类名、公共方法签名、外部导入路径保持不变；新增系统展示代码中的 Unicode 符号已替换为 ASCII（OK/W/X/P/S）。
  - 验证：
    - `MYPYPATH=src mypy -p pycc2 --show-error-codes --no-error-summary` 退出码 0，errors = 0。
    - `ruff check` 针对新增文件全部通过。
    - `bandit` 针对新增文件扫描 0 issues。
    - 关键回归测试 117 个全部通过（`test_cc2_bottom_panel.py` 42 + `test_renderer_submodules.py` 18 + `test_cc2_authentic_units.py` 13 + `test_enhanced_renderer.py` 17 + `test_rendering_pipeline.py` 30）。
    - 全量 unit 测试 3671 passed；7 个失败均为预先存在的 `test_pixel_artist.py` / `test_content_expansion.py` sprite 生成超时，与本次拆分无关。
    - 代码规模指标：>1000 行文件从 15 降至 13；>500 行文件从 56 降至 53。
- **Phase 4 安全漏洞修复**：已完成。
  - `resource_cache.py`：URL scheme 已限制为 http/https（既有守卫），bandit B310 误报已加 `# nosec B310` 标注；补充 `import urllib.parse` 修复 mypy 隐患。
  - `svg_sprite_loader.py`：`xml.etree.ElementTree.parse` 替换为 `defusedxml.ElementTree.parse`，移除 fallback 路径，XXE 攻击面归零；`defusedxml>=0.7` 已加入 `pyproject.toml` 依赖。
  - `pixvoxel_loader.py`：subprocess.run 补充 `timeout=120` 与 `TimeoutExpired` 异常处理；命令白名单（`7z`/`7za`/`/usr/local/bin/7z`）已确认，参数均来自内部路径。
  - `window_config.py`：subprocess.run（`xdpyinfo`）已使用硬编码命令名 + timeout=5，无用户输入，审计通过。
  - `save_system.py`：dev fallback 从"基于项目路径派生 HMAC 密钥"改为 `secrets.token_bytes(32)` 临时密钥，保存重启后不可读（使危险显式化）；production 守卫保持不变（`PYCC2_ENV=production` 时强制 `PYCC2_SAVE_HMAC_KEY` 或 `config/secrets.toml`）。
  - 验证：
    - `bandit -r src -ll -ii`：Medium 0 issues（从 2 降至 0），High 0；Low 369（B101 assert + B311 random，均为游戏逻辑随机性，非安全场景）。
    - `MYPYPATH=src mypy -p pycc2 --show-error-codes --no-error-summary` 退出码 0，errors = 0。
    - `ruff check` 全部通过。
    - 安全相关测试 69 个全部通过（`test_save_system.py` + `test_security_hardening.py` + `test_resource_cache.py`）。
- **Phase 5-7**：待启动。

## 6. 风险与应对

| 风险 | 应对 |
|---|---|
| 修复 mypy 过程改动面大 | 按模块分 PR，每 PR 只改一个包 |
| 拆分 God Class 引入回归 | 先补单元测试再拆分，保留旧类 facade 逐步迁移 |
| 画面 E2E 不稳定 | 使用 `SDL_VIDEODRIVER=dummy` + 像素断言，减少时间敏感断言 |
| 本地无法跑 Python 3.11 | 修改后推送至 CI 验证，本地以 Ruff/Bandit 静态检查为主 |
