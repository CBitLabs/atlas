from django import template
register = template.Library()


@register.filter(name='range') 
def range(number):
    return range(number)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

