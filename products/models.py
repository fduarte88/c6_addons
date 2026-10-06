from django.db import models
from django.db.models import F, Sum
from django.db.models.functions import Coalesce, Greatest
from django.utils.text import slugify
from suppliers.models import Supplier


class CategoryQuerySet(models.QuerySet):
    def tree(self):
        """Cada categoría seguida de sus subcategorías: Camisetas, Camisetas › Básicas, … Pantalones."""
        return self.select_related('parent').order_by(
            Coalesce('parent__name', 'name'), F('parent').asc(nulls_first=True), 'name'
        )


class Origin(models.Model):
    name      = models.CharField('País de procedencia', max_length=100, unique=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name        = 'Procedencia'
        verbose_name_plural = 'Procedencias'
        ordering            = ['name']

    def __str__(self):
        return self.name


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
    slug        = models.SlugField('Slug', max_length=120, unique=True, blank=True,
                                   help_text='Se usa en la URL de la tienda. Se genera desde el nombre.')
    parent      = models.ForeignKey(
                    'self', on_delete=models.PROTECT,
                    null=True, blank=True,
                    verbose_name='Categoría padre', related_name='children'
                  )
    tipo        = models.CharField('Tipo', max_length=3, choices=TIPO_CHOICES, default=TIPO_GENERAL)
    description = models.CharField('Descripción', max_length=200, blank=True)
    is_active   = models.BooleanField('Activa', default=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['name']

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Una subcategoría hereda el tipo del padre (define calce/talle)
        if self.parent_id:
            self.tipo = self.parent.tipo
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)
        # Si cambia el tipo del padre, se propaga a sus subcategorías
        self.children.exclude(tipo=self.tipo).update(tipo=self.tipo)

    def _unique_slug(self):
        base = slugify(self.name) or 'categoria'
        slug, n = base, 2
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    @property
    def full_name(self):
        """'Camisetas › Polo' para subcategorías, 'Camisetas' para las principales."""
        if self.parent_id:
            return f'{self.parent.name} › {self.name}'
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

    # Calce US (americano): 5 – 14 de 0.5 en 0.5
    CALCE_US_CHOICES = []
    _n = 50  # trabajamos en enteros x10 para evitar float impreciso
    while _n <= 140:
        val = f'{_n // 10}' if _n % 10 == 0 else f'{_n // 10}.5'
        CALCE_US_CHOICES.append((val, f'US {val}'))
        _n += 5

    # Calce UK (británico): 5 – 13 de 0.5 en 0.5
    CALCE_UK_CHOICES = []
    _n = 50
    while _n <= 130:
        val = f'{_n // 10}' if _n % 10 == 0 else f'{_n // 10}.5'
        CALCE_UK_CHOICES.append((val, f'UK {val}'))
        _n += 5

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
    origin             = models.ForeignKey(
                            'Origin', on_delete=models.SET_NULL,
                            null=True, blank=True,
                            verbose_name='Procedencia', related_name='products'
                         )
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
                                          choices=CALCE_US_CHOICES,
                                          help_text='Talla americana')
    calce_uk           = models.CharField('Calce UK', max_length=5, blank=True,
                                          choices=CALCE_UK_CHOICES,
                                          help_text='Talla británica')
    image              = models.ImageField('Imagen', upload_to='productos/', blank=True,
                                           help_text='Foto que se muestra en la tienda online')
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
    def talles(self):
        """Talles ofrecidos, de XS a 3XL. Usa el prefetch de 'sizes' si lo hay."""
        if not self.pk:
            return []
        return [s.talle for s in self.sizes.all()]

    def add_stock(self, qty, talle=''):
        """
        Suma stock (resta si qty < 0) sin bajar de 0. Único punto donde Compras,
        Ventas y cancelaciones mueven el stock. Si el producto maneja talles, el
        movimiento va al talle y el total (quantity) se recalcula como la suma.
        """
        if talle:
            self.sizes.filter(talle=talle).update(quantity=Greatest(F('quantity') + qty, 0))
            total = self.sizes.aggregate(total=Sum('quantity'))['total'] or 0
            Product.objects.filter(pk=self.pk).update(quantity=total)
        else:
            Product.objects.filter(pk=self.pk).update(quantity=Greatest(F('quantity') + qty, 0))
        self.refresh_from_db(fields=['quantity'])

    @property
    def size_display(self):
        if self.calce or self.calce_us or self.calce_uk:
            parts = []
            if self.calce:    parts.append(f'EU {self.calce}')
            if self.calce_us: parts.append(f'US {self.calce_us}')
            if self.calce_uk: parts.append(f'UK {self.calce_uk}')
            return ' / '.join(parts)
        if len(self.talles) == 1:
            return f'Talle {self.talles[0]}'
        if self.talles:
            return f'Talles {", ".join(self.talles)}'
        return '—'


class ProductSize(models.Model):
    """Stock de un producto de vestimenta en un talle. Product.quantity es la suma de sus talles."""
    product  = models.ForeignKey(Product, on_delete=models.CASCADE,
                                 verbose_name='Producto', related_name='sizes')
    talle    = models.CharField('Talle', max_length=5, choices=Product.TALLE_CHOICES)
    position = models.PositiveSmallIntegerField(default=0, editable=False)  # orden XS → 3XL
    quantity = models.PositiveIntegerField('Stock', default=0)

    class Meta:
        verbose_name        = 'Talle de producto'
        verbose_name_plural = 'Talles de producto'
        ordering            = ['position']
        constraints         = [
            models.UniqueConstraint(fields=['product', 'talle'], name='unique_product_talle'),
        ]

    def __str__(self):
        return f'{self.product.description} — {self.talle} ({self.quantity})'

    def save(self, *args, **kwargs):
        self.position = [code for code, _ in Product.TALLE_CHOICES].index(self.talle)
        super().save(*args, **kwargs)
