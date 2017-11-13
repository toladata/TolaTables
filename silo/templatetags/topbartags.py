import json
from django import template
from util import getImportApps
from util import getImportAppsVerbose



register = template.Library()


@register.assignment_tag
def getDataImports():
    return getImportAppsVerbose()
