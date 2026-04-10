from django import forms
from django.forms import inlineformset_factory
from customers.models import Customer
from products.models import Product
from .models import Sale, SaleItem, Payment


class SaleForm(forms.ModelForm):
    class Meta:
        model  = Sale
        fields = ['customer', 'date', 'notes']
        labels = {
            'customer': 'Cliente',
            'date':     'Fecha de venta',
            'notes':    'Observaciones',
        }
        widgets = {
            'customer': forms.Select(),
            'date':     forms.DateInput(attrs={'type': 'date'}),
            'notes':    forms.Textarea(attrs={'rows': 2, 'placeholder': 'Observaciones opcionales...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['customer'].empty_label = 'Selecciona un cliente'
        self.fields['notes'].required = False


class SaleItemForm(forms.ModelForm):
    class Meta:
        model  = SaleItem
        fields = ['product', 'quantity', 'unit_price']
        labels = {
            'product':    'Producto',
            'quantity':   'Cant.',
            'unit_price': 'Precio unit. (Gs.)',
        }
        widgets = {
            'product':    forms.Select(attrs={'class': 'item-product'}),
            'quantity':   forms.NumberInput(attrs={'min': '1', 'class': 'item-qty', 'placeholder': '1'}),
            'unit_price': forms.NumberInput(attrs={'min': '0', 'step': '1', 'class': 'item-price', 'placeholder': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo productos activos CON stock disponible
        self.fields['product'].queryset = (
            Product.objects.filter(is_active=True, quantity__gt=0)
                           .select_related('category')
                           .order_by('description')
        )
        self.fields['product'].empty_label = 'Selecciona un producto'

    def clean(self):
        cleaned = super().clean()
        product  = cleaned.get('product')
        quantity = cleaned.get('quantity')

        if product and quantity:
            if product.quantity == 0:
                self.add_error(
                    'product',
                    f'"{product.description}" no tiene stock disponible.'
                )
            elif quantity > product.quantity:
                self.add_error(
                    'quantity',
                    f'Stock insuficiente. Disponible: {product.quantity} unidad(es).'
                )
        return cleaned


# Formset inline — mínimo 1 item, máximo 50
SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem,
    form=SaleItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model  = Payment
        fields = ['date', 'amount', 'payment_type', 'reference', 'notes']
        labels = {
            'date':         'Fecha de pago',
            'amount':       'Monto (Gs.)',
            'payment_type': 'Tipo de pago',
            'reference':    'Referencia / comprobante',
            'notes':        'Notas',
        }
        widgets = {
            'date':      forms.DateInput(attrs={'type': 'date'}),
            'amount':    forms.NumberInput(attrs={'min': '1', 'step': '1', 'placeholder': '0'}),
            'reference': forms.TextInput(attrs={'placeholder': 'Nro. de transferencia, voucher...'}),
            'notes':     forms.TextInput(attrs={'placeholder': 'Notas adicionales'}),
        }

    def __init__(self, sale=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sale = sale
        self.fields['reference'].required = False
        self.fields['notes'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        if self.sale and amount:
            if amount > self.sale.balance:
                raise forms.ValidationError(
                    f'El monto ({amount:,.0f} Gs.) supera el saldo pendiente ({self.sale.balance:,.0f} Gs.).'
                )
        return amount
