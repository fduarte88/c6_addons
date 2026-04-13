from django.db import models
from suppliers.models import Supplier


class Category(models.Model):
    TIPO_GENERAL    = 'GEN'
    TIPO_CALZADO    = 'CAL'
    TIPO_VESTIMENTA = 'VES'
    TIPO_CHOICES = [
        (TIPO_GENERAL,    'General'),
        (TIPO_CALZADO,    'Calzado'),
        (TIPO_VESTIMENTA, 'Vestimenta'),
    ]

    name        = models.CharField('Nombre', max_length=100, unique=True)
    tipo        = models.CharField('Tipo', max_length=3, choices=TIPO_CHOICES, default=TIPO_GENERAL)
    description = models.CharField('Descripción', max_length=200, blank=True)
    is_active   = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def is_calzado(self):
        return self.tipo == self.TIPO_CALZADO

    @property
    def is_vestimenta(self):
        return self.tipo == self.TIPO_VESTIMENTA


class Product(models.Model):
    # Calce EU (europeo / latinoamericano)
    CALCE_CHOICES = [(str(n), str(n)) for n in range(30, 50)]

    # Calce US (americano): 1 – 15 con medios
    CALCE_US_CHOICES = (
        [(f'{n}', f'{n}') for n in range(1, 16)] +
        [(f'{n}.5', f'{n}.5') for n in range(1, 15)]
    )
    CALCE_US_CHOICES = sorted(CALCE_US_CHOICES, key=lambda x: float(x[0]))

    # Calce UK (británico): 1 – 14 con medios
    CALCE_UK_CHOICES = (
        [(f'{n}', f'{n}') for n in range(1, 15)] +
        [(f'{n}.5', f'{n}.5') for n in range(1, 14)]
    )
    CALCE_UK_CHOICES = sorted(CALCE_UK_CHOICES, key=lambda x: float(x[0]))

    # Opciones de talle (ropa)
    TALLE_XS  = 'XS'
    TALLE_S   = 'S'
    TALLE_M   = 'M'
    TALLE_L   = 'L'
    TALLE_XL  = 'XL'
    TALLE_XXL = 'XXL'
    TALLE_3XL = '3XL'
    TALLE_CHOICES = [
        (TALLE_XS,  'XS'),
        (TALLE_S,   'S'),
        (TALLE_M,   'M'),
        (TALLE_L,   'L'),
        (TALLE_XL,  'XL'),
        (TALLE_XXL, 'XXL'),
        (TALLE_3XL, '3XL'),
    ]

    description        = models.CharField('Descripción', max_length=200)
    origin             = models.CharField('Procedencia', max_length=100)
    supplier           = models.ForeignKey(
                            Supplier, on_delete=models.SET_NULL,
                            null=True, blank=True,
                            verbose_name='Proveedor', related_name='products'
                         )
    quantity           = models.PositiveIntegerField('Cantidad en stock', default=0)
    cost               = models.DecimalField('Costo', max_digits=12, decimal_places=2)
    list_price         = models.DecimalField('Precio de lista', max_digits=12, decimal_places=2)
    distributor_price  = models.DecimalField('Precio distribuidor', max_digits=12, decimal_places=2)
    cost_usd           = models.DecimalField('Costo USD', max_digits=10, decimal_places=2, null=True, blank=True)
    cotizacion         = models.DecimalField('Cotización (USD→Gs.)', max_digits=10, decimal_places=2, null=True, blank=True)
    category           = models.ForeignKey(
                            Category, on_delete=models.PROTECT,
                            verbose_name='Categoría', related_name='products'
                         )
    # Campos condicionales
    calce              = models.CharField('Calce EU', max_length=5, blank=True,
                                          choices=CALCE_CHOICES,
                                          help_text='Talla europea/latinoamericana')
    calce_us           = models.CharField('Calce US', max_length=5, blank=True,
                                          help_text='Talla americana')
    calce_uk           = models.CharField('Calce UK', max_length=5, blank=True,
                                          help_text='Talla británica')
    talle              = models.CharField('Talle', max_length=5, blank=True,
                                          choices=TALLE_CHOICES,
                                          help_text='Solo para categoría Vestimenta')
    is_active          = models.BooleanField('Activo', default=True)
    created_at         = models.DateTimeField('Creado', auto_now_add=True)
    updated_at         = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name        = 'Producto'
        verbose_name_plural = 'Productos'
        ordering            = ['description']

    def __str__(self):
        return self.description

    @property
    def margin(self):
        """Margen sobre el costo en %."""
        if self.cost and self.cost > 0:
            return round((self.list_price - self.cost) / self.cost * 100, 1)
        return 0

    @property
    def size_display(self):
        if self.calce or self.calce_us or self.calce_uk:
            parts = []
            if self.calce:    parts.append(f'EU {self.calce}')
            if self.calce_us: parts.append(f'US {self.calce_us}')
            if self.calce_uk: parts.append(f'UK {self.calce_uk}')
            return ' / '.join(parts)
        if self.talle:
            return f'Talle {self.talle}'
        return '—'
