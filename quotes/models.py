from django.db import models
from suppliers.models import Supplier


class SupplierQuoteConfig(models.Model):
    """Configuración de campos del presupuesto por proveedor."""
    supplier      = models.OneToOneField(Supplier, on_delete=models.CASCADE,
                                         related_name='quote_config', verbose_name='Proveedor')
    fields_config = models.JSONField(
        'Configuración de campos', default=list,
        help_text=(
            'Lista de objetos con: key, label, type (number|percent|auto), '
            'default, base (para percent), formula (para auto), in_total (bool).'
        )
    )

    class Meta:
        verbose_name        = 'Config. de presupuesto'
        verbose_name_plural = 'Config. de presupuestos'

    def __str__(self):
        return f'Config. presupuesto — {self.supplier.name}'


class Quote(models.Model):
    """Presupuesto guardado."""
    supplier    = models.ForeignKey(Supplier, on_delete=models.PROTECT,
                                    related_name='quotes', verbose_name='Proveedor')
    description = models.CharField('Descripción del producto', max_length=300, blank=True)
    cotizacion  = models.DecimalField('Cotización USD (Gs.)', max_digits=12, decimal_places=2)
    fields_data = models.JSONField('Valores', default=dict)
    total_usd   = models.DecimalField('Total USD', max_digits=14, decimal_places=2, default=0)
    total_gs    = models.DecimalField('Total Gs.', max_digits=14, decimal_places=2, default=0)
    notes       = models.TextField('Notas', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        ordering            = ['-created_at']

    def __str__(self):
        return f'Presupuesto #{self.pk} — {self.supplier.name}'
