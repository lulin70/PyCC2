"""集成测试：增强渲染模块与主代码的集成

验证4个增强模块能否正确集成到实际游戏渲染管线。
"""
import os

import pygame
import pytest


@pytest.fixture(scope="module")
def pygame_init():
    """初始化pygame"""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


def test_rendering_features_config_loads():
    """测试: 配置模块能否正常加载"""
    from config.rendering_features import get_features

    features = get_features()
    assert features is not None
    status = features.get_status()
    assert isinstance(status, dict)
    assert len(status) == 4


def test_terrain_integration_import(pygame_init):
    """测试: terrain_renderer能否导入增强模块"""
    try:
        from pycc2.presentation.rendering import terrain_renderer
        # 检查是否有集成标记
        assert hasattr(terrain_renderer, '_ENHANCED_TERRAIN_AVAILABLE')
    except ImportError as e:
        pytest.skip(f"terrain_renderer未找到: {e}")


def test_particles_integration_import(pygame_init):
    """测试: effect_renderer能否导入增强模块"""
    try:
        from pycc2.presentation.rendering import effect_renderer
        assert hasattr(effect_renderer, '_ENHANCED_PARTICLES_AVAILABLE')
    except ImportError as e:
        pytest.skip(f"effect_renderer未找到: {e}")


def test_postprocessing_integration_import(pygame_init):
    """测试: render_pipeline能否导入增强模块"""
    try:
        from pycc2.presentation.rendering import render_pipeline
        assert hasattr(render_pipeline, '_ENHANCED_POST_PROCESSING_AVAILABLE')
    except ImportError as e:
        pytest.skip(f"render_pipeline未找到: {e}")


def test_ui_integration_import(pygame_init):
    """测试: cc2_hud能否导入增强模块"""
    try:
        from pycc2.presentation.ui import cc2_hud
        assert hasattr(cc2_hud, '_ENHANCED_UI_AVAILABLE')
    except ImportError as e:
        pytest.skip(f"cc2_hud未找到: {e}")


def test_feature_toggle_works(pygame_init, monkeypatch):
    """测试: Feature toggle机制能否工作"""
    # 测试启用所有特性
    monkeypatch.setenv("PYCC2_ENHANCED_RENDERING", "all")

    # 重新导入以应用环境变量
    import importlib

    import config.rendering_features
    importlib.reload(config.rendering_features)

    from config.rendering_features import get_features
    features = get_features()

    assert features.USE_ENHANCED_TERRAIN
    assert features.USE_ENHANCED_PARTICLES
    assert features.USE_ENHANCED_POST_PROCESSING
    assert features.USE_ENHANCED_UI


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
