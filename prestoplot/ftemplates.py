from . import db


def render_ftemplate(tmpl, context):
    exec_ctx = {'result': result}
    exec("result = eval(f'f{result!r}')", context, exec_ctx)
    return db.Text(exec_ctx['result'])
