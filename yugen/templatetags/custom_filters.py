from django import template
from django.utils.html import strip_tags
from django.utils.dateparse import parse_datetime
from datetime import datetime
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='strip_html')
def strip_html_tags(value):
    return strip_tags(value)

@register.filter(name='parse_iso_datetime')
def parse_iso_datetime(value):
    return parse_datetime(value)

@register.filter(name='parse_iso_date')
def parse_iso_date(value):
    if value is None:
        return value
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z').date()

@register.filter(name='remove_br')
def remove_br(value):
    return mark_safe(re.sub(r'<br\s*/?>', ' ', value))
