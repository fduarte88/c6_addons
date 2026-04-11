from django import forms
from .models import Category, Product


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


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = [
            'description', 'origin', 'category',
            'quantity', 'cost', 'list_price', 'distributor_price',
            'cost_usd', 'cotizacion',
            'calce', 'talle', 'is_active',
        ]
        labels = {
            'description':       'Descripción',
            'origin':            'Origen',
            'category':          'Categoría',
            'quantity':          'Cantidad en stock',
            'cost':              'Costo',
            'list_price':        'Precio de lista',
            'distributor_price': 'Precio distribuidor',
            'cost_usd':          'Costo USD',
            'cotizacion':        'Cotización (1 USD = Gs.)',
            'calce':             'Calce',
            'talle':             'Talle',
            'is_active':         'Producto activo',
        }
        widgets = {
            'description':       forms.TextInput(attrs={'placeholder': 'Descripción del producto'}),
            'origin':            forms.TextInput(attrs={'placeholder': 'Ej: China, Argentina, Brasil'}),
            'quantity':          forms.NumberInput(attrs={'min': '0', 'placeholder': '0'}),
            'cost':              forms.TextInput(attrs={'class': 'gs-input', 'placeholder': '0', 'autocomplete': 'off'}),
            'list_price':        forms.TextInput(attrs={'class': 'gs-input', 'placeholder': '0', 'autocomplete': 'off'}),
            'distributor_price': forms.TextInput(attrs={'class': 'gs-input', 'placeholder': '0', 'autocomplete': 'off'}),
            'cost_usd':          forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'cotizacion':        forms.NumberInput(attrs={'min': '0', 'step': '1', 'placeholder': 'Ej: 7800'}),
            'calce':             forms.Select(),
            'talle':             forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar categorías activas
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = 'Selecciona una categoría'
        # Campos condicionales: no son requeridos en el form (la validación es manual)
        self.fields['calce'].required     = False
        self.fields['talle'].required     = False
        self.fields['cost_usd'].required  = False
        self.fields['cotizacion'].required = False
        # Agregar opción vacía a selects condicionales
        self.fields['calce'].choices  = [('', 'Selecciona calce')] + list(Product.CALCE_CHOICES)
        self.fields['talle'].choices  = [('', 'Selecciona talle')] + list(Product.TALLE_CHOICES)

    def _clean_gs_field(self, field_name):
        """Elimina puntos de miles del valor formateado como Gs. antes de validar."""
        value = self.data.get(field_name, '').replace('.', '').replace(',', '').strip()
        try:
            return int(value) if value else None
        except ValueError:
            raise forms.ValidationError('Ingresa un número válido.')

    def clean_cost(self):
        return self._clean_gs_field('cost')

    def clean_list_price(self):
        return self._clean_gs_field('list_price')

    def clean_distributor_price(self):
        return self._clean_gs_field('distributor_price')

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
            # Limpiar campo que no corresponde
            if not category.is_calzado:
                cleaned['calce'] = ''
            if not category.is_vestimenta:
                cleaned['talle'] = ''

        return cleaned
