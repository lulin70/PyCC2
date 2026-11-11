# PyCC2 P0-2 UI/UX Improvement Plan

**Date**: 2026-11-02  
**Status**: 🚧 IN PROGRESS  
**Methodology**: DevSquad Multi-Role Collaboration + User Journey Testing

---

## Task Overview

实现三大UI组件提升PyCC2用户体验：
1. **Minimap** - 战术概览地图
2. **Status Bar** - 实时状态显示（FPS + 单位信息）
3. **Keyboard Shortcuts** - 快捷键系统

**Quality Gates**:
- ✅ Visual Verification: 每个组件完成后截图验证
- ✅ User Journey Testing: 模拟真实玩家操作流程
- ✅ Integration Testing: 与Phase 2精灵系统无缝集成

---

## DevSquad Role Assignment

### 🎨 UI Designer
**Responsibilities**:
- Minimap视觉设计（位置、尺寸、颜色方案）
- Status Bar布局设计（信息优先级、字体、对比度）
- Keyboard Shortcuts提示UI设计

**Deliverables**:
- Figma风格mockup（ASCII art or description）
- Color palette定义
- Typography specifications

---

### 🏗️ Architect
**Responsibilities**:
- UI组件架构设计（Renderer集成点）
- 渲染层次规划（UI层 vs Game层分离）
- 性能考量（UI渲染不影响主循环FPS）

**Deliverables**:
- Component architecture diagram
- Integration points with EnhancedRenderer
- Performance budget allocation

---

### 💻 Solo-Coder
**Responsibilities**:
- 实现MinimapRenderer组件
- 实现StatusBarRenderer组件
- 实现KeyboardShortcutManager组件
- 集成到EnhancedRenderer

**Deliverables**:
- Working code (3 new modules)
- Integration code (EnhancedRenderer updates)
- Inline documentation

---

### 🧪 Tester
**Responsibilities**:
- 设计User Journey测试用例
- 执行截图验证（每个组件完成后）
- 集成测试验证（与Phase 2精灵）

**Deliverables**:
- Test plan document
- Screenshot evidence collection
- Integration test report

---

## User Journey Test Scenarios

### Journey 1: 新玩家首次游戏 (First-Time Player)
```
1. 启动游戏 → 看到Status Bar显示FPS和游戏状态
2. 点击单位 → Status Bar显示单位详情（HP、武器、状态）
3. 按Tab键 → 快速切换到下一个单位
4. 看Minimap → 理解战场全局态势
5. 点击Minimap → 相机跳转到对应位置
```

**Expected Experience**:
- Status Bar信息清晰易读
- Minimap响应灵敏
- 快捷键提示可见

---

### Journey 2: 中级玩家战术操作 (Tactical Gameplay)
```
1. 按Space暂停游戏 → Status Bar显示"PAUSED"
2. 拖动Minimap → 快速侦察地图
3. 按1-9数字键 → 快速选择编组单位
4. 按Shift+右键 → 设置移动路径点
5. 观察Minimap → 敌军位置显示为红点
```

**Expected Experience**:
- 暂停/恢复流畅无延迟
- Minimap视野范围清晰标注
- 编组快捷键响应即时

---

### Journey 3: 高级玩家性能测试 (Performance Under Load)
```
1. 加载大地图（100+ units）
2. 观察Status Bar的FPS显示
3. 快速拖动Minimap → FPS不应下降
4. 连续按Tab切换单位 → 无卡顿
5. 同时移动多个单位 → Minimap实时更新
```

**Expected Experience**:
- FPS保持在30+
- Minimap更新不影响主渲染
- UI响应时间 < 16ms (60 FPS)

---

## Visual Verification Checklist

### Minimap Component ✅
- [ ] Screenshot 1: Minimap显示完整地图
- [ ] Screenshot 2: 玩家单位显示为蓝点
- [ ] Screenshot 3: 敌方单位显示为红点
- [ ] Screenshot 4: 当前视野框显示为黄色矩形
- [ ] Screenshot 5: 点击Minimap后相机正确跳转

### Status Bar Component ✅
- [ ] Screenshot 1: 默认状态（FPS + 回合数 + 资源）
- [ ] Screenshot 2: 选中单位后显示单位详情
- [ ] Screenshot 3: 暂停状态显示"PAUSED"
- [ ] Screenshot 4: 低FPS警告（FPS < 15时红色高亮）
- [ ] Screenshot 5: 单位血量低于30%时红色警告

### Keyboard Shortcuts Component ✅
- [ ] Screenshot 1: 按H键显示快捷键帮助
- [ ] Screenshot 2: 快捷键提示覆盖层设计
- [ ] Screenshot 3: 按Esc关闭帮助
- [ ] Screenshot 4: Space暂停游戏视觉反馈
- [ ] Screenshot 5: Tab切换单位高亮效果

---

## Integration Testing with Phase 2 Sprites

### Test Case 1: Minimap显示Phase 2精灵单位
```python
# 验证：Minimap上的单位图标使用Phase 2精灵的缩略图
# Expected: 步兵显示为小型rifleman图标，坦克显示为tank图标
```

### Test Case 2: Status Bar显示动画状态
```python
# 验证：Status Bar显示当前单位的动画状态（idle/walk/attack）
# Expected: 移动单位时显示"Moving"，攻击时显示"Attacking"
```

### Test Case 3: 快捷键触发动画切换
```python
# 验证：按快捷键切换单位时，AnimationController正确更新状态
# Expected: Tab切换后新单位立即播放正确动画
```

---

## Technical Specifications

### Minimap
```python
# Position: Bottom-right corner
# Size: 200x200 px (configurable)
# Update Rate: 10 FPS (independent of main loop)
# Zoom Level: Full map view with dynamic scaling
```

### Status Bar
```python
# Position: Top of screen (full width)
# Height: 40 px
# Sections:
#   - Left: FPS + Game Time
#   - Center: Selected Unit Info
#   - Right: Resources + Turn Number
```

### Keyboard Shortcuts
```python
# Core Shortcuts:
#   Space: Pause/Resume
#   Tab: Next Unit
#   Shift+Tab: Previous Unit
#   1-9: Select Unit Group
#   H: Show Help
#   Esc: Close Overlays
```

---

## Performance Budget

| Component | Frame Budget | Memory Budget |
|-----------|--------------|---------------|
| Minimap   | 2ms/frame    | 5MB          |
| Status Bar| 1ms/frame    | 1MB          |
| Shortcuts | 0.5ms/frame  | 0.5MB        |
| **Total** | **3.5ms/frame** | **6.5MB**  |

**Target**: Total UI overhead < 5ms/frame @ 60 FPS

---

## Next Steps

1. **UI Designer**: 提供Minimap和Status Bar的视觉mockup
2. **Architect**: 审查渲染架构并提供集成方案
3. **Solo-Coder**: 实现第一个组件（Minimap优先）
4. **Tester**: 准备截图验证环境并执行Journey 1

---

**DevSquad Collaboration Status**: 🟢 ACTIVE
