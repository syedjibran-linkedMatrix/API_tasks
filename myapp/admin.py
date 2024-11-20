from django.contrib import admin
from .models import User, Project, Task, Document

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'role') 

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'manager', 'created_at') 

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_by', 'task')
