from django.db import models
from django.utils import timezone
from products.models import Product
from suppliers.models import Supplier


class Purchase(models.Model):
    date       = models.DateField('Fecha de compra', default=timezone.now)
    supplier   = models.ForeignKey(
                     Supplier, on_delete=models.SET_NULL,
                     null=True, blank=True,
                     verbose_name='Proveedor', related_name='purchases'
                 )
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
    talle     = models.CharField('Talle', max_length=5, blank=True, choices=Product.TALLE_CHOICES,
                                 help_text='Solo si el producto maneja stock por talle')

    class Meta:
        verbose_name        = 'Item de compra'
        verbose_name_plural = 'Items de compra'

    def __str__(self):
        talle = f' ({self.talle})' if self.talle else ''
        return f'{self.quantity} x {self.product.description}{talle}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost

    def save(self, *args, **kwargs):
        old = PurchaseItem.objects.select_related('product').filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)

        # Suma stock (al talle, si corresponde). Al editar solo se mueve la diferencia;
        # si cambió el producto o el talle, se revierte lo anterior y se suma lo nuevo.
        if old and (old.product_id, old.talle) == (self.product_id, self.talle):
            diff = self.quantity - old.quantity
            if diff:
                self.product.add_stock(diff, self.talle)
        else:
            if old:
                old.product.add_stock(-old.quantity, old.talle)
            self.product.add_stock(self.quantity, self.talle)

    def delete(self, *args, **kwargs):
        self.product.add_stock(-self.quantity, self.talle)
        super().delete(*args, **kwargs)
