import django.db.models.deletion
from django.db import migrations, models


def migrate_origin_text_to_fk(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Origin  = apps.get_model('products', 'Origin')
    db      = schema_editor.connection.alias

    for product in Product.objects.using(db).all():
        text = (product.origin_text or '').strip()
        if not text:
            product.origin = None
        else:
            origin, _ = Origin.objects.using(db).get_or_create(name=text)
            product.origin = origin
        product.save(using=db, update_fields=['origin'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_fix_calce_us_uk_choices'),
    ]

    operations = [
        # 1. Crear modelo Origin
        migrations.CreateModel(
            name='Origin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='País de procedencia')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={
                'verbose_name': 'Procedencia',
                'verbose_name_plural': 'Procedencias',
                'ordering': ['name'],
            },
        ),
        # 2. Renombrar columna actual a origin_text (guarda los datos)
        migrations.RenameField(
            model_name='product',
            old_name='origin',
            new_name='origin_text',
        ),
        # 3. Agregar nueva FK nullable
        migrations.AddField(
            model_name='product',
            name='origin',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='products.origin',
                verbose_name='Procedencia',
            ),
        ),
        # 4. Migrar texto → FK
        migrations.RunPython(migrate_origin_text_to_fk, migrations.RunPython.noop),
        # 5. Eliminar columna de texto ya innecesaria
        migrations.RemoveField(
            model_name='product',
            name='origin_text',
        ),
    ]
