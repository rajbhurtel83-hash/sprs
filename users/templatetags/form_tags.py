from django import template

register = template.Library()


@register.filter(name='addclass')
def addclass(field, css_class):
    """Add a CSS class to a form field widget."""
    return field.as_widget(attrs={'class': css_class})


@register.filter(name='get_item')
def get_item(value, key):
    """Safely read a dictionary item in templates."""
    if isinstance(value, dict):
        return value.get(key, '')
    return ''
