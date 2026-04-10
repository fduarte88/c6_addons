from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model  = Customer
        fields = [
            'doc_type', 'doc_number',
            'first_name', 'last_name',
            'phone', 'email',
            'city', 'address',
            'is_active',
        ]
        labels = {
            'doc_type':   'Tipo de documento',
            'doc_number': 'Número de documento',
            'first_name': 'Nombre',
            'last_name':  'Apellido',
            'phone':      'Teléfono',
            'email':      'Correo electrónico',
            'city':       'Ciudad',
            'address':    'Dirección particular',
            'is_active':  'Cliente activo',
        }
        widgets = {
            'doc_type':   forms.Select(),
            'doc_number': forms.TextInput(attrs={'placeholder': 'Ej: 1234567890'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'phone':      forms.TextInput(attrs={'placeholder': 'Ej: +57 300 000 0000'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'city':       forms.TextInput(attrs={'placeholder': 'Ej: Bogotá'}),
            'address':    forms.TextInput(attrs={'placeholder': 'Calle, número, barrio'}),
        }

    def clean_doc_number(self):
        value = self.cleaned_data.get('doc_number', '').strip()
        qs = Customer.objects.filter(doc_number=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un cliente con ese número de documento.')
        return value

    def clean_email(self):
        value = self.cleaned_data.get('email', '').strip().lower()
        qs = Customer.objects.filter(email=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un cliente con ese correo electrónico.')
        return value
