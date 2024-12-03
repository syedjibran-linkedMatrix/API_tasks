from django.contrib import admin

from .models import Comment, Document, Project, Task, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "manager", "created_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project_id")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_by", "task", "task_id")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "task_id")
