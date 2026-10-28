"""主窗口退出守卫测试。

历史缺陷：主窗口未注册 WM_DELETE_WINDOW 处理，生成/队列进行中
Alt+F4 直接销毁 Tk，守护线程随窗口静默消失，无任何确认。
"""

from unittest.mock import MagicMock, patch


def test_close_with_active_tasks_asks_and_aborts_on_no(app):
    real, _ = app
    real._has_active_tasks = MagicMock(return_value=True)
    with patch("ui.app.messagebox.askyesno", return_value=False) as ask, patch.object(real.root, "destroy") as destroy:
        real._on_close_request()
    ask.assert_called_once()
    destroy.assert_not_called()


def test_close_with_active_tasks_proceeds_on_yes(app):
    real, _ = app
    real._has_active_tasks = MagicMock(return_value=True)
    with patch("ui.app.messagebox.askyesno", return_value=True) as ask, patch.object(real.root, "destroy") as destroy:
        real._on_close_request()
    ask.assert_called_once()
    destroy.assert_called_once()


def test_close_without_tasks_destroys_without_asking(app):
    real, _ = app
    real._has_active_tasks = MagicMock(return_value=False)
    with patch("ui.app.messagebox.askyesno") as ask, patch.object(real.root, "destroy") as destroy:
        real._on_close_request()
    ask.assert_not_called()
    destroy.assert_called_once()


def test_has_active_tasks_reflects_controller_state(app):
    """主按钮在生成期保持可点（兼作取消），在飞探测须走控制器标志。"""
    real, _ = app
    real.gen_controller._running = True
    assert real._has_active_tasks() is True
    real.gen_controller._running = False
    assert real._has_active_tasks() is False
