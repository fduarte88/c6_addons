from django.db import models
from django.utils import timezone
from products.models import Product


class Purchase(models.Model):
    date       = models.DateField('Fecha de compra', default=timezone.now)
    supplier   = models.CharField('Proveedor', max_length=200, blank=True)
    notes      = models.TextField('Observaciones', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Compra'
        verbose_name_plural = 'Compras'
        ordering            = ['-date', '-created_at']

    def __str__(self):
        return f'Compra #{self.pk} — {self.date}'

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class PurchaseItem(models.Model):
    purchase  = models.ForeignKey(Purchase, on_delete=models.CASCADE,
                                  verbose_name='Compra', related_name='items')
    product   = models.ForeignKey(Product, on_delete=models.PROTECT,
                                  verbose_name='Producto')
    quantity  = models.PositiveIntegerField('Cantidad', default=1)
    unit_cost = models.DecimalField('Costo unitario', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name        = 'Item de compra'
        verbose_name_plural = 'Items de compra'

    def __str__(self):
        return f'{self.quantity} x {self.product.description}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_qty = 0 if is_new else PurchaseItem.objects.get(pk=self.pk).quantity
        super().save(*args, **kwargs)
        diff = self.quantity - old_qty
        if diff != 0:
            self.product.quantity += diff
            self.product.save(update_fields=['quantity'])

    def delete(self, *args, **kwargs):
        product = self.product
        product.quantity = max(0, product.quantity - self.quantity)
        product.save(update_fields=['quantity'])
        super().delete(*args, **kwargs)
