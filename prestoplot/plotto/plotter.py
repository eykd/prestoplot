import random
import re

from funcy import first, is_mapping, is_seq, isa

from .. import data

PLOTTO = data.get_plotto_data()

MALE_NAMES = data.get_male_names()
FEMALE_NAMES = data.get_female_names()


is_str = isa(str)


class Plotter:
    def __init__(self, tree):
        self.tree = tree




def generate_plot(lead_ins=1, carry_ons=1, rng=random, data=PLOTTO):
    preamble = rng.choice(data.xpath('//subject/description/text()'))
    resolution = rng.choice(data.xpath('//outcome/description/text()')).lower()

    master_predicate = rng.choice(data.xpath('//predicate'))
    master_clause = master_predicate.find('description').text.lower().rstrip('.')

    start = find_linked(data, rng.choice(master_predicate.xpath('./conflict-link')))
    inciting_incident = ''.join(start.xpath('./description/permutation/text/text()'))

    return f'{preamble}, {master_clause}, {resolution}\n\n{inciting_incident}'


def find_linked(data, link):
    ref = link.get('ref')
    return first(data.xpath(f'//conflict[@id="{ref}"]'))


def transform_to_regex(d):
    keys = sorted(d.keys(), key=lambda k: -len(k))
    if not keys:
        return None
    inner_pattern = '|'.join(f'(?:{re.escape(k)})' for k in keys)
    return re.compile(f'\\b(?:{inner_pattern})(?![a-z])')


def get_random_namer(rng, male_names, female_names):
    def get_random_name(sex):
        if sex == 'male':
            names = male_names
        elif sex == 'female':
            names = female_names
        elif sex == 'any':
            names = rng.choice((male_names, female_names))
        else:
            return None

        return rng.choice(names)

    return get_random_name


class Event:
    def __init__(self, text, cast, transforms):
        self.text = text
        self.cast = cast
        self.transforms = transforms
        self.sub_events = []


class PlotGenerator:
    def __init__(self, rng=None, db=None, namer=None, flip_sexes=False, lead_ins=1, carry_ons=1):
        self.rng = rng if rng is not None else random.Random()
        self.db = db or PLOTTO
        self.namer = namer or get_random_namer(self.rng, MALE_NAMES, FEMALE_NAMES)
        self.flip_sexes = flip_sexes
        self.starting_lead_ins = lead_ins
        self.starting_carry_ons = carry_ons

    flip_sexes_transform = {
        "A"  : "B",
        "A-2": "B-2",
        "A-3": "B-3",
        "A-4": "B-4",
        "A-5": "B-5",
        "A-6": "B-6",
        "A-7": "B-7",
        "A-8": "B-8",
        "A-9": "B-9",
        "B"  : "A",
        "B-2": "A-2",
        "B-3": "A-3",
        "B-4": "A-4",
        "B-5": "A-5",
        "B-6": "A-6",
        "B-7": "A-7",
        "B-8": "A-8",
        "B-9": "A-9"
    }

    def generate(self):
        root_transform = self.flip_sexes_transform if self.flip_sexes else None
        preamble = self.rng.choice(self.db['master_clause_A'])
        resolution = self.rng.choice(self.db['master_clause_C'])
        master = self.rng.choice(self.db['master_clause_B'])

        conflict = self.db['conflicts'][self.rng.choice(master['nodes'])]

        cast = []

        context = {
            'lead_ins': self.starting_lead_ins,
            'carry_ons': self.starting_carry_ons,
        }

        plot = self.expand(conflict, root_transform, context)
        plot = self.apply_names(plot, cast)

        return {
            'group': master['group'],
            'subgroup': master['subgroup'],
            'description': master['description'],
            'cast': cast,
            'plot': '\n\n'.join([
                preamble,
                plot,
                resolution,
            ]).strip()
        }

    def apply_names(self, text, cast):
        name_cache = {}

        name_cp = transform_to_regex(self.db['characters'])

        def replace_name(match):
            if not match:
                return ''

            symbol = match.group()

            description = self.db['characters'][symbol]
            if not description:
                return match

            name = name_cache.get(symbol)

            if name is None:
                name = self.namer(self.db['character-sexes'].get(symbol))
                name_cache[symbol] = name
                cast.append({
                    'symbol': symbol,
                    'name': name,
                    'description': description,
                })

            return name

        if name_cp:
            text = name_cp.sub(replace_name, text)

        return text

    def expand(self, item, transforms, ctx, start=None, end=None):
        results = []

        if not item:
            return 'NULL'

        carry_on = None
        if is_mapping(item):
            carry_on = self._expand_mapping(results, item, transforms, ctx, start, end)

        elif is_str(item):
            results.append(self.expand(self.db['conflicts'][item], transforms, ctx, start, end))

        elif is_seq(item):
            results.append(self.expand(self.rng.choice(item), transforms, ctx, start, end))

        if carry_on:
            results.append(carry_on)

        text = '\n\n'.join(results)

        if transforms:
            text = self.apply_transforms(text, transforms)

        return text

    def _expand_mapping(self, results, item, transforms, ctx, start, end):
        self._expand_lead_ins(results, item, transforms, ctx, start, end)
        carry_on = self._expand_carry_on(results, item, transforms, ctx, start, end)

        if item.get('conflict_id'):
            self._expand_conflict(results, item, transforms, ctx, start, end)

        elif item.get('v'):
            self._expand_v(results, item, transforms, ctx, start, end)

        return carry_on

    def apply_transforms(self, text, transforms):
        transforms_cp = transform_to_regex(transforms)

        if transforms_cp:
            def replace_transform(match):
                if not match:
                    return ''
                symbol = match.group()
                transformed = transforms.get(symbol)
                return transformed if transformed else symbol

            text = transforms_cp.sub(replace_transform, text)

        return text

    def _expand_lead_ins(self, results, item, transforms, ctx, start, end):
        if ctx['lead_ins'] > 0 and item.get('lead_ins'):
            ctx['lead_ins'] -= 1
            results.append(self.expand(item['lead_ins'], transforms, ctx, start, end))

    def _expand_carry_on(self, results, item, transforms, ctx, start, end):
        if ctx['carry_ons'] > 0 and item.get('carry_ons'):
            ctx['carry_ons'] -= 1
            return self.expand(item['carry_ons'], transforms, ctx, start, end)

    def _expand_conflict(self, results, item, transforms, ctx, start, end):
        if is_str(item.get('description')):
            results.append(item['description'])
        else:
            for sub_desc in item.get('description', ()):
                if is_str(sub_desc):
                    results.append(self._get_str(sub_desc, start, end))
                else:
                    results.append(self.expand(sub_desc, transforms, ctx, start, end))

    def _expand_v(self, results, item, transforms, ctx, start, end):
        if item.get('start') or item.get('end'):
            results.append(
                self.expand(
                    self.db['conflicts'][item['v']],
                    item.get('tfm'),
                    ctx,
                    item['start'],
                    item['end'],
                ))
        elif item.get('op') == '+':
            for sub in item.get('v', ()):
                results.append(self.expand(sub, item.get('tfm'), ctx, start, end))

        else:
            results.append(self.expand(item['v'], item.get('tfm'), ctx, start, end))

    def _get_str(self, desc, start, end):
        if not start and not end:
            return desc
        si, ei = 0, len(desc)
        if start:
            si = desc.find(start)
            if si < 0:
                si = 0
            else:
                si += len(start)
        if end:
            ei = desc.find(end)
            if ei < 0:
                ei = 0
        return desc[si:ei]
