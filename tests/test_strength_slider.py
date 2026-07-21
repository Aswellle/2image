import tkinter as tk

from config.fonts import init_fonts
from ui.main_content import _StrengthSlider


class DrawCanvas:
    def __init__(self):
        self.texts = []

    def delete(self, *_args):
        pass

    def create_rectangle(self, *_args, **_kwargs):
        pass

    def create_oval(self, *_args, **_kwargs):
        pass

    def create_line(self, *_args, **_kwargs):
        pass

    def create_text(self, *_args, **kwargs):
        self.texts.append(kwargs["text"])


def test_compact_strength_slider_hides_internal_value_label():
    slider = _StrengthSlider.__new__(_StrengthSlider)
    slider.W = 120
    slider.H = 30
    slider.TX = 10
    slider.TW = 100
    slider.TY = 12
    slider.TH = 5
    slider.HR = 7
    slider.marks = False
    slider.var = type("Strength", (), {"get": lambda _self: 0.6})()
    slider.cv = DrawCanvas()
    slider._gradient = ["#1d4ed8", "#7c3aed", "#dc2626"]

    slider._draw()

    assert slider.cv.texts == []


def test_full_strength_slider_shows_internal_value_and_marks():
    init_fonts()
    root = tk.Tk()
    root.withdraw()
    slider = _StrengthSlider(root, tk.DoubleVar(value=0.6), marks=True)
    root.update_idletasks()

    items = [
        slider.cv.itemcget(item, "text")
        for item in slider.cv.find_all()
        if slider.cv.type(item) == "text"
    ]
    assert "0.6" in items
    assert {"微调", "融合", "重构"}.issubset(items)

    root.destroy()
