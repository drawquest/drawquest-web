from django.views.generic.base import View as DjangoView, TemplateView as DjangoTemplateView, RedirectView as DjangoRedirectView
from django.views.generic.detail import DetailView as DjangoDetailView
from django.views.generic.edit import FormView as DjangoFormView, CreateView as DjangoCreateView, UpdateView as DjangoUpdateView, DeleteView as DjangoDeleteView
from django.views.generic.list import ListView as DjangoListView
import extra_views

from canvas.shortcuts import r2r_jinja


# Forked from django.template.response
def _resolve_template(template):
    "Accepts a path-to-template or list of paths"
    if isinstance(template, (list, tuple)):
        return template[0]

    return template


class Jinja2ResponseMixin(object):
    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)

        template = _resolve_template(self.get_template_names())

        return r2r_jinja(template, context, request=self.request)


class ListView(Jinja2ResponseMixin, DjangoListView): pass

class CreateView(Jinja2ResponseMixin, DjangoCreateView): pass

class UpdateView(Jinja2ResponseMixin, DjangoUpdateView): pass

class DeleteView(Jinja2ResponseMixin, DjangoDeleteView): pass

class DetailView(Jinja2ResponseMixin, DjangoDetailView): pass

class RedirectView(Jinja2ResponseMixin, DjangoRedirectView): pass

class View(Jinja2ResponseMixin, DjangoView): pass

class TemplateView(Jinja2ResponseMixin, DjangoTemplateView): pass

class ModelFormSetView(Jinja2ResponseMixin, extra_views.ModelFormSetView): pass


class SortableListMixin(Jinja2ResponseMixin, extra_views.SortableListMixin): pass

class NamedFormsetsMixin(Jinja2ResponseMixin, extra_views.NamedFormsetsMixin): pass

