import pathlib

from prestoplot import seeds, storages, story

PATH = pathlib.Path(__file__).parent

DATA = PATH / "data"


def test_it_should_generate_a_stable_story_with_seed():
    storage = storages.FileStorage(DATA)
    result = story.render_story(storage, "characters", seed="testing")
    expected = (
        "Our hero, Owenry, is a flashing-eyed, erring explorer, "
        "subjected to adverse conditions. He carries a whip."
    )
    assert result == expected

    result = story.render_story(storage, "characters", seed="testing")
    expected = (
        "Our hero, Owenry, is a flashing-eyed, erring explorer, "
        "subjected to adverse conditions. He carries a whip."
    )
    assert result == expected


def test_it_should_generate_a_stable_story_with_seeded_rng():
    storage = storages.FileStorage(DATA)
    rng = seeds.get_rng("foo")
    result = story.render_story(storage, "characters", seed=rng)
    expected = (
        "Our hero, Carter, is a lithe, married scientist, subjected to "
        "adverse conditions. He carries a whip."
    )
    assert result == expected

    result = story.render_story(storage, "characters", seed=rng)
    expected = (
        "Our heroine, Avery, is a superbly fit, rifle-wielding millionaire, "
        "swayed by pretense. She carries a rifle."
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
