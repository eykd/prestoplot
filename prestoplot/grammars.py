import textwrap

from funcy import is_list, is_mapping, isa

from . import db, texts

is_bool = isa(bool)


def parse_grammar_file(storage, grammar_path, context, included=None):
    if included is None:
        included = {grammar_path}
    else:
        if grammar_path in included:
            return context
        else:
            included.add(grammar_path)

    doc = storage.resolve_module(grammar_path)
    context = parse_includes(
        storage, grammar_path, doc.pop("include", ()), context, included
    )

    render_strategy = parse_render_strategy(
        doc.pop("render", "ftemplate"), grammar_path
    )

    return parse_data(doc, grammar_path, context, render_strategy=render_strategy)


def parse_render_strategy(render_mode, grammar_path):
    if render_mode == "ftemplate":
        return texts.render_ftemplate
    elif render_mode == "jinja2" or render_mode == "jinja":
        return texts.render_jinja2
    else:
        raise ValueError(
            f"Unrecognized render strategy `{render_mode}` in {grammar_path}"
        )


def parse_includes(storage, grammar_path, includes, context, included):
    for include in includes:
        context = parse_grammar_file(storage, include, context, included)
    return context


def parse_data(data, grammar_path, context, render_strategy=texts.render_ftemplate):
    for key, value in data.items():
        context[key] = parse_value(
            value, f"{grammar_path}:{key}", context, render_strategy=render_strategy
        )

    return context


def get_list_setting(value, grammar_path):
    mode = "reuse"
    if value and is_mapping(value[0]):
        if len(value[0]) == 1 and "mode" in value[0]:
            mode = value.pop(0)["mode"]
    return mode, value


def parse_value(value, grammar_path, context, render_strategy=texts.render_ftemplate):
    if is_list(value):
        mode, value = get_list_setting(value, grammar_path)
        if mode == "reuse":
            return db.Database(
                db.choose(
                    [
                        parse_value(
                            v, grammar_path, context, render_strategy=render_strategy
                        )
                        for v in value
                    ]
                ),
                grammar_path,
                context,
            )
        elif mode == "pick":
            return db.Database(
                db.pick(
                    [
                        parse_value(
                            v, grammar_path, context, render_strategy=render_strategy
                        )
                        for v in value
                    ]
                ),
                grammar_path,
                context,
            )
        elif mode == "markov":
            return db.Database(
                db.markovify([texts.RenderedStr(v) for v in value]),
                grammar_path,
                context,
            )
        elif mode == "ratchet":
            return db.Database(
                db.ratchet([texts.RenderedStr(v) for v in value]), grammar_path, context
            )
        elif mode == "list":
            return db.Datalist(
                grammar_path, context, [texts.RenderedStr(v) for v in value]
            )
    elif is_mapping(value):
        return db.Databag(
            grammar_path,
            context,
            {
                k: parse_value(
                    v, grammar_path, context, render_strategy=render_strategy
                )
                for k, v in value.items()
            },
        )
    elif is_bool(value):
        return value
    else:
        return texts.RenderableText(
            fix_text(value), grammar_path, context, render_strategy=render_strategy
        )


def fix_text(text):
    return textwrap.dedent(text).strip()
