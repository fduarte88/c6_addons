from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_payment_discount_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='talle',
            field=models.CharField(blank=True, choices=[('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'), ('3XL', '3XL')], help_text='Solo si el producto maneja stock por talle', max_length=5, verbose_name='Talle'),
        ),
    ]
