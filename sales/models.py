from django.db import models
from django.utils import timezone
from customers.models import Customer
from products.models import Product


class Sale(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_PARTIAL   = 'partial'
    STATUS_PAID      = 'paid'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pendiente'),
        (STATUS_PARTIAL,   'Pago parcial'),
        (STATUS_PAID,      'Pagado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    customer   = models.ForeignKey(Customer, on_delete=models.PROTECT,
                                   verbose_name='Cliente', related_name='sales')
    date       = models.DateField('Fecha de venta', default=timezone.now)
    notes      = models.TextField('Observaciones', blank=True)
    status     = models.CharField('Estado', max_length=12,
                                  choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering            = ['-date', '-created_at']

    def __str__(self):
        return f'Venta #{self.pk} — {self.customer.full_name}'

    # ── Totales ──────────────────────────────────────
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_paid(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def balance(self):
        return self.total - self.total_paid

    # ── Actualiza estado según pagos ─────────────────
    def update_status(self):
        if self.status == self.STATUS_CANCELLED:
            return
        paid = self.total_paid
        total = self.total
        if paid <= 0:
            self.status = self.STATUS_PENDING
        elif paid < total:
            self.status = self.STATUS_PARTIAL
        else:
            self.status = self.STATUS_PAID
        self.save(update_fields=['status'])


class SaleItem(models.Model):
    sale       = models.ForeignKey(Sale, on_delete=models.CASCADE,
                                   verbose_name='Venta', related_name='items')
    product    = models.ForeignKey(Product, on_delete=models.PROTECT,
                                   verbose_name='Producto')
    quantity   = models.PositiveIntegerField('Cantidad', default=1)
    unit_price = models.DecimalField('Precio unitario', max_digits=14, decimal_places=2)
    talle      = models.CharField('Talle', max_length=5, blank=True, choices=Product.TALLE_CHOICES,
                                  help_text='Solo si el producto maneja stock por talle')

    class Meta:
        verbose_name        = 'Ítem de venta'
        verbose_name_plural = 'Ítems de venta'

    def __str__(self):
        talle = f' ({self.talle})' if self.talle else ''
        return f'{self.quantity} × {self.product.description}{talle}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        # Si no se especificó precio, usa el precio de lista del producto
        if not self.unit_price:
            self.unit_price = self.product.list_price

        old = SaleItem.objects.select_related('product').filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)

        # Descuenta stock (del talle, si corresponde). Al editar solo se mueve la diferencia;
        # si cambió el producto o el talle, se devuelve lo anterior y se descuenta lo nuevo.
        if old and (old.product_id, old.talle) == (self.product_id, self.talle):
            diff = self.quantity - old.quantity
            if diff:
                self.product.add_stock(-diff, self.talle)
        else:
            if old:
                old.product.add_stock(old.quantity, old.talle)
            self.product.add_stock(-self.quantity, self.talle)

    def delete(self, *args, **kwargs):
        # Devuelve el stock al eliminar el ítem
        self.product.add_stock(self.quantity, self.talle)
        super().delete(*args, **kwargs)


class Payment(models.Model):
    TYPE_CASH     = 'EFE'
    TYPE_TRANSFER = 'TRF'
    TYPE_CARD     = 'TAR'
    TYPE_DISCOUNT = 'DSC'
    TYPE_CHOICES = [
        (TYPE_CASH,     'Efectivo'),
        (TYPE_TRANSFER, 'Transferencia'),
        (TYPE_CARD,     'Tarjeta'),
        (TYPE_DISCOUNT, 'Descuento'),
    ]

    sale         = models.ForeignKey(Sale, on_delete=models.CASCADE,
                                     verbose_name='Venta', related_name='payments')
    date         = models.DateField('Fecha de pago', default=timezone.now)
    amount       = models.DecimalField('Monto', max_digits=14, decimal_places=2)
    payment_type = models.CharField('Tipo de pago', max_length=3,
                                    choices=TYPE_CHOICES, default=TYPE_CASH)
    reference    = models.CharField('Referencia / comprobante', max_length=100, blank=True,
                                    help_text='Número de transferencia, voucher, etc.')
    notes        = models.CharField('Notas', max_length=200, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering            = ['date', 'created_at']

    def __str__(self):
        return f'Pago #{self.pk} — {self.get_payment_type_display()} {self.amount}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sale.update_status()
