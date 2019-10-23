import logging

import jinja2
from funcy import cached_property, identity, isa

jinja2_env = jinja2.Environment(undefined=jinja2.DebugUndefined)


def render_ftemplate(tmpl, grammar_path, context):
    global_ctx = {**context}
    local_ctx = {"result": tmpl}
    try:
        exec("result = eval(f'''f{result!r}''')", global_ctx, local_ctx)
    except Exception as exc:
        logging.error(f"{exc}--Could not render template in {grammar_path}:")
        logging.error(f"Template:\n{tmpl}")
        raise
    return RenderedStr(local_ctx["result"])


def render_jinja2(tmpl, grammar_path, context):
    try:
        return RenderedStr(jinja2_env.from_string(tmpl).render(context))
    except jinja2.TemplateError as exc:
        logging.error(f"{exc}--Could not render Jinja2 template in {grammar_path}:")
        logging.error(f"Template:\n{tmpl}")
        msg = f"Could not render Jinja2 template ({exc}): "
        if hasattr(exc, "source") and exc.source:
            lineno = exc.lineno
            line = exc.source.splitlines()[lineno - 1]
            logging.error(f"{grammar_path}, line {lineno}")
            logging.error(f"--> {line}")
            msg += f"\n{grammar_path}, line {lineno}"
            msg += f"\n--> {line}"
        else:
            msg += f"\n{grammar_path}"
            msg += f"\n{tmpl}"
        raise ValueError(msg)


class Text:
    vowels = set("aeiou")

    def __init__(self, value, grammar_path, context, transformer=identity):
        self.value = value
        self.context = context
        self.grammar_path = grammar_path
        self.transformer = transformer

    @cached_property
    def an(self):
        if str(self.value)[0].lower() in self.vowels:
            return "an"
        else:
            return "a"

    a = an

    @cached_property
    def An(self):
        return self.an.capitalize()

    A = An

    def __str__(self):
        return self.render()

    def __repr__(self):
        return repr(self.value)

    def __getattr__(self, attr):
        if hasattr(str, attr):
            return getattr(self.value, attr)
        else:
            return super().__getattr__(attr)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return str(self) == other

    def render(self, context=None):
        return RenderedStr(self.transformer(self.value))


class RenderableText(Text):
    def __init__(
        self,
        value,
        grammar_path,
        context,
        transformer=identity,
        render_strategy=render_ftemplate,
    ):
        super().__init__(value, grammar_path, context, transformer=transformer)
        self._render = render_strategy

    def __str__(self):
        return self.render(self.context)

    def render(self, context=None):
        return RenderedStr(
            self._render(super().render(), self.grammar_path, context or self.context)
        )


is_text = isa(Text)


class RenderedStr(str):
    vowels = set("aeiou")

    @cached_property
    def an(self):
        if self[0].lower() in self.vowels:
            return "an"
        else:
            return "a"

    a = an

    @cached_property
    def An(self):
        return self.an.capitalize()

    A = An
