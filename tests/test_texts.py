import pathlib

from prestoplot import texts

PATH = pathlib.Path(__file__).parent

DATA = PATH / "data"


def test_text_indeterminate_article_a():
    text = texts.Text("foo", "path", {})
    assert text.a == "a"
    assert text.an == "a"


def test_text_indeterminate_article_an():
    text = texts.Text("ollie", "path", {})
    assert text.a == "an"
    assert text.an == "an"


def test_renderable_text_indeterminate_article_a():
    text = texts.RenderableText("foo", "path", {})
    assert text.a == "a"
    assert text.an == "a"


def test_renderable_text_indeterminate_article_an():
    text = texts.RenderableText("ollie", "path", {})
    assert text.a == "an"
    assert text.an == "an"
