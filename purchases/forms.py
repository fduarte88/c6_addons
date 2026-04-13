from django import forms
from django.forms import inlineformset_factory
from products.models import Product
from .models import Purchase, PurchaseItem


class PurchaseForm(forms.ModelForm):
    class Meta:
        model  = Purchase
        fields = ['date', 'supplier', 'notes']
        labels = {
            'date':     'Fecha de compra',
            'supplier': 'Proveedor',
            'notes':    'Observaciones',
        }
        widgets = {
            'date':     forms.DateInput(
                            format='%d/%m/%Y',
                            attrs={'placeholder': 'DD/MM/AAAA', 'class': 'date-dmy'}
                        ),
            'supplier': forms.TextInput(attrs={'placeholder': 'Nombre del proveedor (opcional)'}),
            'notes':    forms.Textarea(attrs={'rows': 2, 'placeholder': 'Observaciones opcionales...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].required = False
        self.fields['notes'].required    = False
        self.fields['date'].input_formats = ['%d/%m/%Y', '%Y-%m-%d']


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model  = PurchaseItem
        fields = ['product', 'quantity', 'unit_cost']
        labels = {
            'product':   'Producto',
            'quantity':  'Cant.',
            'unit_cost': 'Costo unit. (Gs.)',
        }
        widgets = {
            'product':   forms.Select(attrs={'class': 'item-product'}),
            'quantity':  forms.NumberInput(attrs={'min': '1', 'class': 'item-qty', 'placeholder': '1'}),
            'unit_cost': forms.NumberInput(attrs={'min': '0', 'step': '1', 'class': 'item-price', 'placeholder': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = (
            Product.objects.filter(is_active=True)
                           .select_related('category')
                           .order_by('description')
        )
        self.fields['product'].empty_label = 'Selecciona un producto'


PurchaseItemFormSet = inlineformset_factory(
    Purchase, PurchaseItem,
    form=PurchaseItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
