from django.contrib import admin
from .models import WorkFlow,NodeType,Node,Connection
# Register your models here.

admin.site.register(WorkFlow)
admin.site.register(NodeType)
admin.site.register(Node)
admin.site.register(Connection)