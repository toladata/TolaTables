from django.contrib import admin

from .models import *

admin.site.register(Board)
admin.site.register(Graph)
admin.site.register(GraphModel)
admin.site.register(Item)
admin.site.register(GraphInput)