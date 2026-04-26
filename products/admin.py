from django.contrib import admin
from .models import Category, Origin, Product

@admin.register(Origin)
class OriginAdmin(admin.ModelAdmin):
    list_display  = ('name', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'tipo', 'is_active')
    list_filter   = ('tipo', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('description', 'category', 'origin', 'quantity', 'is_active')
    list_filter   = ('category', 'origin', 'is_active')
    search_fields = ('description',)
