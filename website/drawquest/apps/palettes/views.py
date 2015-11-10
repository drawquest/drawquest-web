from django.shortcuts import get_object_or_404, Http404

from canvas.redis_models import redis
from drawquest.apps.palettes.models import Color, ColorPack
from drawquest.apps.palettes.forms import ColorPackForm, ColorForm
from drawquest.generic import ModelFormSetView, SortableListMixin


class _PalettesView(ModelFormSetView):
    def get_context_data(self, **kwargs):
        context = super(_PalettesView, self).get_context_data(**kwargs)
        context['colors_header'] = redis.get('colors_header')
        context['color_packs_header'] = redis.get('color_packs_header')
        return context


class ColorPackList(_PalettesView):
    model = ColorPack
    form_class = ColorPackForm
    template_name = 'palettes/colorpack_formset.html'
    extra = 1


class ColorList(_PalettesView):
    model = Color
    form_class = ColorForm
    template_name = 'palettes/color_formset.html'
    extra = 1

