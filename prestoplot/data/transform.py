import logging
import re
import string

import attr
from funcy import cached_property, filter, first, takewhile
from lxml import etree as ET
from lxml.builder import E
from slugify import Slugify

from .. import entities

from . import PATH


logging.basicConfig(level=logging.INFO)

slugify = Slugify(to_lower=True)


def transform_plotto_html_to_xml():
    html_source = HTMLExtractor(PATH / 'plotto.html')
    try:
        XMLBuilder(html_source).write_xml(PATH / 'plotto.xml')
    except:
        logging.exception('Whoops!')
        import ipdb; ipdb.post_mortem()


class XMLBuilder:
    def __init__(self, datasource):
        self.datasource = datasource

    def build_xml_root(self):
        return E.plotto(
            self.build_characters(self.datasource.characters),
            self.build_subjects(self.datasource.a_clauses),
            self.build_predicates(self.datasource.b_clauses),
            self.build_outcomes(self.datasource.c_clauses),
            self.build_conflicts(self.datasource.conflicts),
        )

    def write_xml(self, fp):
        xml_root = self.build_xml_root()
        with open(fp, 'wb') as fo:
            fo.write(
                ET.tostring(
                    xml_root,
                    encoding='utf-8',
                    xml_declaration=True,
                    standalone=True,
                    with_comments=True,
                    pretty_print=True,
                ))

    @staticmethod
    def build_characters(characters):
        return E.characters(
            *(
                E.character(c.description, designation=c.designation, sex=c.sex)
                for c in characters
            )
        )

    def build_subjects(self, clauses):
        return E.subjects(
            *[
                E.subject(E.description(c.clause), number=c.number)
                for c in clauses
            ]
        )

    def build_predicates(self, clauses):
        return E.predicates(
            *[
                E.predicate(
                    E.description(clause.clause),
                    *[
                        self.build_conflict_link(link)
                        for link in clause.links
                    ],
                    number=clause.number
                )
                for clause in clauses
            ]
        )

    def build_outcomes(self, clauses):
        return E.outcomes(
            *[
                E.outcome(E.description(c.clause), number=c.number)
                for c in clauses
            ]
        )

    def build_conflicts(self, conflicts):
        return E.conflicts(
            *[
                self.build_conflict(conflict)
                for conflict in conflicts
            ]
        )

    def build_conflict(self, conflict):
        return E.conflict(
            E.description(*[self.build_permutation(n + 1, p)
                            for n, p in enumerate(conflict.permutations)]),
            E('lead-ups', *[self.build_group(group) for group in conflict.lead_ups]),
            E('carry-ons', *[self.build_group(group) for group in conflict.carry_ons]),
            id = conflict.cid,
            category = conflict.category,
            subcategory = conflict.subcategory,
        )

    def build_permutation(self, num, permutation):
        return E.permutation(
            E.text(permutation.text),
            *[E.option(o) for o in permutation.options],
            E.includes(*[self.build_group(g) for g in permutation.includes]) if permutation.includes else '',
            number=str(num),
        )

    def build_group(self, group):
        return E.group(*[self.build_conflict_link(link)
                         for link in group.links],
                       mode=group.mode)

    def build_conflict_link(self, link):
        conflict = self.datasource.get_conflict_by_id(link.id)
        el = E(
            'conflict-link',
            *[
                E.transform(**{'from': tfrom, 'to': tto})
                for tfrom, tto in link.transformations.items()
            ],
            *[
                E.add(character)
                for character in link.additions
            ],
            *[
                E.remove(text)
                for text in link.eliminations
            ],
            ref = link.id,
            category = conflict.category,
            subcategory = conflict.subcategory,
        )
        if link.option:
            el.attrib['option'] = link.option
        if link.permutations:
            el.attrib['permutations'] = ','.join(str(p) for p in link.permutations)
        return el


class HTMLExtractor:
    def __init__(self, html_source):
        with open(html_source) as fi:
            html_tree = ET.parse(fi, ET.HTMLParser())

        self.root = html_tree.getroot()

    @cached_property
    def characters(self):
        return self.extract_characters()

    @cached_property
    def a_clauses(self):
        return self.extract_a_clauses()

    @cached_property
    def b_clauses(self):
        return self.extract_b_clauses()

    @cached_property
    def c_clauses(self):
        return self.extract_c_clauses()

    @cached_property
    def conflicts(self):
        return self.extract_conflicts()

    @cached_property
    def conflict_index(self):
        return {conflict.cid: conflict for conflict in self.conflicts}

    def get_conflict_by_id(self, cid):
        return self.conflict_index[cid]

    def extract_characters(self):
        start_el = first(self.root.xpath('//*[@id="character-symbols"][1]')).getnext()

        def is_not_bodytext(el):
            return self.get_class(el) != 'bodytext'

        items = filter(self.has_text,
                       takewhile(is_not_bodytext, start_el.itersiblings()))

        for item in items:
            designation, description = self.get_text(item).split(',', maxsplit=1)
            if self.is_female(description):
                sex = 'female'
            elif self.is_male(description):
                sex = 'male'
            elif 'object' in description:
                sex = 'none'
            else:
                sex = 'any'

            yield entities.Character(
                designation = designation,
                description = description.strip(),
                sex = sex,
            )

    def extract_a_clauses(self):
        start_el = self.get_first_el_with_id('a-clauses')

        items = filter(self.has_text,
                       takewhile(self.is_bodylist, start_el.itersiblings()))

        for item in items:
            number, clause = self.get_text(item).rstrip(',').split(maxsplit=1)
            number = number.strip('.')
            yield entities.AClause(number=number, clause=clause)

    def extract_b_clauses(self):
        start_el = self.get_first_el_with_id('b-clauses')

        items = filter(self.has_text,
                       takewhile(self.is_bodylist, start_el.itersiblings()))
        conflict_index = self.extract_b_clause_conflict_index()

        for item in items:
            number, clause = self.get_text(item).rstrip(',').split(maxsplit=1)
            number = number.strip('()')
            yield entities.BClause(
                number = number,
                clause = clause,
                links = conflict_index[number],
            )

    def extract_c_clauses(self):
        start_el = self.get_first_el_with_id('c-clauses')

        items = filter(self.has_text,
                       takewhile(self.is_bodylist, start_el.itersiblings()))

        for item in items:
            number, clause = self.get_text(item).rstrip(',').split(maxsplit=1)
            number = number.strip('()')
            yield entities.CClause(number=number, clause=clause)

    def extract_b_clause_conflict_index(self):
        start_el = self.get_first_el_with_id('index-b-clause-conflicts')
        index = {}

        items = filter(self.has_text,
                       takewhile(self.is_bodylist, start_el.itersiblings()))

        extractor = StatefulHTMLConflictExtractor(self)
        for item in items:
            number = item.text.strip().split(maxsplit=1)[0]
            number = number.strip('()')
            clinks = []
            for clink in item.xpath('./a'):
                clinks.extend(extractor.extract_conflict_links(self.get_text(clink)))
            index[number] = clinks

        return index

    def extract_conflicts(self):
        return StatefulHTMLConflictExtractor(self).extract_conflicts()

    def is_bodylist(self, el):
        return self.get_class(el) == 'bodylist'

    def get_first_el_with_id(self, el_id):
        return first(self.root.xpath(f'//*[@id="{el_id}"][1]'))

    def has_text(self, el):
        return bool(self.get_text(el).strip(' '))

    @staticmethod
    def get_text(el):
        return ((el.text or '') + ''.join(t for c in el for t in c.itertext())).strip()

    @staticmethod
    def get_class(el):
        return el.attrib.get('class')

    female_descriptors = [
        'female',
        'mother',
        'sister',
        'daughter',
        'aunt',
        'niece',
    ]

    male_descriptors = [
        'male',
        'father',
        'brother',
        'son',
        'uncle',
        'nephew',
    ]

    def is_female(self, description):
        for desc in self.female_descriptors:
            if desc in description:
                return True
        else:
            return False

    def is_male(self, description):
        for desc in self.male_descriptors:
            if desc in description:
                return True
        else:
            return False


class StatefulHTMLConflictExtractor:
    def __init__(self, parent):
        self.parent = parent
        self.category = None
        self.subcategory = None
        self.b_clause_id = None
        self.conflict = None
        self.conflicts = []
        self.conflict_index = {}

    def extract_conflicts(self):
        start_el = first(self.parent.root.xpath('//div[@class="group"]'))

        for el in start_el.xpath('.|following::div'):
            klass = self.parent.get_class(el)
            parser = getattr(self, f'handle_{klass}', None)
            if parser is not None:
                parser(el)

        for conflict in self.conflicts:
            self.conflict_index[conflict.cid] = conflict

        self.fix_conflict_links()

        return self.conflicts

    def handle_group(self, el):
        self.category = self.parent.get_text(el)

    def handle_subgroup(self, el):
        self.subcategory = self.parent.get_text(el)

    def handle_bclause(self, el):
        self.b_clause_id = self.parent.get_text(el).split()[0].strip('()')

    def handle_conflict(self, el):
        self.conflict = entities.Conflict(
            id = el.attrib['id'],
            category = self.category,
            subcategory = self.subcategory,
            predicate = self.b_clause_id,
        )
        self.conflicts.append(self.conflict)

    def handle_desc(self, el):
        description = el.text + ''.join(ET.tostring(c, encoding=str) for c in el)
        permutations = []
        for text in re.split(r' \*+ ', description):
            if text.strip('* '):
                permutation_el = ET.fromstring(f'<div>{text.strip("* ").replace("&", "&amp;")}</div>')
                includes = self.extract_conflict_link_groups(permutation_el)

                text = (permutation_el.text or '') + ''.join(c.tail or '' for c in permutation_el)
                text = (text.replace(' , ', ', ')
                        .replace(' . ', '. ')
                        .strip())
                if not text.endswith('.'):
                    text += '.'
                options = re.split(r' \[\d\] ', text)
                permutation = entities.ConflictPermutation(
                    text = options[0].strip(),
                    options = [o.strip() for o in options[1:]],
                    includes = includes,
                )
                permutations.append(permutation)
        self.conflict.permutations = permutations

    def handle_prelinks(self, el):
        sub_id_span = first(el.xpath('./span[@class="subid"][1]'))
        if sub_id_span is not None:
            if self.conflict.sub_id:
                # It's a new version of the same conflict. Make a copy.
                self.conflict = entities.Conflict(**attr.asdict(self.conflict))
                self.conflicts.append(self.conflict)
            # No matter what, assign the sub id
            self.conflict.sub_id = self.parent.get_text(sub_id_span)

        self.conflict.lead_ups = self.extract_conflict_link_groups(el)

    def handle_postlinks(self, el):
        self.conflict.carry_ons = self.extract_conflict_link_groups(el)

    def extract_conflict_link_groups(self, el):
        groups = []
        for clink_group in el.xpath('./span[@class="clinkgroup"]'):
            group = entities.ConflictLinkGroup()
            groups.append(group)
            if ' ; ' in ''.join(clink_group.itertext()):
                group.mode = 'include'

            for clink_a in clink_group.xpath('./a[@class="clink"]'):
                link_text = self.parent.get_text(clink_a)
                group.links.extend(self.extract_conflict_links(link_text))

        return groups

    def extract_conflict_links(self, link_text):
        for pattern, name in self.conflict_link_patterns.items():
            match = re.match(pattern, link_text)
            if match is not None:
                yield from getattr(self, f'handle_{name}')(match)
                break
        else:
            logging.error(f'No handler for link text: {link_text}')

    conflict_link_patterns = {
        r'^(?P<num>\d+[a-z]?)$': 'number_only',
        r'^(?P<num>\d+[a-z]?)(?P<opt>(?:-\d)+)$': 'number_with_options',
        r'^(?P<num>\d+)(?P<sub_id>[a-z])(?P<sub_ids>(?:, [a-z])+)$': 'number_with_sub_ids',
        r'^(?P<init>.+), (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) & (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) & (?P<from>last [A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) & ch (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+), ch (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) ch (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) & “(?P<from>[-’a-zA-Z0-9 ]+)” to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) and “(?P<from>[-’a-zA-Z0-9 ]+)” to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) ch (?P<from>[A-Z][-A-Z0-9 ]+) to “(?P<to>[-’a-zA-Z0-9 ]+)”$': 'with_transformation',
        r'^(?P<init>.+), ch “(?P<from>[-’a-zA-Z0-9 ]+)” to “(?P<to>[-’a-zA-Z0-9 ]+)”$': 'with_transformation',
        r'^(?P<init>.+) ch “(?P<from>[-’a-zA-Z0-9 ]+)” to “(?P<to>[-’a-zA-Z0-9 ]+)”$': 'with_transformation',
        r'^(?P<init>.+) & tr (?P<from>[A-Z][-A-Z0-9]*) & (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) tr (?P<from>[A-Z][-A-Z0-9]*) & (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) & (?P<from_a>[A-Z][-A-Z0-9]*) and (?P<from_b>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_double_transformation',
        r'^(?P<init>.+) and (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*)$': 'with_transformation',
        r'^(?P<init>.+) and “(?P<from>[-’a-zA-Z0-9 ]+)” to “(?P<to>[-’a-zA-Z0-9 ]+)”$': 'with_transformation',
        r'^(?P<init>.+) (?P<permutation>\**-\*+)': 'with_permutation',
        r'^(?P<init>.+) & add (?P<add>[A-Z][-A-Z0-9]*)$': 'with_addition',
        r'^(?P<init>.+)add (?P<add>[A-Z][-A-Z0-9]*)$': 'with_addition',
        r'^(?P<init>.+) and eliminate “(?P<eliminate>[-’a-zA-Z0-9 ]+)”$': 'with_elimination',
        r'^(?P<init>.+) & eliminate “(?P<eliminate>[-’a-zA-Z0-9 ]+)”$': 'with_elimination',
        r'^(?P<init>.+) ch (?P<from>[A-Z][-A-Z0-9]*) to (?P<to>[A-Z][-A-Z0-9]*, .+)$': 'with_transformation',
    }

    def handle_number_only(self, match):
        cid = match.group('num')
        yield entities.ConflictLink(
            id = cid,
        )

    def handle_number_with_options(self, match):
        for link in self.extract_conflict_links(match.group('num')):
            options = match.group('opt').strip('-').split('-')
            for option in options:
                link = entities.ConflictLink(**attr.asdict(link))
                link.option = option
                yield link

    def handle_number_with_sub_ids(self, match):
        sub_ids = [match.group('sub_id')] + [
            si.strip() for si in match.group('sub_ids').split(',')
            if si.strip()
        ]
        number = match.group('num')
        for sub_id in sub_ids:
            yield entities.ConflictLink(id=f'{number}{sub_id}')

    def handle_with_transformation(self, match):
        for link in self.extract_conflict_links(match.group('init').strip()):
            link.transformations[match.group('from')] = match.group('to')
            yield link

    def handle_with_double_transformation(self, match):
        for link in self.extract_conflict_links(match.group('init').strip()):
            link.transformations[match.group('from_a')] = match.group('to')
            link.transformations[match.group('from_b')] = match.group('to')
            yield link

    def handle_with_permutation(self, match):
        for link in self.extract_conflict_links(match.group('init').strip()):
            a, b = match.group('permutation').split('-')
            pa = a.count('*') + 1
            pb = b.count('*') + 1
            link.permutations.extend(range(pa, pb))
            yield link

    def handle_with_addition(self, match):
        for link in self.extract_conflict_links(match.group('init').strip()):
            link.additions.append(match.group('add'))
            yield link

    def handle_with_elimination(self, match):
        for link in self.extract_conflict_links(match.group('init').strip()):
            link.eliminations.append(match.group('eliminate'))
            yield link

    def fix_conflict_links(self):
        for conflict in self.conflicts:
            self.conflict = conflict
            linkdbs = [conflict.lead_ups, conflict.carry_ons] + [
                p.includes for p in conflict.permutations
            ]
            for linkdb in linkdbs:
                for group in linkdb:
                    for link in list(group.links):
                        cid = link.id
                        if cid not in self.conflict_index:
                            bare_cid = cid.rstrip(string.ascii_lowercase)
                            endings = [
                                key.replace(cid, '')
                                for key in self.conflict_index.keys()
                                if re.match(f'^{cid}[a-z]$', key)
                            ]
                            if endings:
                                idx = group.links.index(link)
                                group.links.remove(link)
                                for ending in reversed(endings):
                                    new_link = entities.ConflictLink(**attr.asdict(link))
                                    new_link.id = bare_cid + ending
                                    logging.error(f'{cid} -> {new_link.id} (from conflict {conflict.cid})')
                                    group.links.insert(idx, new_link)
                            else:
                                if bare_cid in self.conflict_index:
                                    logging.error(f'{cid} -> {bare_cid} (from conflict {conflict.cid})')
                                    link.id = bare_cid
                                else:
                                    raise KeyError(f'No conflict {cid} exists (linked from conflict {conflict.cid})')
