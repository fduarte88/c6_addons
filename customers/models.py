from django.db import models


class Customer(models.Model):
    DOC_DNI      = 'DNI'
    DOC_CEDULA   = 'CC'
    DOC_PASAPORTE = 'PAS'
    DOC_RUC      = 'RUC'
    DOC_CHOICES = [
        (DOC_DNI,       'DNI'),
        (DOC_CEDULA,    'Cédula de identidad'),
        (DOC_PASAPORTE, 'Pasaporte'),
        (DOC_RUC,       'RUC / NIT'),
    ]

    doc_type   = models.CharField('Tipo de documento', max_length=5, choices=DOC_CHOICES, default=DOC_CEDULA)
    doc_number = models.CharField('Número de documento', max_length=30, unique=True)
    first_name = models.CharField('Nombre', max_length=100)
    last_name  = models.CharField('Apellido', max_length=100)
    phone      = models.CharField('Teléfono', max_length=25)
    email      = models.EmailField('Correo electrónico', unique=True)
    city       = models.CharField('Ciudad', max_length=100)
    address    = models.CharField('Dirección particular', max_length=200)
    is_active  = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField('Fecha de registro', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name}, {self.first_name} [{self.doc_number}]'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def initials(self):
        return f'{self.first_name[:1]}{self.last_name[:1]}'.upper()
