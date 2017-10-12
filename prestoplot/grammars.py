import textwrap

from funcy import is_list, is_mapping
from path import Path
import yaml

from . import db
from . import texts


def parse_grammar_file(grammar_path, context, included=None):
    grammar_path = Path(grammar_path).abspath()
    if included is None:
        included = {grammar_path}
    else:
        if grammar_path in included:
            return context
        else:
            included.add(grammar_path)

    with open(grammar_path, encoding='utf-8') as fi:
        doc = yaml.load(fi)
        context = parse_includes(grammar_path.parent, doc.pop('include', ()), context, included)
        return parse_data(doc, context)


def parse_includes(base_path, includes, context, included):
    for include in includes:
        context = parse_grammar_file(base_path / f'{include}.yaml', context, included)
    return context


def parse_data(data, context):
    for key, value in data.items():
        context[key] = parse_value(value, context)

    return context


def get_list_setting(value):
    mode = 'reuse'
    if value and is_mapping(value[0]):
        if len(value[0]) == 1 and 'mode' in value[0]:
            mode = value.pop(0)['mode']
    return mode, value


def parse_value(value, context):
    if is_list(value):
        mode, value = get_list_setting(value)
        if mode == 'reuse':
            return db.Database(db.choose([parse_value(v, context)
                                          for v in value]), context)
        elif mode == 'pick':
            return db.Database(db.pick([parse_value(v, context)
                                        for v in value]), context)
        elif mode == 'markov':
            return db.Database(
                db.markovify([str(v) for v in value]),
                context
            )
        elif mode == 'ratchet':
            return db.Database(
                db.ratchet([str(v) for v in value]),
                context
            )
        elif mode == 'list':
            return db.Datalist(context, [str(v) for v in value])
    elif is_mapping(value):
        return db.Databag(context, {k: parse_value(v, context) for k, v in value.items()})
    else:
        return texts.RenderableText(fix_text(value), context)


def fix_text(text):
    return textwrap.dedent(text).strip()
