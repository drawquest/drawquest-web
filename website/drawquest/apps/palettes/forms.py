from itertools import chain

from django import forms
from django.forms.util import flatatt
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from drawquest.apps.palettes.models import Color, ColorPack


# Widget rendering code forked from django.forms.widgets

class ColorCheckboxInput(forms.CheckboxInput):
    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='checkbox', name=name)
        if self.check_test(value):
            final_attrs['checked'] = 'checked'
        if not (value is True or value is False or value is None or value == ''):
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(value)
        return format_html('<input{0} />', flatatt(final_attrs))


class ColorsSelect(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = ['<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = format_html(' for="{0}"', final_attrs['id'])
            else:
                label_for = ''

            cb = ColorCheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = force_text(option_label)
            output.append(format_html('<li><label{0}>{1} {2}</label></li>',
                                      label_for, rendered_cb, option_label))
        output.append('</ul>')
        return mark_safe('\n'.join(output))


def label_from_color_instance(obj):
    return mark_safe('<div class="color_option_swatch" style="background-color:rgb({red}, {green}, {blue})" title="{label}"><div class="color_option_swatch_inner"></div></div>'.format(red=obj.red, green=obj.green, blue=obj.blue, label=obj.label))


class ColorPackForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ColorPackForm, self).__init__(*args, **kwargs)

        self.fields['colors'].label_from_instance = label_from_color_instance
        self.fields['colors'].queryset = Color.includable_in_color_pack()
        

    class Meta(object):
        model = ColorPack
        exclude = ['id', 'owners', 'legacy_palette_name']
        widgets = {
            'ordinal': forms.TextInput(attrs={'class': 'ordinal'}),
            'colors': ColorsSelect(),
        }


class ColorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ColorForm, self).__init__(*args, **kwargs)

    class Meta(object):
        model = Color
        exclude = ['id', 'owners']
        widgets = {
            'ordinal': forms.TextInput(attrs={'class': 'ordinal'}),
        }

