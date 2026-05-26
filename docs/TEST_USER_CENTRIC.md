# PyCC2 用户操作视角测试策略 (User-Centric Test Strategy)

> 强化版本: 从用户角度验证所有操作可用
> 版本: v2.0 (严格模式)
> 创建日期: 2026-05-22
> 配套文档: UI_REALISTIC_PIXEL_SPEC.md (视觉规范)

---

## 核心理念

**"测试不是为了证明代码能工作，而是证明用户不会遇到问题"**

---

## 一、用户场景矩阵 (User Scenario Matrix)

### 场景1: 新游戏流程 (New Game Flow)
```
前置条件: 游戏已安装, 可启动
步骤:
  1. 启动 python -m pycc2.main
  2. 等待主菜单出现 (< 5秒)
  3. 点击 "New Campaign" 按钮
  4. 选择阵营 (Allies / Axis)
  5. 选择难度 (Easy / Normal / Hard / Veteran)
  6. 点击 "Start Campaign"
  7. 进入战略地图视图 (Market Garden走廊)

预期结果:
  ✅ 每步无崩溃
  ✅ 按钮有响应 (hover/点击视觉反馈)
  ✅ 选择正确保存 (进入对应战役)
  ✅ 加载时间 < 3秒

验证方法: 自动化脚本 + 人工观察录屏

失败判定:
  ❌ 启动崩溃或报错
  ❌ 主菜单超过10秒未显示
  ❌ 点击按钮无响应
  ❌ 选择后进入错误界面
```

### 场景2: 战斗部署阶段 (Deployment Phase)
```
前置条件: 已进入一场Battle
步骤:
  1. 显示部署界面 (左侧单位池 + 右侧地图)
  2. 从单位池拖拽 Rifle Squad 到地图己方区域
  3. 验证: 单位出现在拖放位置
  4. 拖拽 MG Team 到另一个位置
  5. 验证: 第二个单位出现, RP进度条更新
  6. 尝试拖拽到敌方区域 (应被拒绝或弹回)
  7. 验证: 无法在敌方区域放置
  8. 重复直到放置9个单位 (或RP耗尽)
  9. 点击 "Start Battle" 按钮
  10. 进入实时战斗界面

预期结果:
  ✅ 拖拽操作流畅 (跟随鼠标)
  ✅ 放置规则正确执行 (友军区OK, 敌军区拒绝)
  ✅ RP计数准确 (增减正确)
  ✅ Start Battle按钮可点击
  ✅ 过渡到战斗界面无卡顿 (>1秒)

失败判定:
  ❌ 拖拽时单位消失
  ❌ 放置位置错误 (偏移/穿透)
  ❌ RP不扣减或扣减错误
  ❌ Start Battle无响应或崩溃
```

### 场景3: 战斗核心操作 - 7命令验证 (Combat Commands)

这是**用户最关心的核心测试**！

#### 3.1 前进 (Move Command) ★基础命令★
```
操作序列:
  1. 左键点击己方 Rifle Squad (选中)
  2. 验证: 单位显示黄色选中框
  3. 验证: 底部面板更新为单位详情 (HP/士气/弹药)
  4. 右键单击地图空白处 (弹出上下文菜单)
  5. 验证: 菜单包含 "Move" 选项 (绿色可用状态)
  6. 点击 "Move" (或按快捷键 M)
  7. 验证: 鼠标变为移动模式 (可能变色/显示路径预览)
  8. 左键单击目标位置 (发出移动指令)
  9. 验证: 单位开始向目标位置移动 (非瞬移!)
  10. 验证: 移动过程中播放行走动画 (腿部摆动)
  11. 验证: 移动速度合理 (非瞬间到达, 也非过慢)
  12. 单位到达目标位置后停止

预期结果:
  ✅ 选中反馈即时 (< 0.1秒)
  ✅ 详情面板信息准确 (名称/HP/士气/弹药/状态)
  ✅ 右键菜单正确弹出 (位置合理/选项完整)
  ✅ Move命令可触发
  ✅ 路径预览显示 (绿/红虚线)
  ✅ 单位平滑移动 (非瞬移, 有速度感)
  ✅ 动画正确 (8方向朝向匹配移动方向)
  ✅ 到达后停止 (不穿墙/不越界)

失败判定:
  ❌ 选中后无视觉反馈
  ❌ 详情面板未更新或显示错误数据
  ❌ 右键菜单不弹出或选项缺失
  ❌ 点击Move后无反应
  ❌ 单位瞬移 (无移动过程)
  ❌ 移动方向与朝向不符
  ❌ 单位穿墙/越界
  ❌ 单位到达后不停留
```

#### 3.2 快速前进 (Fast Move / Run)
```
操作序列:
  1. 选中单位
  2. 右键菜单选择 "Fast Move" 或双击目标位置
  3. 验证: 单位以更快速度移动 (约为正常1.5-2x)
  4. 验证: 快速移动时疲劳值增加更快
  5. 验证: 快速移动时隐蔽度降低 (更容易被发现)

预期结果:
  ✅ 速度明显快于普通移动
  ✅ 有代价 (疲劳/隐蔽惩罚)
  ✅ 动画可能不同 (跑步姿态 vs 走路)

失败判定:
  ❌ 速度与普通移动无差异
  ❌ 无疲劳/隐蔽惩罚 (不平衡)
  ❌ 动画未变化
```

#### 3.3 潜行 (Sneak / Stealth Move)
```
操作序列:
  1. 选中侦察兵/步兵
  2. 右键菜单选择 "Sneak"
  3. 点击目标位置 (应在掩体附近)
  4. 验证: 单位以极慢速度移动 (正常0.3-0.5x)
  5. 验证: 移动时隐蔽度大幅提升 (不易被敌方发现)
  6. 验证: 可能呈现蹲姿/爬行动画

预期结果:
  ✅ 速度显著降低
  ✅ 发现概率降低 (结合昼夜系统: 夜间+50%)
  ✅ 视觉上有区别 (姿态更低/动作更小心)

失败判定:
  ❌ 速度未降低
  ❌ 隐蔽度未提升
  ❌ 视觉上无法区分潜行状态
```

#### 3.4 攻击 (Attack Command) ★最重要★
```
操作序列:
  1. 选中己方 Rifle Squad (有弹药, 在射程内)
  2. 右键单击敌方 Infantry Unit
  3. 验证: 弹出菜单, "Attack" 选项为绿色 (可执行)
  4. 点击 "Attack" (或按 A 键)
  5. 验证完整视觉链路:
     a. 攻击线绘制 (红线从射手到目标)
     b. 射击动画播放 (举枪→开枪→后坐)
     c. 枪口火焰特效 (黄色小椭圆, 0.05s)
     d. 弹道线显示 (细白线, 0.1s)
     e. 命中特效 (目标位置火花, 0.15s)
     f. 目标HP减少 (详情面板HP条缩短)
     g. 伤害数字显示 (-5 HP 红色浮动文字)
     h. 弹药数减少 (详情面板ammo-1)
  6. 如果目标死亡:
     a. 死亡动画播放 (倒下→躺平)
     b. 单位变为尸体标记 (灰色/小X)
     c. 从单位列表移除 (不再可控)
     d. 战斗日志记录: "[02:15] Rifle Squad → Enemy Squad (-8 KIA)"

预期结果 (最关键的!):
  ✅ 攻击命令可触发
  ✅ 视觉链路完整 (选敌→攻击→动画→特效→伤害→反馈)
  ✅ 伤害数值正确 (基于武器/距离/方向/cover计算)
  ✅ 弹药消耗正确
  ✅ 死亡处理完整 (动画→尸体→移除)
  ✅ 战斗日志记录

失败判定 (绝对不允许):
  ❌ 攻击后无任何视觉反馈 (黑箱操作)
  ❌ 伤害数值错误 (如: 应该-5却显示-999)
  ❌ 目标不死 (HP<=0仍站立)
  ❌ 死亡后仍可控/仍在列表
  ❌ 攻击无弹药消耗 (无限弹药bug)
  ❌ 攻击线穿越墙壁 (LOS失效)
```

#### 3.5 放烟雾 (Smoke Grenade)
```
操作序列:
  1. 选中持有烟雾弹的单位 (检查弹药>0)
  2. 右键菜单选择 "Smoke"
  3. 点击投放位置 (前方2-3格范围)
  4. 验证:
     a. 单位执行投掷动画 (手臂挥动)
     b. 烟雾弹飞行弧线 (抛物线, 0.3s)
     c. 落点产生烟雾团 (灰白色圆形, 半径3格)
     d. 烟雾持续3回合 (约45秒)
     e. 烟雾内单位不可被敌方看见 (除非相邻)
     f. 弹药 smoke-1

预期结果:
  ✅ 烟雾视觉效果明显 (大面积遮蔽)
  ✅ LOS阻断功能生效 (烟雾后敌人看不见)
  ✅ 持续时间正确
  ✅ 弹药消耗

失败判定:
  ❌ 烟雾不可见或太小
  ❌ LOS未阻断 (敌人仍能看见)
  ❌ 持续时间错误
  ❌ 无弹药消耗
```

#### 3.6 防御/挖壕 (Defend / Dig In)
```
操作序列:
  1. 选中单位
  2. 右键菜单选择 "Dig In" / "Defend"
  3. 验证:
     a. 单位进入防御姿态 (蹲下/趴下动画)
     b. 单位不再自动移动 (锁定位置)
     c. cover bonus提升 (+50% 防护)
     d. 经过3回合 (90tick) 后:
        - 地面显示战壕/散兵坑标记 (壕沟线条)
        - cover bonus永久提升
        - 单位可随时取消 Dig In 并移动

预期结果:
  ✅ 姿态改变可视 (站立→蹲/趴)
  ✅ 防护值提升 (可通过Tooltip查看)
  ✅ 战壕可视化 (地面纹理变化)
  ✅ 可取消恢复移动

失败判定:
  ❌ 姿态未改变
  ❌ 防护值未提升
  ❌ 战壕不可见
  ❌ 无法取消
```

#### 3.7 隐蔽/躲藏 (Hide / Take Cover)
```
操作序列:
  1. 选中单位 (靠近建筑物/树篱/墙壁)
  2. 右键菜单选择 "Hide"
  3. 验证:
     a. 单位快速移动到最近掩体后 (1-2格距离)
     b. 单位进入隐蔽状态 (半透明?或特殊标记?)
     c. 隐蔽度大幅提升 (敌方更难发现)
     d. 如果掩体是建筑: 单位进入建筑内部 (从地表消失?)

预期结果:
  ✅ 自动寻找最佳掩体位置
  ✅ 隐蔽状态可视化 (图标/半透明/状态栏提示)
  ✅ 发现概率降低
  ✅ 可随时取消Hide并移动

失败判定:
  ❌ 未移动到掩体
  ❌ 隐蔽状态不可视
  ❌ 发现概率未降低
  ❌ 无法取消
```

### 场景4: 单位切换与画面响应
```
操作序列:
  1. 当前选中 Unit A (Rifle Squad)
  2. 验证: 底部面板显示 Unit A 信息
  3. 验证: 射程圈显示 Unit A 的武器射程
  4. 左键单击 Unit B (MG Team, 在视野内)
  5. 验证:
     a. 选中框从 Unit A 转移到 Unit B
     b. 底部面板立即更新为 Unit B 信息
     c. 射程圈更新为 Unit B 的射程 (可能不同)
     d. 如果 Unit B 是友军: 显示其状态
     e. 如果 Unit B 是敌军: 可能显示 "?" (未知信息)
  6. 左键单击地图空白处
  7. 验证: 取消所有选中, 底部面板清空或显示通用信息

预期结果:
  ✅ 切换响应 < 0.1秒
  ✅ 信息更新准确无误
  ✅ 射程圈动态调整
  ✅ 敌我识别正确
  ✅ 取消选中工作正常

失败判定:
  ❌ 切换延迟 > 0.5秒
  ❌ 信息更新滞后或错误
  ❌ 射程圈未更新
  ❌ 敌友识别混乱
```

### 场景5: 小地图交互
```
操作序列:
  1. 观察右下角小地图
  2. 验证: 己方单位显示为绿点/蓝点
  3. 验证: 敌方单位 (已发现) 显示为红点
  4. 验证: 未发现区域显示为黑色/战争迷雾
  5. 左键单击小地图某个位置
  6. 验证: 大地图相机移动到该位置 (居中显示)
  7. 点击小地图 +/- 缩放按钮
  8. 验证: 大地图缩放级别改变

预期结果:
  ✅ 小地图反映真实状态
  ✅ 点击定位准确
  ✅ 缩放功能正常

失败判定:
  ❌ 小地图与实际不符
  ❌ 点击定位偏移
  ❌ 缩放无效或崩溃
```

### 场景6: 存档/读档循环
```
操作序列:
  1. 战斗进行中 (已有一些操作历史)
  2. 点击 "Save Game" 按钮 (或按 F5)
  3. 验证: 存档对话框出现 (或自动存档到Slot 0)
  4. 验证: 存档时间戳显示
  5. 退出游戏 (Alt+F4 或菜单退出)
  6. 重新启动游戏
  7. 点击 "Load Game"
  8. 选择刚才的存档
  9. 验证:
     a. 加载成功 (< 3秒)
     b. 所有单位位置/状态/HP/弹药完全恢复
     c. 时间/天气/战役进度一致
     d. 可继续操作 (不会卡死/崩溃)

预期结果:
  ✅ 存档文件生成 (可检查 saves/ 目录)
  ✅ 读档后状态100%一致
  ✅ 无数据损坏/丢失

失败判定:
  ❌ 存档文件未生成
  ❌ 读档后状态不一致
  ❌ 数据损坏 (JSON解析错误)
  ❌ 读档后崩溃
```

### 场景7: 胜利/失败结束
```
操作序列 (胜利场景):
  1. 全歼敌方单位 (或达成胜利条件)
  2. 验证:
     a. 战斗暂停/冻结
     b. 胜利界面弹出 ("VICTORY!" 文字)
     c. AAR面板显示 (统计: 我方损失/敌方损失/用时/accuracy)
     d. "Continue" 按钮 (进入下一场或返回战略地图)
  3. 点击 Continue
  4. 验证: 回到战略地图或下一场Battle准备

操作序列 (失败场景):
  1. 我方指挥官阵亡 / 全军覆没 / 士气崩溃
  2. 验证:
     a. 失败界面弹出 ("DEFEAT" 文字)
     b. AAR面板显示 (即使失败也有统计)
     c. "Retry" / "Load Save" / "Quit" 选项
  4. 选择 Retry
  5. 验证: 重新开始当前Battle (初始部署阶段)

预期结果:
  ✅ 胜负判定正确 (不会误判)
  ✅ 结果界面美观 (不简陋)
  ✅ AAR数据准确
  ✅ 后续流程通畅

失败判定:
  ❌ 胜负误判 (应胜判败/反之)
  ❌ 结果界面缺失或丑陋
  ❌ AAR数据错误
  ❌ Continue/Retry导致崩溃
```

---

## 二、自动化测试实现方案

### 2.1 pytest-playwright 用于UI交互
```python
# tests/e2e/test_user_scenarios.py
import pytest
from pygame import display, event
from time import sleep

class TestUserScenarioNewGame:
    def test_new_game_complete_flow(self, pygame_env):
        """场景1: 新游戏完整流程"""
        game = GameLoop()
        game.init()

        # Step 1: 等待主菜单
        assert game.current_state == GameState.MAIN_MENU
        assert game.main_menu.visible == True

        # Step 2: 点击 New Campaign
        game.handle_click(NEW_CAMPAIGN_BUTTON_POS)
        assert game.current_state == GameState.FACTION_SELECT

        # Step 3: 选择阵营
        game.handle_click(ALLIES_FACTION_POS)
        assert game.selected_faction == Faction.ALLIES

        # Step 4: 选择难度
        game.handle_click(DIFFICULTY_NORMAL_POS)
        assert game.difficulty == Difficulty.NORMAL

        # Step 5: 开始战役
        game.handle_click(START_BUTTON_POS)
        assert game.current_state == GameState.STRATEGIC_MAP
        assert game.campaign.active == True

        game.shutdown()

class TestUserScenarioCombatCommands:
    def test_move_command_full_sequence(self, combat_env):
        """场景3.1: Move命令完整序列"""
        battle = create_test_battle()

        # 选中单位
        unit = battle.player_units[0]
        battle.select_unit(unit)
        assert unit.is_selected == True
        assert battle.ui.bottom_panel.shows_unit(unit) == True

        # 右键菜单
        menu = battle.context_menu.show(battle.mouse_pos)
        assert "Move" in menu.items
        assert menu.items["Move"].enabled == True

        # 执行Move
        target_pos = (unit.position[0] + 3, unit.position[1])
        battle.execute_command("move", target_pos)

        # 验证移动
        assert unit.target_position == target_pos
        assert unit.state == State.MOVING

        # 等待移动完成 (模拟)
        for _ in range(60):  # 3秒 @ 20fps
            battle.update(1/20)

        assert unit.position == target_pos  # 到达目标
        assert unit.state == State.IDLE         # 停止

    def test_attack_command_with_visual_feedback(self, combat_env):
        """场景3.4: Attack命令+完整视觉反馈"""
        battle = create_test_battle_with_enemy()
        attacker = battle.player_units[0]
        target = battle.enemy_units[0]

        # 选中→攻击
        battle.select_unit(attacker)
        battle.execute_command("attack", target.position)

        # 验证攻击链
        assert attacker.target == target
        assert attacker.state == State.ATTACKING

        # 模拟攻击结算
        for _ in range(30):  # 1.5秒
            battle.update(1/20)

        # 验证伤害
        assert target.hp < target.max_hp  # HP减少了
        assert attacker.ammo == attacker.ammo - 1  # 弹药-1

        # 验证日志
        last_log = battle.combat_log.last_entry
        assert "attack" in last_log.lower() or "hit" in last_log.lower()

    def test_all_seven_commands_respond(self, combat_env):
        """验证7个命令都能响应"""
        commands = ["move", "fast_move", "sneak", "attack",
                    "smoke", "defend", "hide"]
        battle = create_test_battle()
        unit = battle.player_units[0]

        for cmd in commands:
            battle.select_unit(unit)
            # 检查命令是否在菜单中
            menu = battle.get_context_menu(unit)
            assert cmd in [item.id for item in menu.available_items], \
                   f"Command '{cmd}' missing from context menu"

            # 尝试执行 (如果可执行的话)
            if menu.is_command_available(cmd):
                result = battle.try_execute_command(cmd, get_target_for(cmd))
                assert result.success == True, \
                       f"Command '{cmd}' execution failed: {result.error}"
```

### 2.2 视觉回归测试 (Screenshot Comparison)
```python
# tests/visual/test_visual_regression.py
import pytest
from PIL import Image, ImageChops

@pytest.mark.visual
def test_unit_selection_highlight():
    """选中单位的视觉反馈"""
    game = setup_battle_scene()
    unit = game.player_units[0]

    # 选中前截图
    before = game.screenshot()

    # 选中
    game.select_unit(unit)

    # 选中后截图 (等待渲染)
    game.render_frame()
    after = game.screenshot()

    # 比较: 选中框区域应该不同
    bbox = unit.screen_rect.inflate(4, 4)  # 选中框范围
    diff = ImageChops.diff(before.crop(bbox), after.crop(bbox))
    assert diff.getbbox() is not None, "No visual change on selection!"

@pytest.mark.visual
def test_attack_muzzle_flash():
    """攻击时的枪口火焰"""
    game = setup_battle_scene()
    attacker, target = setup_attack_pair()

    game.select_unit(attacker)
    game.execute_attack(target)

    # 在攻击帧截图
    flash_frame = game.capture_frame_at_time(attack_time + 0.05)

    # 检查枪口位置有亮点 (黄色/白色)
    muzzle_pos = attacker.get_muzzle_screen_pos()
    pixel_color = flash_frame.getpixel(muzzle_pos)

    assert is_bright_pixel(pixel_color), \
           f"Muzzle flash not visible at {muzzle_pos}, color={pixel_color}"

@pytest.mark.visual
def test_8_direction_distinctiveness():
    """8方向精灵差异性测试"""
    from PIL import ImageChops

    directions = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw']
    sprites = []

    for dir in directions:
        sprite = load_sprite(f"allies_rifleman_{dir}_idle_0.png")
        sprites.append(sprite)

    # 相邻方向差异必须 >30%
    for i in range(len(directions)):
        next_i = (i + 1) % len(directions)
        diff = ImageChops.diff(sprites[i], sprites[next_i])
        diff_bbox = diff.getbbox()

        if diff_bbox is None:
            # 完全相同, 失败!
            assert False, f"Directions {directions[i]} and {directions[next_i]} are identical!"

        # 计算差异像素比例
        diff_pixels = sum(1 for p in diff.getdata() if p != (0, 0, 0, 0))
        total_pixels = sprites[i].size[0] * sprites[i].size[1]
        diff_ratio = diff_pixels / total_pixels

        assert diff_ratio > 0.30, \
               f"Directions {directions[i]} and {directions[next_i]} too similar: {diff_ratio:.1%} diff"

@pytest.mark.visual
def test_realistic_not_geometric():
    """验证精灵不是简单几何形状"""
    sprite = load_sprite("allies_rifleman_n_idle_0.png")

    # 转换为numpy数组分析
    import numpy as np
    arr = np.array(sprite)

    # 检查颜色多样性 (几何形状通常只有1-3种颜色)
    unique_colors = len(set(tuple(pixel) for row in arr for pixel in row if pixel[3] > 0))

    assert unique_colors >= 5, \
           f"Sprite looks geometric (only {unique_colors} colors). Need ≥5 for realistic style."

    # 检查边缘复杂度 (几何形状边缘平滑)
    # 这里简化检查: 真实像素艺术应该有不规则边缘
    edges = detect_edges(arr)
    edge_complexity = calculate_edge_irregularity(edges)

    assert edge_complexity > 0.3, \
           f"Edge too regular ({edge_complexity:.2f}). Looks like geometric shape."
```

### 2.3 性能基准测试
```python
# tests/benchmark/test_performance.py
import pytest
import time

class TestPerformanceBenchmarks:
    def test_startup_time(self):
        """启动时间 < 5秒"""
        start = time.time()
        game = GameLoop()
        game.init()
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Startup too slow: {elapsed:.1f}s (limit: 5s)"

    def test_render_fps_with_50_units(self):
        """50单位同屏 ≥ 20fps"""
        game = create_battle_with_n_units(50)
        game.start_rendering()

        frames = []
        start_time = time.time()
        test_duration = 5.0  # 测试5秒

        while time.time() - start_time < test_duration:
            frame_start = time.time()
            game.render_frame()
            frame_end = time.time()
            frames.append(frame_end - frame_start)

        avg_frame_time = sum(frames) / len(frames)
        fps = 1.0 / avg_frame_time

        assert fps >= 20, f"FPS too low with 50 units: {fps:.1f} (min: 20)"

    def test_save_load_time(self):
        """存档/读档 < 3秒"""
        game = create_mid_battle_state()

        # 测试存档
        save_start = time.time()
        game.save("test_slot")
        save_time = time.time() - save_start

        assert save_time < 2.0, f"Save too slow: {save_time:.1f}s"

        # 测试读档
        load_start = time.time()
        loaded_game = GameLoop.load("test_slot")
        load_time = time.time() - load_start

        assert load_time < 3.0, f"Load too slow: {load_time:.1f}s"
```

---

## 三、测试覆盖矩阵 (Test Coverage Matrix)

### 用户操作 × 系统响应 矩阵

| 用户操作 | UI响应 | 模型更新 | 视觉反馈 | 音效 | 日志 | 测试优先级 |
|---------|--------|---------|---------|------|------|-----------|
| 左键选单位 | 选中框+详情面板 | selected=True | 高亮动画 | 选中音? | "Selected X" | P0 |
| 右键地面 | 上下文菜单弹出 | - | 菜单动画 | 菜单音 | - | P0 |
| Move命令 | 路径预览 | target=set | 移动动画 | 命令确认音 | "Move to X" | P0 |
| Fast Move | 快速路径预览 | mode=fast | 跑步动画 | 急促脚步声 | "Fast move" | P1 |
| Sneak | 潜行路径 | mode=stealth | 爬行动画 | 无声 | "Sneaking" | P1 |
| Attack(敌军) | 攻击线+准星 | target=enemy | 射击动画+特效 | 枪声 | "Attacking X" | P0 |
| Attack(超出射程) | 红色X或灰化 | - | 错误提示 | 错误音 | "Out of range" | P0 |
| Smoke | 投掷预览 | ammo-- | 投掷动画 | 引信声 | "Smoke at X" | P1 |
| Dig In | 防御图标 | mode=dig | 蹲下动画 | 铲铲声 | "Digging in" | P1 |
| Hide | 掩体高亮 | target=cover | 移动到掩体 | 悄息声 | "Taking cover" | P1 |
| 切换单位 | 选中框转移 | 新单位数据 | 面板切换 | - | - | P0 |
| 小地图点击 | 相机移动 | camera.pos= | 地图滚动 | - | - | P1 |
| Save | 存档对话框 | save_file.write() | 保存动画 | 硬盘写入音 | "Game saved" | P0 |
| Load | 读档对话框 | load_file.read() | 加载动画 | 硬盘读取音 | "Game loaded" | P0 |
| Pause | 暂停覆盖层 | paused=True | 时间停止 | 暂停音 | "Paused" | P1 |
| 胜利 | Victory界面 | game_over=victory | 庆祝动画 | 胜利音乐 | "Victory!" | P0 |
| 失败 | Defeat界面 | game_over=defeat | 失败动画 | 失败音乐 | "Defeat" | P0 |

**P0项必须100%通过才能发布**
**P1项应在首次发布前修复**

---

## 四、手动测试检查清单 (Manual QA Checklist)

### 每次代码提交前必须人工验证:

#### 启动与基本功能
- [ ] **启动测试**: 游戏能在macOS/Windows/Linux启动无报错
- [ ] **启动时间**: 主菜单在5秒内出现
- [ ] **控制台清洁**: 无Python异常/pygame错误输出

#### 新游戏流程
- [ ] **新游戏**: 完整走完新游戏流程 (菜单→选阵营→开始)
- [ ] **按钮响应**: 所有按钮有hover/click视觉反馈
- [ ] **加载性能**: 战役加载 < 3秒

#### 部署阶段
- [ ] **拖拽操作**: 至少拖放3个单位, 验证放置规则
- [ ] **RP系统**: RP计数准确增减
- [ ] **边界检查**: 无法在敌方区域放置单位

#### 战斗核心操作 (7命令逐一验证!)
- [ ] **Move命令**: 单位平滑移动, 动画正确, 方向匹配
- [ ] **Fast Move**: 速度明显加快, 有疲劳/隐蔽惩罚
- [ ] **Sneak**: 速度降低, 隐蔽提升, 视觉可区分
- [ ] **Attack**: 完整视觉链路 (动画+特效+伤害+日志)
- [ ] **Smoke**: 烟雾可见, LOS阻断, 持续时间正确
- [ ] **Dig In**: 姿态改变, 防护提升, 战壕可视化
- [ ] **Hide**: 自动找掩体, 状态可视, 可取消

#### 单位管理
- [ ] **单位切换**: 点击5个不同单位, 确认面板每次更新
- [ ] **射程圈**: 切换单位时射程圈动态调整
- [ ] **敌我识别**: 友军/敌军/未知状态正确显示

#### 地图与相机
- [ ] **小地图**: 反映真实状态, 点击定位准确
- [ ] **缩放**: +/- 按钮有效, 不崩溃
- [ ] **拖动**: 可拖动大地图平移

#### 存档系统
- [ ] **存档循环**: 存档→退出→重启→读档, 状态100%一致
- [ ] **存档速度**: 存档 < 2秒, 读档 < 3秒
- [ ] **多存档**: 支持多个存档槽位

#### 结束流程
- [ ] **胜利条件**: 全歼敌人或达成目标触发胜利
- [ ] **失败条件**: 指挥官阵亡/全军覆没触发失败
- [ ] **AAR面板**: 统计数据准确完整
- [ ] **后续流程**: Continue/Retry/Quit均正常

#### 性能与稳定性
- [ ] **帧率观察**: 运行5分钟无严重掉帧 (<20fps)
- [ ] **内存稳定**: 无明显内存泄漏增长
- [ ] **极端情况**: 50单位同屏不崩溃

#### 视觉质量 (新! 与UI_REALISTIC_PIXEL_SPEC联动)
- [ ] **精灵写实性**: 步兵/载具不是几何形状, 有人体结构
- [ ] **8方向差异**: 盲测步兵8方向准确率 >90%
- [ ] **动画流畅**: 待机/行走/射击/死亡动画流畅自然
- [ ] **军事风格**: 配色符合二战军事写实风格
- [ ] **细节丰富**: 32×32内有足够细节 (非纯色块)
- [ ] **透明背景**: 精灵无白边/毛刺

### 每周全面测试 (CI/CD集成):

- [ ] **完整战役**: 连续玩3场Battle (Day1→Day2→Day3)
- [ ] **全兵种测试**: 使用所有兵种类型 (步枪/机枪/反坦克/军官等)
- [ ] **全载具测试**: 使用所有载具类型 (坦克/半履带/吉普等)
- [ ] **极端情况**: 50单位同屏 / 最快速度 / 最慢速度
- [ ] **错误输入**: 快速乱点键盘鼠标 / 断网 / 窗口resize
- [ ] **长时间运行**: 连续运行1小时无内存泄漏
- [ ] **跨平台**: macOS + Windows + Linux均可运行

### 发布前最终验收 (Release Criteria):

**硬性指标 (必须全部通过)**:
- [ ] P0测试用例 100% 通过率
- [ ] P1测试用例 ≥95% 通过率
- [ ] 启动时间 < 5秒
- [ ] 存档/读档 < 3秒
- [ ] 50单位同帧 ≥ 20fps
- [ ] CC2老玩家评分 ≥7.3/10 (UI_REALISTIC_PIXEL_SPEC标准)
- [ ] 8方向盲测准确率 >90%
- [ ] 零Critical/High级别Bug

**软性指标 (建议达成)**:
- [ ] P1测试用例 100% 通过率
- [ ] CC2老玩家评分 ≥8.0/10
- [ ] 用户满意度调查 ≥4.0/5.0
- [ ] 平均会话时长 > 30分钟 (说明有吸引力)

---

## 五、缺陷分级与响应流程

### Bug严重等级定义

#### P0 - Critical (发布阻断器)
```
定义: 导致无法进行游戏或数据丢失的问题
示例:
  - 游戏无法启动
  - 存档损坏无法读取
  - 核心命令(如Attack)完全无效
  - 崩溃/闪退
响应时间: 立即修复 (≤4小时)
发布影响: 必须修复才能发布
```

#### P1 - High (重要功能失效)
```
定义: 核心功能可用但有明显缺陷
示例:
  - Attack命令无视觉反馈
  - 移动方向与朝向不符
  - 死亡后仍可控
  - 弹药不消耗
响应时间: 24小时内修复
发布影响: 强烈建议修复后发布
```

#### P2 - Medium (功能异常但不阻塞)
```
定义: 功能可用但体验不佳
示例:
  - 某些方向相似度高 (>70%相同)
  - UI响应稍慢 (>0.3秒)
  - 特效偶尔不显示
  - 小地图轻微偏移
响应时间: 本周内修复
发布影响: 可带已知问题发布, 但需记录
```

#### P3 - Low (优化项/锦上添花)
```
定义: 不影响功能的改进建议
示例:
  - 动画可以更流畅
  - 配色可以更美观
  - 可以添加更多粒子效果
  - 加载时间可以更快
响应时间: 下个版本迭代
发布影响: 不影响发布
```

### Bug报告模板
```markdown
## Bug报告

**标题**: [P0/P1/P2/P3] 简短描述

**重现步骤**:
1. ...
2. ...
3. ...

**预期结果**:
...

**实际结果**:
...

**环境**:
- OS: macOS 14.0 / Windows 11 / Ubuntu 22.04
- Python: 3.11.x
- Pygame: 2.5.x
- 分辨率: 1920×1080

**截图/录屏**:
[附图]

**复现频率**:
□ 总是复现 (100%)
□ 经常复现 (>50%)
□ 偶尔复现 (<50%)
□ 很难复现 (<10%)

**日志输出**:
\```
(paste console output here)
\```

**相关测试用例**:
- test_xxx.py::test_yyy
```

---

## 六、持续集成配置

### GitHub Actions 工作流示例
```yaml
# .github/workflows/e2e_tests.yml
name: E2E User-Centric Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  user-scenario-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e ".[dev,test]"
        pip install pytest-playwright
        playwright install-deps

    - name: Run P0 tests (Critical path)
      run: |
        pytest tests/e2e/test_user_scenarios.py -k "p0 or critical" -v --tb=short
      env:
        PYTEST_TIMEOUT: 300

    - name: Run visual regression tests
      run: |
        pytest tests/visual/test_visual_regression.py -v --tb=short

    - name: Run performance benchmarks
      run: |
        pytest tests/benchmark/test_performance.py -v --tb=short

    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: |
          test-results/
          screenshots/
```

---

## 七、测试数据管理

### 测试存档 fixtures
```python
# tests/fixtures/test_saves/
"""
预构建的测试存档, 用于各种场景:

test_deployment_phase.json   - 部署阶段初始状态
test_mid_battle.json         - 战斗中途 (双方各有伤亡)
test_near_victory.json       - 接近胜利 (敌方仅剩1单位)
test_near_defeat.json        - 接近失败 (我方仅剩指挥官)
test_large_scale.json        - 大规模战斗 (50单位)
test_night_battle.json       - 夜间战斗 (低 visibility)
test_rainy_weather.json      - 雨天 (影响移动和视线)
"""
```

### 测试地图 fixtures
```python
# tests/fixtures/test_maps/
"""
特殊测试地图:

open_field.json              - 开阔地 (无掩体)
urban_combat.json            - 城市巷战 (多建筑)
bridge_crossing.json         - 桥梁争夺战
forest_ambush.json           - 森林伏击 (高树篱)
bocage_hell.json             - 诺曼底树篱地狱 (密集树篱)
river_defense.json           - 河流防御 (需要桥梁)
"""
```

---

*文档作者: DevSquad Test Expert + UX Specialist*
*版本: v2.0 (User-Centric)*
*重点: 7命令全测 + 用户操作视角 + 视觉反馈验证 + 写实精灵验收*
*配套文档*: UI_REALISTIC_PIXEL_SPEC.md (视觉规范)
*下次更新*: Phase 1精灵制作完成后补充具体测试脚本
