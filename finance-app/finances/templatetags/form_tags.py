"""Template filters that render Django form fields with Bootstrap 5 classes."""

from django import forms
from django.template import Library
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = Library()


@register.filter
def alert_class(tag):
    """Map Django's message tags to Bootstrap alert variants."""
    return {"error": "danger", "debug": "secondary"}.get(tag, tag or "success")


@register.filter
def bootstrap_field(field):
    """Render a bound field with form-control/form-select + error feedback."""
    widget = field.field.widget
    css = "form-control"
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
        css = "form-check-input"
    elif isinstance(widget, forms.Select):
        css = "form-select"
    if field.errors:
        css += " is-invalid"

    attrs = dict(widget.attrs)
    attrs["class"] = " ".join(filter(None, [attrs.get("class"), css]))
    html = [field.as_widget(attrs=attrs)]

    if field.field.help_text:
        html.append(
            f'<div class="form-text text-muted-small">{escape(field.field.help_text)}</div>'
        )
    if field.errors:
        errors = "".join(f"<div>{escape(error)}</div>" for error in field.errors)
        html.append(f'<div class="invalid-feedback d-block">{errors}</div>')
    return mark_safe("".join(html))
