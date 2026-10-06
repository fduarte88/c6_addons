import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import CategoryForm, ProductForm
from .models import Category, Product, ProductSize

MEDIA_TMP = tempfile.mkdtemp()


def fake_image(name='camiseta.png'):
    buf = io.BytesIO()
    Image.new('RGB', (40, 40), (23, 28, 38)).save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class ProductImageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self.client.force_login(User.objects.create_user('operador', password='x'))
        self.polo = Category.objects.create(
            name='Polo test', parent=Category.objects.create(name='Camisetas test', tipo=Category.TIPO_VESTIMENTA)
        )

    def post_product(self, url, **extra):
        data = {
            'description': 'Camiseta polo azul', 'category': self.polo.pk, 'talles': ['M', 'L'], 'quantity': '0',
            'cost': '50.000', 'list_price': '150.000', 'distributor_price': '120.000',
        }
        data.update(extra)
        return self.client.post(url, data)

    def test_crear_producto_con_imagen(self):
        response = self.post_product(reverse('product_create'), image=fake_image())
        self.assertRedirects(response, reverse('product_list'))
        product = Product.objects.get()
        self.assertTrue(product.image.name.startswith('productos/'))
        self.assertEqual(product.list_price, 150000)

    def test_quitar_imagen_al_editar(self):
        self.post_product(reverse('product_create'), image=fake_image())
        product = Product.objects.get()
        self.post_product(reverse('product_edit', args=[product.pk]), **{'image-clear': 'on', 'is_active': 'on'})
        product.refresh_from_db()
        self.assertFalse(product.image)

    def test_talles_se_guardan_en_orden_y_son_obligatorios_en_vestimenta(self):
        self.post_product(reverse('product_create'), talles=['XL', 'S', 'M'])
        self.assertEqual(Product.objects.get().talles, ['S', 'M', 'XL'])

        response = self.post_product(reverse('product_create'), talles=[])
        self.assertIn('talles', response.context['form'].errors)
        self.assertEqual(Product.objects.count(), 1)

    def test_archivo_que_no_es_imagen_se_rechaza(self):
        txt = SimpleUploadedFile('nota.png', b'no soy una imagen', content_type='image/png')
        response = self.post_product(reverse('product_create'), image=txt)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors.get('image'))
        self.assertFalse(Product.objects.exists())


class CategoryFormTests(TestCase):
    def test_subcategoria_toma_el_tipo_del_padre_aunque_no_se_envie(self):
        padre = Category.objects.create(name='Camperas test', tipo=Category.TIPO_VESTIMENTA)
        form = CategoryForm(data={'name': 'Rompevientos', 'parent': padre.pk, 'is_active': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().tipo, Category.TIPO_VESTIMENTA)

    def test_categoria_con_subcategorias_no_puede_tener_padre(self):
        a = Category.objects.create(name='A')
        b = Category.objects.create(name='B')
        Category.objects.create(name='A1', parent=a)
        form = CategoryForm(data={'name': 'A', 'parent': b.pk, 'tipo': 'GEN'}, instance=a)
        self.assertFalse(form.is_valid())
        self.assertIn('parent', form.errors)

    def test_solo_categorias_principales_como_padre(self):
        a = Category.objects.create(name='A')
        a1 = Category.objects.create(name='A1', parent=a)
        choices = set(CategoryForm().fields['parent'].queryset)
        self.assertIn(a, choices)
        self.assertNotIn(a1, choices)

    def test_no_se_elimina_categoria_con_subcategorias(self):
        admin = User.objects.create_user('admin', password='x')
        admin.profile.role = 'admin'
        admin.profile.save()
        self.client.force_login(admin)
        a = Category.objects.create(name='A')
        Category.objects.create(name='A1', parent=a)
        self.client.post(reverse('category_delete', args=[a.pk]))
        self.assertTrue(Category.objects.filter(pk=a.pk).exists())


class SizeStockTests(TestCase):
    """Stock por talle: Compras suman al talle, Ventas descuentan y cancelar devuelve."""

    def setUp(self):
        from customers.models import Customer
        self.customer = Customer.objects.create(
            doc_number='123', first_name='Ana', last_name='Pérez', phone='0981000000', city='Asunción', address='x',
        )
        remeras = Category.objects.create(name='Remeras test', tipo=Category.TIPO_VESTIMENTA)
        self.remera = Product.objects.create(
            description='Remera básica', category=remeras, cost=1, list_price=75000, distributor_price=75000,
        )
        for talle in ('S', 'M', 'L'):
            ProductSize.objects.create(product=self.remera, talle=talle)

    def stock(self):
        self.remera.refresh_from_db()
        return self.remera.quantity, {s.talle: s.quantity for s in self.remera.sizes.all()}

    def comprar(self, talle, qty):
        from purchases.models import Purchase, PurchaseItem
        return PurchaseItem.objects.create(purchase=Purchase.objects.create(), product=self.remera,
                                           talle=talle, quantity=qty, unit_cost=1)

    def vender(self, talle, qty):
        from sales.models import Sale, SaleItem
        sale = Sale.objects.create(customer=self.customer)
        SaleItem.objects.create(sale=sale, product=self.remera, talle=talle, quantity=qty, unit_price=75000)
        return sale

    def test_compra_venta_y_cancelacion_mueven_el_stock_del_talle(self):
        self.comprar('M', 5)
        self.comprar('L', 2)
        self.assertEqual(self.stock(), (7, {'S': 0, 'M': 5, 'L': 2}))

        sale = self.vender('M', 3)
        self.assertEqual(self.stock(), (4, {'S': 0, 'M': 2, 'L': 2}))

        self.client.force_login(User.objects.create_user('op', password='x'))
        self.client.post(reverse('sale_cancel', args=[sale.pk]))
        self.assertEqual(self.stock(), (7, {'S': 0, 'M': 5, 'L': 2}))

    def test_borrar_una_compra_revierte_el_stock_del_talle(self):
        item = self.comprar('S', 4)
        self.client.force_login(User.objects.create_user('op', password='x'))
        self.client.post(reverse('purchase_delete', args=[item.purchase_id]))
        self.assertEqual(self.stock(), (0, {'S': 0, 'M': 0, 'L': 0}))

    def test_venta_valida_talle_y_stock_del_talle(self):
        from sales.forms import SaleItemForm
        self.comprar('M', 2)
        data = {'product': self.remera.pk, 'quantity': 1, 'unit_price': 75000}
        self.assertIn('talle', SaleItemForm(data={**data, 'talle': ''}).errors)
        self.assertIn('talle', SaleItemForm(data={**data, 'talle': 'XL'}).errors)       # no ofrecido
        form = SaleItemForm(data={**data, 'talle': 'M', 'quantity': 3})
        self.assertIn('Stock insuficiente en talle M', form.errors['quantity'][0])
        self.assertTrue(SaleItemForm(data={**data, 'talle': 'M', 'quantity': 2}).is_valid())

    def test_compra_exige_talle_ofrecido(self):
        from purchases.forms import PurchaseItemForm
        data = {'product': self.remera.pk, 'quantity': 1, 'unit_cost': 1}
        self.assertIn('talle', PurchaseItemForm(data={**data, 'talle': ''}).errors)
        self.assertTrue(PurchaseItemForm(data={**data, 'talle': 'S'}).is_valid())

    def test_no_se_quita_un_talle_con_stock(self):
        self.comprar('M', 1)
        form = ProductForm(instance=self.remera, data={
            'description': 'Remera básica', 'category': self.remera.category_id, 'quantity': 1,
            'cost': '1', 'list_price': '75.000', 'distributor_price': '75.000', 'talles': ['S', 'L'],
        })
        self.assertFalse(form.is_valid())
        self.assertIn('M (1)', form.errors['talles'][0])


class ProductDeleteTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user('operador', password='x'))
        self.product = Product.objects.create(
            description='Gorra', category=Category.objects.create(name='Accesorios test'),
            cost=1, list_price=50000, distributor_price=45000,
        )
        self.url = reverse('product_delete', args=[self.product.pk])

    def test_producto_sin_movimientos_se_elimina(self):
        self.client.post(self.url)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_producto_con_compras_no_se_elimina_y_avisa(self):
        from purchases.models import Purchase, PurchaseItem
        PurchaseItem.objects.create(purchase=Purchase.objects.create(), product=self.product, quantity=1, unit_cost=1)

        page = self.client.get(self.url)
        self.assertContains(page, 'tiene ventas o compras registradas')
        self.assertNotContains(page, 'Sí, eliminar')

        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('product_list'))
        self.assertContains(response, 'tiene ventas o compras registradas')
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
