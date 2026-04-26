from django import forms
from suppliers.models import Supplier
from .models import Category, Origin, Product


class OriginForm(forms.ModelForm):
    class Meta:
        model  = Origin
        fields = ['name', 'is_active']
        labels = {'name': 'País de procedencia', 'is_active': 'Activo'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': 'Ej: China, Argentina, Brasil'})}


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name', 'tipo', 'description', 'is_active']
        labels = {
            'name':        'Nombre',
            'tipo':        'Tipo',
            'description': 'Descripción',
            'is_active':   'Categoría activa',
        }
        widgets = {
            'name':        forms.TextInput(attrs={'placeholder': 'Ej: Zapatillas'}),
            'description': forms.TextInput(attrs={'placeholder': 'Descripción opcional'}),
        }


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

    class Meta:
        model  = Product
        fields = [
            'description', 'origin', 'category', 'supplier',
            'quantity', 'cost', 'list_price', 'distributor_price',
            'cost_usd', 'cotizacion',
            'calce', 'calce_us', 'calce_uk', 'talle', 'is_active',
        ]
        labels = {
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
            'talle':             'Talle',
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
            'talle':    forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset   = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = 'Selecciona una categoría'
        self.fields['origin'].queryset    = Origin.objects.filter(is_active=True)
        self.fields['origin'].required    = False
        self.fields['origin'].empty_label = 'Sin procedencia'
        self.fields['calce'].required       = False
        self.fields['calce_us'].required    = False
        self.fields['calce_uk'].required    = False
        self.fields['talle'].required       = False
        self.fields['cost_usd'].required    = False
        self.fields['cotizacion'].required  = False
        self.fields['supplier'].required    = False
        self.fields['supplier'].queryset    = Supplier.objects.filter(is_active=True).order_by('name')
        self.fields['supplier'].empty_label = 'Sin proveedor asignado'
        self.fields['calce'].choices    = [('', '— EU —')]    + list(Product.CALCE_CHOICES)
        self.fields['calce_us'].choices = [('', '— US —')]    + list(Product.CALCE_US_CHOICES)
        self.fields['calce_uk'].choices = [('', '— UK —')]    + list(Product.CALCE_UK_CHOICES)
        self.fields['talle'].choices    = [('', '— Talle —')] + list(Product.TALLE_CHOICES)
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

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        calce    = cleaned.get('calce', '').strip()
        talle    = cleaned.get('talle', '').strip()

        if category:
            if category.is_calzado and not calce:
                self.add_error('calce', 'El calce es obligatorio para la categoría Calzado.')
            if category.is_vestimenta and not talle:
                self.add_error('talle', 'El talle es obligatorio para la categoría Vestimenta.')
            # Limpiar campos que no corresponden
            if not category.is_calzado:
                cleaned['calce']    = ''
                cleaned['calce_us'] = ''
                cleaned['calce_uk'] = ''
            if not category.is_vestimenta:
                cleaned['talle'] = ''

        return cleaned
