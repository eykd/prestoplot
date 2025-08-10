import pathlib
from typing import Final

from prestoplot import texts

PATH: Final[pathlib.Path] = pathlib.Path(__file__).parent

DATA: Final[pathlib.Path] = PATH / 'data'


def test_text_indeterminate_article_a() -> None:
    text = texts.Text('foo', 'path', {})
    assert text.a == 'a'
    assert text.an == 'a'


def test_text_indeterminate_article_an() -> None:
    text = texts.Text('ollie', 'path', {})
    assert text.a == 'an'
    assert text.an == 'an'


def test_renderable_text_indeterminate_article_a() -> None:
    text = texts.RenderableText('foo', 'path', {})
    assert text.a == 'a'
    assert text.an == 'a'


def test_renderable_text_indeterminate_article_an() -> None:
    text = texts.RenderableText('ollie', 'path', {})
    assert text.a == 'an'
    assert text.an == 'an'
