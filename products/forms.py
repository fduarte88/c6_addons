from django import forms
from suppliers.models import Supplier
from .models import Category, Origin, Product, ProductSize


class OriginForm(forms.ModelForm):
    class Meta:
        model  = Origin
        fields = ['name', 'is_active']
        labels = {'name': 'País de procedencia', 'is_active': 'Activo'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': 'Ej: China, Argentina, Brasil'})}


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name', 'parent', 'tipo', 'description', 'is_active']
        labels = {
            'name':        'Nombre',
            'parent':      'Categoría padre',
            'tipo':        'Tipo',
            'description': 'Descripción',
            'is_active':   'Categoría activa',
        }
        widgets = {
            'name':        forms.TextInput(attrs={'placeholder': 'Ej: Zapatillas'}),
            'description': forms.TextInput(attrs={'placeholder': 'Descripción opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Un solo nivel: el padre tiene que ser una categoría principal
        parents = Category.objects.filter(parent__isnull=True, is_active=True)
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields['parent'].queryset    = parents.order_by('name')
        self.fields['parent'].required    = False
        self.fields['parent'].empty_label = 'Ninguna (categoría principal)'
        self.fields['tipo'].required      = False  # una subcategoría lo hereda del padre

    def clean(self):
        cleaned = super().clean()
        parent  = cleaned.get('parent')
        if parent:
            if self.instance.pk and self.instance.children.exists():
                self.add_error('parent', 'Esta categoría tiene subcategorías, no puede ser subcategoría de otra.')
            cleaned['tipo'] = parent.tipo
        elif not cleaned.get('tipo'):
            self.add_error('tipo', 'Este campo es obligatorio.')
        return cleaned


def _gs_char_field(label, required=True):
    """CharField con máscara Gs. que evita la validación DecimalField de Django."""
    return forms.CharField(
        label=label,
        required=required,
        widget=forms.TextInput(attrs={'class': 'gs-input', 'placeholder': '0', 'autocomplete': 'off'}),
    )


class ProductForm(forms.ModelForm):
    # Declarados como CharField para evitar que Django valide como Decimal antes
    # de que podamos limpiar los puntos de miles del formato Guaraní.
    cost              = _gs_char_field('Costo')
    list_price        = _gs_char_field('Precio de lista')
    distributor_price = _gs_char_field('Precio distribuidor')
    # No es un campo del modelo: se guarda como filas de ProductSize (ver _save_m2m)
    talles            = forms.MultipleChoiceField(
                            label='Talles disponibles', required=False,
                            choices=Product.TALLE_CHOICES,
                            widget=forms.CheckboxSelectMultiple,
                        )

    class Meta:
        model  = Product
        fields = [
            'description', 'origin', 'category', 'supplier',
            'quantity', 'cost', 'list_price', 'distributor_price',
            'cost_usd', 'cotizacion',
            'calce', 'calce_us', 'calce_uk', 'image', 'is_active',
        ]
        labels = {
            'image':             'Imagen',
            'description':       'Descripción',
            'origin':            'Procedencia',
            'category':          'Categoría',
            'supplier':          'Proveedor',
            'quantity':          'Cantidad en stock',
            'cost_usd':          'Costo USD',
            'cotizacion':        'Cotización (1 USD = Gs.)',
            'calce':             'Calce EU',
            'calce_us':          'Calce US',
            'calce_uk':          'Calce UK',
            'is_active':         'Producto activo',
        }
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Descripción del producto'}),
            'quantity':    forms.NumberInput(attrs={'readonly': True, 'tabindex': '-1', 'class': 'field-readonly'}),
            'cost_usd':    forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0,00'}),
            'cotizacion':  forms.NumberInput(attrs={'min': '0', 'step': '1',    'placeholder': 'Ej: 7.800'}),
            'calce':    forms.Select(),
            'calce_us': forms.Select(),
            'calce_uk': forms.Select(),
            'image':    forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset   = Category.objects.filter(is_active=True).tree()
        self.fields['category'].empty_label = 'Selecciona una categoría'
        self.fields['origin'].queryset    = Origin.objects.filter(is_active=True)
        self.fields['origin'].required    = False
        self.fields['origin'].empty_label = 'Sin procedencia'
        self.fields['calce'].required       = False
        self.fields['calce_us'].required    = False
        self.fields['calce_uk'].required    = False
        self.fields['cost_usd'].required    = False
        self.fields['cotizacion'].required  = False
        self.fields['supplier'].required    = False
        self.fields['supplier'].queryset    = Supplier.objects.filter(is_active=True).order_by('name')
        self.fields['supplier'].empty_label = 'Sin proveedor asignado'
        self.fields['calce'].choices    = [('', '— EU —')]    + list(Product.CALCE_CHOICES)
        self.fields['calce_us'].choices = [('', '— US —')]    + list(Product.CALCE_US_CHOICES)
        self.fields['calce_uk'].choices = [('', '— UK —')]    + list(Product.CALCE_UK_CHOICES)
        # Stock actual de cada talle (solo lectura: se mueve por Compras / Ventas)
        self.size_stock = {s.talle: s.quantity for s in self.instance.sizes.all()} if self.instance.pk else {}
        if self.instance.pk:
            self.initial['talles'] = list(self.size_stock)
        # Rellenar valor inicial formateado en modo edición
        for fname in ('cost', 'list_price', 'distributor_price'):
            val = getattr(self.instance, fname, None)
            if val is not None:
                self.initial[fname] = str(int(round(float(val))))

    def clean_quantity(self):
        # Stock bloqueado: siempre conserva el valor almacenado
        if self.instance and self.instance.pk:
            return self.instance.quantity
        return 0  # nuevo producto siempre arranca en 0

    def _parse_gs(self, field_name):
        """Quita puntos de miles, retorna int listo para guardar en DecimalField."""
        raw = self.cleaned_data.get(field_name, '')
        digits = str(raw).replace('.', '').replace(',', '').strip()
        if not digits:
            raise forms.ValidationError('Este campo es obligatorio.')
        try:
            return int(digits)
        except ValueError:
            raise forms.ValidationError('Ingresa un número válido (sin decimales).')

    def clean_cost(self):
        return self._parse_gs('cost')

    def clean_list_price(self):
        return self._parse_gs('list_price')

    def clean_distributor_price(self):
        return self._parse_gs('distributor_price')

    def talle_options(self):
        """Checkboxes de talles junto con su stock actual (None si el talle aún no existe)."""
        return [(cb, self.size_stock.get(cb.data['value'])) for cb in self['talles']]

    def clean_talles(self):
        # Siempre en el orden de TALLE_CHOICES (XS, S, M, …), no en el orden en que se marcaron
        elegidos = set(self.cleaned_data.get('talles') or [])
        return [code for code, _ in Product.TALLE_CHOICES if code in elegidos]

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        calce    = cleaned.get('calce', '').strip()
        talles   = cleaned.get('talles', [])

        if category:
            if category.is_calzado and not calce:
                self.add_error('calce', 'El calce es obligatorio para la categoría Calzado.')
            if category.is_vestimenta and not talles:
                self.add_error('talles', 'Marca al menos un talle para la categoría Vestimenta.')
            # Limpiar campos que no corresponden
            if not category.is_calzado:
                cleaned['calce']    = ''
                cleaned['calce_us'] = ''
                cleaned['calce_uk'] = ''
            if not category.is_vestimenta:
                cleaned['talles'] = []

        # Un talle con stock no se puede quitar (se perdería ese stock)
        talles = cleaned.get('talles', [])
        con_stock = [f'{t} ({q})' for t, q in self.size_stock.items() if q and t not in talles]
        if con_stock:
            self.add_error('talles', f'No se puede quitar un talle con stock: {", ".join(con_stock)}.')
        # El stock existente sin talle no se puede repartir solo entre talles nuevos
        if talles and not self.size_stock and self.instance.pk and self.instance.quantity:
            self.add_error('talles', f'Este producto ya tiene {self.instance.quantity} unidad(es) en stock '
                                     f'sin talle; no se le pueden agregar talles.')
        return cleaned

    def _save_m2m(self):
        super()._save_m2m()
        # Sincroniza los talles ofrecidos: crea los nuevos (stock 0) y borra los desmarcados (sin stock)
        talles = self.cleaned_data.get('talles', [])
        self.instance.sizes.exclude(talle__in=talles).delete()
        for talle in talles:
            if talle not in self.size_stock:
                ProductSize.objects.create(product=self.instance, talle=talle)
