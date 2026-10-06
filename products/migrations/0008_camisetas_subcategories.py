from django.db import migrations
from django.utils.text import slugify

SUBCATEGORIES = ['Polo', 'Básicas', 'Gráficas']


def create_camisetas(apps, schema_editor):
    """'Remeras' pasa a llamarse 'Camisetas' y se le crean las subcategorías de la tienda."""
    Category = apps.get_model('products', 'Category')
    db       = schema_editor.connection.alias
    qs       = Category.objects.using(db)

    camisetas = qs.filter(name='Camisetas').first()
    if camisetas is None:
        camisetas = qs.filter(name='Remeras').first()
    if camisetas is None:
        camisetas = qs.create(name='Camisetas', slug='camisetas', tipo='VES')
    else:
        camisetas.name = 'Camisetas'
        camisetas.slug = 'camisetas'
        camisetas.tipo = 'VES'
        camisetas.save(using=db, update_fields=['name', 'slug', 'tipo'])

    for name in SUBCATEGORIES:
        qs.get_or_create(
            name=name,
            defaults={'slug': slugify(name), 'parent': camisetas, 'tipo': 'VES'},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_category_parent_slug_product_image'),
    ]

    operations = [
        migrations.RunPython(create_camisetas, migrations.RunPython.noop),
    ]
