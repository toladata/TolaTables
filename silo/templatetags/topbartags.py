import json
from django import template
from util import getImportedApps



register = template.Library()


@register.assignment_tag
def getDataImports():
    return getImportedApps()
