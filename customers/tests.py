from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from sales.models import Sale
from .models import Customer


class CustomerDeleteTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user('operador', password='x'))
        self.customer = Customer.objects.create(
            doc_number='123', first_name='Ana', last_name='Pérez', phone='0981000000', city='Asunción', address='x',
        )
        self.url = reverse('customer_delete', args=[self.customer.pk])

    def test_cliente_sin_ventas_se_elimina(self):
        self.client.post(self.url)
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_cliente_con_ventas_no_se_elimina_y_avisa(self):
        Sale.objects.create(customer=self.customer)

        page = self.client.get(self.url)
        self.assertContains(page, 'tiene ventas registradas')
        self.assertNotContains(page, 'Sí, eliminar')

        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('customer_list'))
        self.assertContains(response, 'tiene ventas registradas')
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())
