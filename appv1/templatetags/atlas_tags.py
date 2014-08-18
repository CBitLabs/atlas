from django import template
register = template.Library()


@register.filter(name='times') 
def  times(number):
    return range(number)


@register.filter
def get_value(dictionary, key):
    return dictionary.get(key)

