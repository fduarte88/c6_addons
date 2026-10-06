import django.db.models.deletion
from django.db import migrations, models

TALLES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']


def spread(total, n):
    """Reparte el stock en n talles: partes iguales y el resto a los talles del medio."""
    base, rest = divmod(total, n)
    parts = [base] * n
    middle_first = sorted(range(n), key=lambda i: abs(i - (n - 1) / 2))
    for i in middle_first[:rest]:
        parts[i] += 1
    return parts


def talles_to_sizes(apps, schema_editor):
    Product     = apps.get_model('products', 'Product')
    ProductSize = apps.get_model('products', 'ProductSize')
    db          = schema_editor.connection.alias
    for product in Product.objects.using(db).exclude(talles=[]):
        talles = sorted(product.talles, key=TALLES.index)
        for talle, qty in zip(talles, spread(product.quantity, len(talles))):
            ProductSize.objects.using(db).create(
                product=product, talle=talle, quantity=qty, position=TALLES.index(talle),
            )


def sizes_to_talles(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    db      = schema_editor.connection.alias
    for product in Product.objects.using(db).filter(sizes__isnull=False).distinct():
        product.talles = list(product.sizes.order_by('position').values_list('talle', flat=True))
        product.save(using=db, update_fields=['talles'])


class Migration(migrations.Migration):
    """Stock por talle: cada talle ofrecido pasa a ser un ProductSize con su propio stock."""

    dependencies = [
        ('products', '0009_product_talles'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductSize',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('talle', models.CharField(choices=[('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'), ('3XL', '3XL')], max_length=5, verbose_name='Talle')),
                ('position', models.PositiveSmallIntegerField(default=0, editable=False)),
                ('quantity', models.PositiveIntegerField(default=0, verbose_name='Stock')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sizes', to='products.product', verbose_name='Producto')),
            ],
            options={
                'verbose_name': 'Talle de producto',
                'verbose_name_plural': 'Talles de producto',
                'ordering': ['position'],
                'constraints': [models.UniqueConstraint(fields=('product', 'talle'), name='unique_product_talle')],
            },
        ),
        migrations.RunPython(talles_to_sizes, sizes_to_talles),
        migrations.RemoveField(
            model_name='product',
            name='talles',
        ),
    ]
