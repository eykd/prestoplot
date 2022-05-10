from prestoplot import markov, seeds

NAMES = [
    "Noah",
    "Liam",
    "William",
    "Mason",
    "James",
    "Benjamin",
    "Jacob",
    "Michael",
    "Elijah",
    "Ethan",
    "Alexander",
    "Oliver",
    "Daniel",
    "Lucas",
    "Matthew",
    "Aiden",
    "Jackson",
    "Logan",
    "David",
    "Joseph",
    "Samuel",
    "Henry",
    "Owen",
    "Sebastian",
    "Gabriel",
    "Carter",
    "Jayden",
    "John",
    "Luke",
    "Anthony",
    "Isaac",
    "Dylan",
    "Wyatt",
    "Andrew",
    "Joshua",
    "Christopher",
    "Grayson",
    "Jack",
    "Julian",
    "Ryan",
    "Jaxon",
    "Levi",
    "Nathan",
]


def test_it_should_generate_stable_names_from_seed():
    gen = markov.NameGenerator(NAMES)

    result = gen.get_random_name(seed="foo")
    assert result == "Anden"

    result = gen.get_random_name(seed="foo")
    assert result == "Anden"


def test_it_should_generate_stable_names_with_seeded_rng():
    gen = markov.NameGenerator(NAMES)
    rng = seeds.get_rng("foo")

    result = gen.get_random_name(seed=rng)
    assert result == "Anden"

    result = gen.get_random_name(seed=rng)
    assert result == "Andrew"
