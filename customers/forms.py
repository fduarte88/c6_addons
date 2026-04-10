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
            'phone':      forms.TextInput(attrs={'placeholder': '9X XXX XXXX', 'class': 'phone-local', 'id': 'id_phone'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'info@info.com'}),
            'city':       forms.TextInput(attrs={'placeholder': 'Ej: Bogotá'}),
            'address':    forms.TextInput(attrs={'placeholder': 'Calle, número, barrio'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        # Al editar, mostrar solo el número local (sin el prefijo 595)
        if self.instance and self.instance.pk and self.instance.phone:
            phone = self.instance.phone
            if phone.startswith('595'):
                self.initial['phone'] = phone[3:]

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        digits = ''.join(filter(str.isdigit, value))
        if not digits:
            raise forms.ValidationError('Ingresa un número de teléfono válido.')
        if not digits.startswith('595'):
            digits = '595' + digits
        return digits

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
        if not value:
            return 'info@info.com'
        return value
