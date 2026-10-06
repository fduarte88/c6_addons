from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer
from products.models import Category, Product
from .forms import SaleItemForm
from .models import Sale, SaleItem


class ConceptoLibreTests(TestCase):
    """Líneas de venta sin producto (servicio, deuda): suman al total pero no mueven stock."""

    def setUp(self):
        self.client.force_login(User.objects.create_user('operador', password='x'))
        self.customer = Customer.objects.create(
            doc_number='123', first_name='Ana', last_name='Pérez', phone='0981000000', city='Asunción', address='x',
        )
        self.gorra = Product.objects.create(
            description='Gorra', category=Category.objects.create(name='Accesorios test'),
            cost=1, list_price=50000, distributor_price=45000,
        )
        self.gorra.add_stock(5)

    def stock(self):
        self.gorra.refresh_from_db()
        return self.gorra.quantity

    def test_pantalla_de_carga_ofrece_conceptos(self):
        page = self.client.get(reverse('sale_create'))
        self.assertContains(page, 'Agregar concepto')
        self.assertContains(page, 'name="items-0-description"')

    def test_concepto_suma_al_total_sin_mover_stock(self):
        sale = Sale.objects.create(customer=self.customer)
        SaleItem.objects.create(sale=sale, description='Deuda anterior', quantity=1, unit_price=300000)
        SaleItem.objects.create(sale=sale, product=self.gorra, quantity=2, unit_price=45000)
        sale.update_status()

        self.assertEqual(sale.total, 390000)
        self.assertEqual(sale.balance, 390000)
        self.assertEqual(sale.status, Sale.STATUS_PENDING)
        self.assertEqual(self.stock(), 3)

    def test_linea_sin_producto_ni_concepto_no_se_guarda(self):
        sale = Sale.objects.create(customer=self.customer)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SaleItem.objects.create(sale=sale, quantity=1, unit_price=1000)

    def test_formulario_de_linea(self):
        sin_nada = SaleItemForm(data={'quantity': 1, 'unit_price': 1000})
        self.assertIn('description', sin_nada.errors)

        sin_monto = SaleItemForm(data={'description': 'Bordado', 'quantity': 1, 'unit_price': 0})
        self.assertIn('unit_price', sin_monto.errors)

        servicio = SaleItemForm(data={'description': 'Bordado', 'quantity': 3, 'unit_price': 15000, 'talle': 'M'})
        self.assertTrue(servicio.is_valid(), servicio.errors)
        self.assertEqual(servicio.cleaned_data['talle'], '')

        # Con producto, el texto de la descripción se ignora (sale del catálogo)
        producto = SaleItemForm(data={'product': self.gorra.pk, 'description': 'Gorra', 'quantity': 1, 'unit_price': 45000})
        self.assertTrue(producto.is_valid(), producto.errors)
        self.assertEqual(producto.cleaned_data['description'], '')

    def test_venta_con_producto_y_concepto_desde_el_formulario(self):
        response = self.client.post(reverse('sale_create'), {
            'customer': self.customer.pk, 'date': '06/10/2026', 'notes': '',
            'items-TOTAL_FORMS': 2, 'items-INITIAL_FORMS': 0, 'items-MIN_NUM_FORMS': 1, 'items-MAX_NUM_FORMS': 1000,
            'items-0-product': self.gorra.pk, 'items-0-description': 'Gorra', 'items-0-quantity': 1, 'items-0-unit_price': 45000,
            'items-1-product': '', 'items-1-description': 'Servicio de bordado', 'items-1-quantity': 2, 'items-1-unit_price': 20000,
        })
        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.pk]))
        self.assertEqual(sale.total, 85000)
        self.assertEqual(self.stock(), 4)

        detalle = self.client.get(reverse('sale_detail', args=[sale.pk]))
        self.assertContains(detalle, 'Servicio de bordado')
        self.assertContains(detalle, 'Concepto libre')

        estado = self.client.get(reverse('customer_statement', args=[self.customer.pk]))
        self.assertContains(estado, 'Servicio de bordado')

        pdf = self.client.get(reverse('customer_statement_pdf', args=[self.customer.pk]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')

    def post_venta(self, *filas):
        data = {
            'customer': self.customer.pk, 'date': '06/10/2026', 'notes': '',
            'items-TOTAL_FORMS': len(filas), 'items-INITIAL_FORMS': 0,
            'items-MIN_NUM_FORMS': 1, 'items-MAX_NUM_FORMS': 1000,
        }
        for i, fila in enumerate(filas):
            base = {'product': '', 'description': '', 'quantity': 1, 'unit_price': ''}
            data.update({f'items-{i}-{k}': v for k, v in {**base, **fila}.items()})
        return self.client.post(reverse('sale_create'), data)

    def test_filas_vacias_se_ignoran(self):
        # La primera fila quedó vacía y el concepto se cargó en la segunda
        response = self.post_venta({}, {'description': 'Calzado futsal adidas', 'unit_price': 400000})
        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.pk]))
        self.assertEqual([i.label for i in sale.items.all()], ['Calzado futsal adidas'])
        self.assertEqual(sale.total, 400000)

    def test_sin_ninguna_linea_cargada_avisa(self):
        response = self.post_venta({}, {})
        self.assertContains(response, 'Agrega al menos un producto o concepto.')
        self.assertFalse(Sale.objects.exists())

    def test_cancelar_devuelve_solo_el_stock_de_productos(self):
        sale = Sale.objects.create(customer=self.customer)
        SaleItem.objects.create(sale=sale, product=self.gorra, quantity=2, unit_price=45000)
        SaleItem.objects.create(sale=sale, description='Envío & embalaje <urgente>', quantity=1, unit_price=25000)
        self.assertEqual(self.stock(), 3)

        self.client.post(reverse('sale_cancel', args=[sale.pk]))
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.STATUS_CANCELLED)
        self.assertEqual(self.stock(), 5)

    def test_pdf_con_concepto_con_caracteres_especiales(self):
        sale = Sale.objects.create(customer=self.customer)
        SaleItem.objects.create(sale=sale, description='Envío & embalaje <urgente>', quantity=1, unit_price=25000)
        pdf = self.client.get(reverse('customer_statement_pdf', args=[self.customer.pk]))
        self.assertEqual(pdf.status_code, 200)
