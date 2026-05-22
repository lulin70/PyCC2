# PyCC2 Assets Directory

此目录存放从Close Combat 2原版游戏提取的美术资源。

## 目录结构

```
assets/
├── sprites/
│   ├── units/
│   │   ├── allies/          # 盟军单位精灵
│   │   │   ├── infantry_squad_d0.png  (北)
│   │   │   ├── infantry_squad_d1.png  (东北)
│   │   │   ├── ...
│   │   │   └── infantry_squad_d7.png  (西北)
│   │   └── axis/            # 轴心国单位精灵
│   ├── vehicles/            # 载具精灵
│   └── effects/             # 特效精灵
└── terrain/
    ├── terrain_00.png       # 草地
    ├── terrain_01.png       # 道路
    └── ...
```

## 命名规范

### 单位精灵
格式: `{unit_type}_d{direction}.png`
- unit_type: infantry_squad, machine_gun_squad, commander, tank, sniper_team, medic_team
- direction: 0-7 (N, NE, E, SE, S, SW, W, NW)
- 尺寸: 128x128px (推荐)

### 地形tiles
格式: `terrain_{id:02d}.png`
- id: 00-13
- 尺寸: 32x32px 或 64x64px

### 特效精灵
格式: `{effect_name}_f{frame:02d}.png`
- effect_name: explosion, smoke, muzzle_flash, etc.
- frame: 动画帧索引 (00-99)

## 资源来源

1. **CC2原版游戏**: SteamUnlocked / GOG / Steam
2. **CC2Spriter工具**: closecombat2.hpage.com (v2.94)
3. **文档参考**:
   - CC2Guide-SpriteFiles-v9.zip
   - CC2Guide-Terrain-File-v5.pdf
   - CC2MapMuseum.zip

## 提取步骤

1. 下载CC2原版游戏
2. 运行提取脚本:
   ```bash
   python scripts/extract_cc2_assets.py --cc2-dir /path/to/cc2 --output assets/
   ```
3. 使用CC2Spriter手动转换.spr文件
4. 按命名规范组织文件

## Fallback机制

如果assets目录中没有对应资源，游戏会自动使用程序化生成的精灵（pixel_artist.py）。
这确保了即使没有原版资源，游戏也能正常运行。

## 版权说明

Close Combat 2资源版权归原开发商所有。
本项目仅用于学习和研究目的。
