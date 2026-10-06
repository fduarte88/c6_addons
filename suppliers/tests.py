from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from quotes.models import Quote
from .models import Supplier


class SupplierDeleteTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user('operador', password='x'))
        self.supplier = Supplier.objects.create(name='Proveedor test')
        self.url = reverse('supplier_delete', args=[self.supplier.pk])

    def test_proveedor_sin_presupuestos_se_elimina(self):
        self.client.post(self.url)
        self.assertFalse(Supplier.objects.filter(pk=self.supplier.pk).exists())

    def test_proveedor_con_presupuestos_no_se_elimina_y_avisa(self):
        Quote.objects.create(supplier=self.supplier, cotizacion=7300)

        page = self.client.get(self.url)
        self.assertContains(page, 'tiene presupuestos registrados')
        self.assertNotContains(page, 'Sí, eliminar')

        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('supplier_list'))
        self.assertContains(response, 'tiene presupuestos registrados')
        self.assertTrue(Supplier.objects.filter(pk=self.supplier.pk).exists())
