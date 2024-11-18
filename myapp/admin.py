from django.contrib import admin
from .models import User, Project

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass