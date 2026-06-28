from pathlib import Path


def test_frontend_api_base_url_is_env_driven():
    content = Path("frontend/src/api/index.js").read_text(encoding="utf-8")
    vite_config = Path("frontend/vite.config.js").read_text(encoding="utf-8")

    assert "VITE_API_BASE_URL" in content
    assert "|| '/api'" in content
    assert "VITE_BACKEND_URL" in vite_config
    assert "http://127.0.0.1:8010" in vite_config
    assert "strictPort: true" in vite_config
    assert "localhost:8002/api" not in content


def test_frontend_routes_are_sandbox_first():
    router = Path("frontend/src/router/index.js").read_text(encoding="utf-8")
    layout = Path("frontend/src/layouts/MainLayout.vue").read_text(encoding="utf-8")

    assert "path: ''" in router
    assert "component: SandboxView" in router
    assert "path: 'experiments'" in router
    assert "path: 'system'" in router
    assert "path: 'dev/modules/:moduleId?'" in router
    assert "path: 'preprocessing'" in router
    assert "redirect: '/'" in router
    assert "redirect: '/preprocessing'" not in router

    assert "实验沙盒" in layout
    assert "实验记录" in layout
    assert "系统状态" in layout
    assert "数据预处理" not in layout
    assert "感知 (Perception)" not in layout
    assert "决策 (Decision)" not in layout
    assert "规划 (Planning)" not in layout
