from django.contrib import admin
from .models import MenuItem

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'available', 'created_at']
    list_filter = ['available']
    search_fields = ['name']