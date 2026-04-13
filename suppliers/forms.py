from django import forms
from .models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model  = Supplier
        fields = ['name', 'doc_number', 'contact', 'phone', 'email', 'address', 'notes', 'is_active']
        labels = {
            'name':       'Nombre / Razón social',
            'doc_number': 'RUC / NIT / Documento',
            'contact':    'Persona de contacto',
            'phone':      'Teléfono',
            'email':      'Correo electrónico',
            'address':    'Dirección',
            'notes':      'Notas',
            'is_active':  'Proveedor activo',
        }
        widgets = {
            'name':       forms.TextInput(attrs={'placeholder': 'Nombre o razón social'}),
            'doc_number': forms.TextInput(attrs={'placeholder': 'Ej: 80012345-1'}),
            'contact':    forms.TextInput(attrs={'placeholder': 'Nombre del contacto'}),
            'phone':      forms.TextInput(attrs={'placeholder': 'Ej: 0981 123 456'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'info@info.com'}),
            'address':    forms.TextInput(attrs={'placeholder': 'Dirección del proveedor'}),
            'notes':      forms.Textarea(attrs={'rows': 2, 'placeholder': 'Observaciones opcionales...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['doc_number', 'contact', 'phone', 'email', 'address', 'notes']:
            self.fields[f].required = False
