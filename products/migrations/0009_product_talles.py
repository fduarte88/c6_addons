from django.db import migrations, models


def talle_to_talles(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    db      = schema_editor.connection.alias
    for product in Product.objects.using(db).exclude(talle=''):
        product.talles = [product.talle]
        product.save(using=db, update_fields=['talles'])


def talles_to_talle(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    db      = schema_editor.connection.alias
    for product in Product.objects.using(db).exclude(talles=[]):
        product.talle = product.talles[0]
        product.save(using=db, update_fields=['talle'])


class Migration(migrations.Migration):
    """Un producto de vestimenta pasa de tener un talle a una lista de talles disponibles."""

    dependencies = [
        ('products', '0008_camisetas_subcategories'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='talles',
            field=models.JSONField(
                blank=True, default=list, verbose_name='Talles disponibles',
                help_text='Solo Vestimenta. Lista de TALLE_CHOICES, ej: ["S", "M", "L"]. En la tienda el cliente elige uno.',
            ),
        ),
        migrations.RunPython(talle_to_talles, talles_to_talle),
        migrations.RemoveField(
            model_name='product',
            name='talle',
        ),
    ]
