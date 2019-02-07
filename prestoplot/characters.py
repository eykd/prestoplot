import random

import attr
import factory
from funcy import cached_property
import pycorpora

from . import data


@attr.s
class Character:
    context = attr.ib()
    sex = attr.ib()
    firstname = attr.ib()
    lastname = attr.ib()

    @cached_property
    def he(self):
        if self.sex == 'male':
            return 'he'
        elif self.sex == 'female':
            return 'she'
        else:
            return 'it'

    she = he

    @cached_property
    def He(self):
        return self.he.title()

    She = He

    @cached_property
    def him(self):
        if self.sex == 'male':
            return 'him'
        elif self.sex == 'female':
            return 'her'
        else:
            return 'it'

    her = him

    @cached_property
    def Him(self):
        return self.he.title()

    Her = Him


class CharacterFactory(factory.Factory):
    class Meta:
        model = Character
    context = None
    sex = factory.LazyAttribute(lambda o: random.choice(['male', 'female']))
    firstname = factory.LazyAttribute(
        lambda o: random.choice(
            data.get_female_names() if o.sex == 'female' else data.get_male_names()
        ))
    lastname = factory.LazyAttribute(lambda o: random.choice(pycorpora.humans.lastNames['lastNames']))
