from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.urls import reverse
from products.models import Category, Product, ProductSize


class StoreCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gorras = Category.objects.create(name='Gorras', tipo=Category.TIPO_VESTIMENTA)
        cls.trucker = Category.objects.create(name='Trucker', parent=cls.gorras)
        cls.snapback = Category.objects.create(name='Snapback', parent=cls.gorras)
        cls.otra = Category.objects.create(name='Bolsos test', tipo=Category.TIPO_GENERAL)

        cls.barata = cls._product('Gorra trucker negra', cls.trucker, 90000, sizes={'S': 1, 'M': 2, 'L': 2, 'XL': 0})
        cls.cara = cls._product('Gorra snapback azul', cls.snapback, 150000, sizes={'M': 1, 'L': 1})
        cls._product('Gorra sin stock', cls.trucker, 80000, sizes={'M': 0})
        cls._product('Gorra inactiva', cls.snapback, 80000, sizes={'M': 3}, active=False)
        cls._product('Bolso', cls.otra, 50000, qty=4)

    @staticmethod
    def _product(description, category, price, sizes=None, qty=0, active=True):
        """sizes: {talle: stock}; el stock total del producto es la suma."""
        sizes = sizes or {}
        product = Product.objects.create(
            description=description, category=category, is_active=active,
            quantity=sum(sizes.values()) if sizes else qty,
            cost=price // 2, list_price=price, distributor_price=price - 10000,
        )
        for talle, stock in sizes.items():
            ProductSize.objects.create(product=product, talle=talle, quantity=stock)
        return product

    def get(self, **params):
        return self.client.get(reverse('store_category', args=['gorras']), params)

    def test_muestra_solo_productos_a_la_venta_de_la_categoria(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['page'].object_list), {self.barata, self.cara})

    def test_pestanas_con_cantidades(self):
        tabs = self.get().context['tabs']
        self.assertEqual([(t['label'], t['count']) for t in tabs], [('Todos', 2), ('Trucker', 1), ('Snapback', 1)])
        self.assertTrue(tabs[0]['active'])

    def test_filtra_por_subcategoria(self):
        response = self.get(sub='snapback')
        self.assertEqual(list(response.context['page'].object_list), [self.cara])
        self.assertEqual(response.context['current'], self.snapback)

    def test_subcategoria_desconocida_muestra_todos(self):
        response = self.get(sub='no-existe')
        self.assertIsNone(response.context['current'])
        self.assertEqual(response.context['page'].paginator.count, 2)

    def test_orden_por_precio(self):
        asc = self.get(orden='precio-asc').context['page'].object_list
        desc = self.get(orden='precio-desc').context['page'].object_list
        self.assertEqual(list(asc), [self.barata, self.cara])
        self.assertEqual(list(desc), [self.cara, self.barata])

    def test_muestra_precio_de_lista(self):
        self.assertContains(self.get(), 'Gs. 150.000')

    def test_url_de_subcategoria_redirige_a_la_pestana(self):
        response = self.client.get(reverse('store_category', args=['trucker']))
        self.assertRedirects(response, reverse('store_category', args=['gorras']) + '?sub=trucker')

    def test_categoria_inactiva_da_404(self):
        self.gorras.is_active = False
        self.gorras.save()
        self.assertEqual(self.get().status_code, 404)

    def test_sin_productos_muestra_mensaje(self):
        response = self.client.get(reverse('store_category', args=['bolsos-test']) + '?sub=x')
        self.assertContains(response, 'Bolso')
        vacia = Category.objects.create(name='Vacía')
        self.assertContains(self.client.get(reverse('store_category', args=[vacia.slug])), 'Todavía no hay')


    def order(self, product, **params):
        return self.client.get(reverse('store_whatsapp_order', args=[product.pk]), params)

    @override_settings(STORE_WHATSAPP='595981000111')
    def test_tarjeta_con_talles_elegibles_y_boton(self):
        response = self.get(sub='trucker')
        self.assertContains(response, reverse('store_whatsapp_order', args=[self.barata.pk]))
        for talle in ('S', 'M', 'L'):
            self.assertContains(response, f'name="talle" value="{talle}" required')
        self.assertContains(response, 'name="talle" value="XL" disabled')   # agotado
        self.assertContains(response, 'Comprar')

    @override_settings(STORE_WHATSAPP='595981000111')
    def test_pedido_con_talle_redirige_a_whatsapp(self):
        response = self.order(self.barata, talle='L')
        url = urlparse(response['Location'])
        self.assertEqual((url.netloc, url.path), ('wa.me', '/595981000111'))
        text = parse_qs(url.query)['text'][0]
        self.assertIn('Gorra trucker negra (Talle L)', text)
        self.assertIn('Precio: Gs. 90.000', text)
        self.assertIn(f'Código: {self.barata.pk}', text)

    @override_settings(STORE_WHATSAPP='595981000111')
    def test_pedido_sin_talle_o_con_talle_invalido_vuelve_a_la_tienda(self):
        for params in ({}, {'talle': 'XXL'}, {'talle': 'XL'}):   # sin talle, inexistente, agotado
            response = self.order(self.barata, **params)
            self.assertRedirects(response, reverse('store_category', args=['gorras']))

    @override_settings(STORE_WHATSAPP='595981000111')
    def test_producto_sin_talles_no_pide_talle(self):
        bolso = Product.objects.get(description='Bolso')
        self.assertEqual(urlparse(self.order(bolso)['Location']).netloc, 'wa.me')

    @override_settings(STORE_WHATSAPP='595981000111')
    def test_no_se_pide_un_producto_sin_stock(self):
        sin_stock = Product.objects.get(description='Gorra sin stock')
        self.assertEqual(self.order(sin_stock, talle='M').status_code, 404)

    @override_settings(STORE_WHATSAPP='')
    def test_sin_numero_no_hay_boton(self):
        response = self.get()
        self.assertNotContains(response, '/tienda/pedido/')
        self.assertEqual(self.order(self.barata, talle='M').status_code, 404)


class CategoryModelTests(TestCase):
    def test_subcategoria_hereda_tipo_y_se_propaga(self):
        padre = Category.objects.create(name='Buzos', tipo=Category.TIPO_VESTIMENTA)
        hija = Category.objects.create(name='Canguro', parent=padre, tipo=Category.TIPO_GENERAL)
        self.assertEqual(hija.tipo, Category.TIPO_VESTIMENTA)

        padre.tipo = Category.TIPO_GENERAL
        padre.save()
        hija.refresh_from_db()
        self.assertEqual(hija.tipo, Category.TIPO_GENERAL)

    def test_slug_unico_y_nombre_completo(self):
        a = Category.objects.create(name='Niños')
        b = Category.objects.create(name='Ninos')
        self.assertEqual(a.slug, 'ninos')
        self.assertEqual(b.slug, 'ninos-2')
        hija = Category.objects.create(name='Remeras niños', parent=a)
        self.assertEqual(str(hija), 'Niños › Remeras niños')


class LandingTests(TestCase):
    def test_tarjeta_vestimenta_lleva_a_camisetas(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('store_category', args=['camisetas']))
