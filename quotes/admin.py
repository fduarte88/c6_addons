from django.contrib import admin
from .models import SupplierQuoteConfig, Quote


@admin.register(SupplierQuoteConfig)
class SupplierQuoteConfigAdmin(admin.ModelAdmin):
    list_display = ['supplier']
    help_texts   = {
        'fields_config': (
            'Ejemplo eBay: '
            '[{"key":"costo","label":"Costo","type":"number","default":0,"in_total":true},'
            '{"key":"tax","label":"TAX","type":"number","default":0,"in_total":true},'
            '{"key":"rentabilidad_pct","label":"Rentabilidad %","type":"percent","base":"costo","default":42,"in_total":true},'
            '{"key":"porcentaje_ley","label":"% Ley","type":"auto","formula":"costo * 0.02","in_total":true}]'
        )
    }


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'supplier', 'cotizacion', 'total_usd', 'total_gs', 'created_at']
    list_filter   = ['supplier']
    readonly_fields = ['created_at']
