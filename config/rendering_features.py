"""渲染功能特性开关配置

统一管理所有增强渲染功能的feature flags。
可通过环境变量 PYCC2_ENHANCED_RENDERING 控制。

环境变量值：
- "all" 或 "1" 或 "true": 启用所有增强特性
- "terrain": 仅启用增强地形
- "particles": 仅启用增强粒子
- "postprocess": 仅启用增强后处理
- "ui": 仅启用增强UI
- "terrain,particles": 启用多个特性（逗号分隔）
- 空或其他: 使用默认配置
"""

import os


class RenderingFeatures:
    """渲染特性管理器"""

    def __init__(self):
        """从环境变量初始化feature flags"""
        env_var = os.environ.get("PYCC2_ENHANCED_RENDERING", "").lower()

        # 解析环境变量
        if env_var in ("all", "1", "true"):
            enabled_features = {"terrain", "particles", "postprocess", "ui"}
        elif env_var:
            enabled_features = set(f.strip() for f in env_var.split(","))
        else:
            # 默认配置：逐步启用（先地形和粒子，后处理和UI需要更多测试）
            enabled_features = set()  # 默认全部关闭，向后兼容

        # 设置各个feature flags
        self.USE_ENHANCED_TERRAIN = "terrain" in enabled_features
        self.USE_ENHANCED_PARTICLES = "particles" in enabled_features
        self.USE_ENHANCED_POST_PROCESSING = "postprocess" in enabled_features
        self.USE_ENHANCED_UI = "ui" in enabled_features

    def get_status(self) -> dict[str, bool]:
        """获取所有特性状态"""
        return {
            "enhanced_terrain": self.USE_ENHANCED_TERRAIN,
            "enhanced_particles": self.USE_ENHANCED_PARTICLES,
            "enhanced_post_processing": self.USE_ENHANCED_POST_PROCESSING,
            "enhanced_ui": self.USE_ENHANCED_UI,
        }

    def enable_all(self) -> None:
        """启用所有增强特性（用于测试）"""
        self.USE_ENHANCED_TERRAIN = True
        self.USE_ENHANCED_PARTICLES = True
        self.USE_ENHANCED_POST_PROCESSING = True
        self.USE_ENHANCED_UI = True

    def disable_all(self) -> None:
        """禁用所有增强特性（回退到旧版本）"""
        self.USE_ENHANCED_TERRAIN = False
        self.USE_ENHANCED_PARTICLES = False
        self.USE_ENHANCED_POST_PROCESSING = False
        self.USE_ENHANCED_UI = False


# 全局单例
_features = RenderingFeatures()


# 导出便捷访问
def is_enhanced_terrain_enabled() -> bool:
    """检查增强地形是否启用"""
    return _features.USE_ENHANCED_TERRAIN


def is_enhanced_particles_enabled() -> bool:
    """检查增强粒子是否启用"""
    return _features.USE_ENHANCED_PARTICLES


def is_enhanced_post_processing_enabled() -> bool:
    """检查增强后处理是否启用"""
    return _features.USE_ENHANCED_POST_PROCESSING


def is_enhanced_ui_enabled() -> bool:
    """检查增强UI是否启用"""
    return _features.USE_ENHANCED_UI


def get_features() -> RenderingFeatures:
    """获取全局特性管理器"""
    return _features


# 导出全局flags（向后兼容）
USE_ENHANCED_TERRAIN = _features.USE_ENHANCED_TERRAIN
USE_ENHANCED_PARTICLES = _features.USE_ENHANCED_PARTICLES
USE_ENHANCED_POST_PROCESSING = _features.USE_ENHANCED_POST_PROCESSING
USE_ENHANCED_UI = _features.USE_ENHANCED_UI


if __name__ == "__main__":
    # 测试和诊断

    print("PyCC2 Rendering Features Status")
    print("=" * 50)
    print(
        f"Environment: PYCC2_ENHANCED_RENDERING={os.environ.get('PYCC2_ENHANCED_RENDERING', '(not set)')}"
    )
    print()

    status = _features.get_status()
    for feature, enabled in status.items():
        symbol = "✓" if enabled else "✗"
        print(f"  {symbol} {feature}: {enabled}")

    print()
    print("Usage:")
    print("  export PYCC2_ENHANCED_RENDERING=all     # Enable all")
    print("  export PYCC2_ENHANCED_RENDERING=terrain,particles  # Enable specific")
    print("  unset PYCC2_ENHANCED_RENDERING          # Disable all (default)")
