import logging
from funcy import cached_property, isa


def render_ftemplate(tmpl, context):
    global_ctx = {**context}
    local_ctx = {'result': tmpl}
    try:
        exec("result = eval(f'f{result!r}')", global_ctx, local_ctx)
    except Exception:
        logging.error('Could not render template: %r', tmpl)
        logging.error('Context: %r', context)
        raise
    return Text(local_ctx['result'], context)


class Text:
    vowels = set('aeiou')

    def __init__(self, value, context):
        self.value = value
        self.context = context

    @cached_property
    def an(self):
        if self.value[0].lower() in self.vowels:
            return 'an'
        else:
            return 'a'

    a = an

    @cached_property
    def An(self):
        return self.an.capitalize()

    A = An

    def __str__(self):
        return self.value

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


class RenderableText(Text):
    def __str__(self):
        return render_ftemplate(self.value, self.context)


is_str = isa(str, Text)
