from inspect import getargspec
from functools import partial

from django.template.base import Library, TagHelperNode, generic_tag_compiler


class Library(Library):
    def context_tag(self, func):
        params, varargs, varkw, defaults = getargspec(func)

        class ContextNode(TagHelperNode):
            def render(self, context):
                resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                return func(context, *resolved_args, **resolved_kwargs)

        compile_func = partial(
            generic_tag_compiler,
            params=params[1:],
            varargs=varargs,
            varkw=varkw,
            defaults=defaults[1:] if defaults else None,
            name=getattr(func, "_decorated_function", func).__name__,
            takes_context=False,
            node_class=ContextNode,
        )

        compile_func.__doc__ = func.__doc__

        self.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
        return func

