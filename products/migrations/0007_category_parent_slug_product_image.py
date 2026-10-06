import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify


def fill_category_slugs(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    db       = schema_editor.connection.alias
    used     = set()

    for category in Category.objects.using(db).order_by('pk'):
        base = slugify(category.name) or 'categoria'
        slug, n = base, 2
        while slug in used:
            slug = f'{base}-{n}'
            n += 1
        used.add(slug)
        category.slug = slug
        category.save(using=db, update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_origin_model'),
    ]

    operations = [
        # 1. Subcategorías
        migrations.AddField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='children', to='products.category',
                verbose_name='Categoría padre',
            ),
        ),

        # 2. Slug: se agrega nullable y sin índice, se completa y luego se vuelve único
        #    (sin índice en este paso: si no, PostgreSQL crea dos veces el índice "_like")
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(max_length=120, null=True, blank=True, db_index=False, verbose_name='Slug'),
        ),
        migrations.RunPython(fill_category_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(
                blank=True, max_length=120, unique=True, verbose_name='Slug',
                help_text='Se usa en la URL de la tienda. Se genera desde el nombre.',
            ),
        ),

        # 3. Imagen del producto para la tienda online
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(
                blank=True, upload_to='productos/', verbose_name='Imagen',
                help_text='Foto que se muestra en la tienda online',
            ),
        ),
    ]
