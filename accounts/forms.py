from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repite la contraseña'}),
    )
    role = forms.ChoiceField(
        label='Rol',
        choices=UserProfile.ROLE_CHOICES,
    )
    phone = forms.CharField(
        label='Teléfono',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Número de teléfono'}),
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username':   'Usuario',
            'first_name': 'Nombre',
            'last_name':  'Apellido',
            'email':      'Correo electrónico',
        }
        widgets = {
            'username':   forms.TextInput(attrs={'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            profile = user.profile
            profile.role  = self.cleaned_data['role']
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        label='Rol',
        choices=UserProfile.ROLE_CHOICES,
    )
    phone = forms.CharField(
        label='Teléfono',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Número de teléfono'}),
    )
    is_active = forms.BooleanField(
        label='Usuario activo',
        required=False,
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username':   'Usuario',
            'first_name': 'Nombre',
            'last_name':  'Apellido',
            'email':      'Correo electrónico',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['role'].initial  = self.instance.profile.role
            self.fields['phone'].initial = self.instance.profile.phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = user.profile
            profile.role  = self.cleaned_data['role']
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user
