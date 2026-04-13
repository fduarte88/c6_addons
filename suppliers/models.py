from django.db import models


class Supplier(models.Model):
    name       = models.CharField('Nombre / Razón social', max_length=200)
    doc_number = models.CharField('RUC / NIT / Documento', max_length=30, blank=True)
    contact    = models.CharField('Contacto', max_length=100, blank=True)
    phone      = models.CharField('Teléfono', max_length=25, blank=True)
    email      = models.EmailField('Correo electrónico', blank=True)
    address    = models.CharField('Dirección', max_length=200, blank=True)
    notes      = models.TextField('Notas', blank=True)
    is_active  = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def initials(self):
        words = self.name.split()
        return (words[0][:1] + (words[1][:1] if len(words) > 1 else '')).upper()
