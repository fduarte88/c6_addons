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
            'calce':             'Calce',
            'talle':             'Talle',
            'is_active':         'Producto activo',
        }
        widgets = {
            'description':       forms.TextInput(attrs={'placeholder': 'Descripción del producto'}),
            'origin':            forms.TextInput(attrs={'placeholder': 'Ej: China, Argentina, Brasil'}),
            'quantity':          forms.NumberInput(attrs={'min': '0', 'placeholder': '0'}),
            'cost':              forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'list_price':        forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'distributor_price': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'calce':             forms.Select(),
            'talle':             forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar categorías activas
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = 'Selecciona una categoría'
        # Campos condicionales: no son requeridos en el form (la validación es manual)
        self.fields['calce'].required = False
        self.fields['talle'].required = False
        # Agregar opción vacía a selects condicionales
        self.fields['calce'].choices  = [('', 'Selecciona calce')] + list(Product.CALCE_CHOICES)
        self.fields['talle'].choices  = [('', 'Selecciona talle')] + list(Product.TALLE_CHOICES)

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
