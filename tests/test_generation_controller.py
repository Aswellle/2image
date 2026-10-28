"""单图生成在飞防重与主按钮调度语义测试。

历史缺陷：generate() 无在飞守卫，Ctrl+R / 重新生成按钮可并发派生第二个
worker 覆写取消令牌与批次参数；cancel_generation 定义后无任何调用方。
"""

from unittest.mock import MagicMock

from services.application.generation_controller import GenerationController


def make_controller():
    app = MagicMock()
    return GenerationController(app), app


def test_generate_or_cancel_dispatches_by_state():
    controller, _ = make_controller()
    controller.generate = MagicMock()

    controller.generate_or_cancel()
    controller.generate.assert_called_once()

    controller.cancel_generation = MagicMock()
    controller._running = True
    controller.generate_or_cancel()
    controller.cancel_generation.assert_called_once()
    # 仍在运行：不得再次触发新的生成
    controller.generate.assert_called_once()


def test_generate_blocked_while_running():
    controller, app = make_controller()
    controller._running = True

    controller.generate()

    # 在飞期间不得触碰任何 UI 状态（否则会覆写进行中的批次参数）
    app.content.pt.get.assert_not_called()
    app._batch_params = None
    assert app._batch_params is None


def test_cancel_generation_cancels_active_token():
    controller, _ = make_controller()
    token = MagicMock()
    controller._cancel_token = token

    controller.cancel_generation()
    token.cancel.assert_called_once()


def test_cancel_without_token_is_noop():
    controller, _ = make_controller()
    controller._cancel_token = None
    controller.cancel_generation()  # 不得抛异常
