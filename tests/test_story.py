import pathlib

from prestoplot import story

PATH = pathlib.Path(__file__).parent

DATA = PATH / 'data'


def test_render_story():
    result = story.render_story(DATA / 'characters.yaml', seed='testing')
    expected = ('Our hero, Noah, is a flashing-eyed, erring explorer, '
                'subjected to adverse conditions. He carries a whip.')
    assert result == expected
