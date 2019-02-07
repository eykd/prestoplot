import attr


@attr.s
class Character:
    designation = attr.ib()
    description = attr.ib()
    sex = attr.ib()


@attr.s
class AClause:
    number = attr.ib()
    clause = attr.ib()


@attr.s
class BClause:
    number = attr.ib()
    clause = attr.ib()
    links = attr.ib()


@attr.s
class CClause:
    number = attr.ib()
    clause = attr.ib()


@attr.s
class ConflictLinkGroup:
    links = attr.ib(default=attr.Factory(list))
    mode = attr.ib(default='choose')


@attr.s
class ConflictLink:
    id = attr.ib()
    transformations = attr.ib(default=attr.Factory(dict))
    additions = attr.ib(default=attr.Factory(list))
    eliminations = attr.ib(default=attr.Factory(list))
    permutations = attr.ib(default=attr.Factory(list))
    option = attr.ib(default=None)


@attr.s
class Conflict:
    id = attr.ib()
    sub_id = attr.ib(default=None)
    category = attr.ib(default=None)
    subcategory = attr.ib(default=None)
    predicate = attr.ib(default=None)
    lead_ups = attr.ib(default=attr.Factory(list))
    carry_ons = attr.ib(default=attr.Factory(list))
    permutations = attr.ib(default=attr.Factory(list))

    @property
    def cid(self):
        return f'{self.id}{self.sub_id if self.sub_id is not None else ""}'


@attr.s
class ConflictPermutation:
    text = attr.ib(default=None)
    options = attr.ib(default=attr.Factory(list))
    includes = attr.ib(default=attr.Factory(list))
