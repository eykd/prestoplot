import pathlib

from prestoplot import storages, story

PATH = pathlib.Path(__file__).parent

DATA = PATH / "data"


def test_render_story():
    storage = storages.FileStorage(DATA)
    result = story.render_story(storage, "characters", seed="testing")
    expected = (
        "Our hero, Noah, is a flashing-eyed, erring explorer, "
        "subjected to adverse conditions. He carries a whip."
    )
    assert result == expected


def test_render_story_jinja2():
    storage = storages.FileStorage(DATA)
    result = story.render_story(storage, "characters_jinja", seed="testing")
    expected = (
        "Our hero, Noah, is a flashing-eyed, erring explorer, "
        "subjected to adverse conditions. He carries a whip."
    )
    assert result == expected
