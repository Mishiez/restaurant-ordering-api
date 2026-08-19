from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # UserAdmin already handles password hashing, permissions UI, etc.
    # We're just adding our custom `role` field into the existing
    # list view and the edit form, not rebuilding the admin from
    # scratch.
    list_display = ['id', 'username', 'email', 'role', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Restaurant role', {'fields': ('role',)}),
    )