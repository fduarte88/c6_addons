import io
import json
from datetime import date as date_type
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from customers.models import Customer
from products.models import Product
from .models import Sale, SaleItem, Payment
from .forms import SaleForm, SaleItemFormSet, PaymentForm
from purchases.models import Purchase, PurchaseItem

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ──────────────────────────────────────────
# VENTAS — Lista
# ──────────────────────────────────────────

@login_required
def sale_list(request):
    query    = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'active')  # active | paid | cancelled

    base_qs = Sale.objects.select_related('customer').prefetch_related('items', 'payments')

    if query:
        base_qs = base_qs.filter(
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)  |
            Q(customer__doc_number__icontains=query)  |
            Q(pk__icontains=query)
        )

    sales_active    = base_qs.filter(status__in=[Sale.STATUS_PENDING, Sale.STATUS_PARTIAL]).order_by('-date', '-pk')
    sales_paid      = base_qs.filter(status=Sale.STATUS_PAID).order_by('-date', '-pk')
    sales_cancelled = base_qs.filter(status=Sale.STATUS_CANCELLED).order_by('-date', '-pk')

    tab_sales = {'active': sales_active, 'paid': sales_paid, 'cancelled': sales_cancelled}
    current_sales = list(tab_sales.get(active_tab, sales_active))

    tab_total        = sum(s.total      for s in current_sales)
    tab_total_paid   = sum(s.total_paid for s in current_sales)
    tab_total_saldo  = sum(s.balance    for s in current_sales)

    context = {
        'sales_active':    sales_active,
        'sales_paid':      sales_paid,
        'sales_cancelled': sales_cancelled,
        'tab_total':       tab_total,
        'tab_total_paid':  tab_total_paid,
        'tab_total_saldo': tab_total_saldo,
        'query':           query,
        'active_tab':      active_tab,
        'total_ventas':    Sale.objects.count(),
        'total_pending':   Sale.objects.filter(status=Sale.STATUS_PENDING).count(),
        'total_partial':   Sale.objects.filter(status=Sale.STATUS_PARTIAL).count(),
        'total_paid':      Sale.objects.filter(status=Sale.STATUS_PAID).count(),
        'total_cancelled': Sale.objects.filter(status=Sale.STATUS_CANCELLED).count(),
    }
    return render(request, 'sales/list.html', context)


# ──────────────────────────────────────────
# VENTAS — Crear
# ──────────────────────────────────────────

@login_required
def sale_create(request):
    # JSON de precios distribuidor para autocompletar en el formulario
    prices = {str(p.pk): float(p.distributor_price)
              for p in Product.objects.filter(is_active=True, quantity__gt=0)}

    if request.method == 'POST':
        form    = SaleForm(request.POST)
        formset = SaleItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                sale = form.save()
                formset.instance = sale
                formset.save()
                sale.update_status()
            messages.success(request, f'Venta #{sale.pk} registrada correctamente.')
            return redirect('sale_detail', pk=sale.pk)
    else:
        form    = SaleForm()
        formset = SaleItemFormSet()

    return render(request, 'sales/form.html', {
        'form':      form,
        'formset':   formset,
        'action':    'Nueva',
        'prices_json': json.dumps(prices),
    })


# ──────────────────────────────────────────
# VENTAS — Detalle
# ──────────────────────────────────────────

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('customer')
                    .prefetch_related('items__product', 'payments'),
        pk=pk
    )
    payment_form = PaymentForm(sale=sale, initial={'date': sale.date})
    return render(request, 'sales/detail.html', {
        'sale':         sale,
        'payment_form': payment_form,
    })


# ──────────────────────────────────────────
# VENTAS — Cancelar
# ──────────────────────────────────────────

@login_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status != Sale.STATUS_CANCELLED:
            # Devuelve stock de cada ítem
            for item in sale.items.select_related('product').all():
                item.product.quantity += item.quantity
                item.product.save(update_fields=['quantity'])
        sale.status = Sale.STATUS_CANCELLED
        sale.save(update_fields=['status'])
        messages.success(request, f'Venta #{sale.pk} cancelada.')
        return redirect('sale_list')
    return render(request, 'sales/confirm_cancel.html', {'sale': sale})


# ──────────────────────────────────────────
# PAGOS — Agregar pago a una venta
# ──────────────────────────────────────────

@login_required
def payment_add(request, sale_pk):
    sale = get_object_or_404(Sale, pk=sale_pk)

    if sale.status == Sale.STATUS_PAID:
        messages.error(request, 'Esta venta ya está totalmente pagada.')
        return redirect('sale_detail', pk=sale.pk)

    if sale.status == Sale.STATUS_CANCELLED:
        messages.error(request, 'No se pueden registrar pagos en una venta cancelada.')
        return redirect('sale_detail', pk=sale.pk)

    if request.method == 'POST':
        form = PaymentForm(sale=sale, data=request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale = sale
            payment.save()  # sale.update_status() se llama en Payment.save()
            messages.success(
                request,
                f'Pago de Gs. {payment.amount:,.0f} registrado. '
                f'Saldo restante: Gs. {sale.balance:,.0f}.'
            )
            return redirect('sale_detail', pk=sale.pk)
    else:
        form = PaymentForm(sale=sale)

    return render(request, 'sales/payment_form.html', {'form': form, 'sale': sale})


# ──────────────────────────────────────────
# PAGOS — Eliminar pago
# ──────────────────────────────────────────

@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    sale    = payment.sale
    if request.method == 'POST':
        payment.delete()
        sale.update_status()
        messages.success(request, 'Pago eliminado.')
        return redirect('sale_detail', pk=sale.pk)
    return render(request, 'sales/payment_confirm_delete.html', {'payment': payment})


# ──────────────────────────────────────────
# ESTADO DE CUENTA — por cliente
# ──────────────────────────────────────────

@login_required
def customer_statement(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    sales    = Sale.objects.filter(customer=customer) \
                           .exclude(status=Sale.STATUS_CANCELLED) \
                           .prefetch_related('items__product', 'payments') \
                           .order_by('-date', '-created_at')

    # Totales globales del cliente
    total_ventas  = sum(s.total       for s in sales)
    total_pagado  = sum(s.total_paid  for s in sales)
    total_saldo   = sum(s.balance     for s in sales
                        if s.status != Sale.STATUS_CANCELLED)

    context = {
        'customer':     customer,
        'sales':        sales,
        'total_ventas': total_ventas,
        'total_pagado': total_pagado,
        'total_saldo':  total_saldo,
    }
    return render(request, 'sales/statement.html', context)


# ──────────────────────────────────────────
# API — Búsqueda de clientes (AJAX)
# ──────────────────────────────────────────

@login_required
def customer_lookup_api(request, pk):
    """Devuelve datos de un cliente por su ID (código)."""
    try:
        c = Customer.objects.get(pk=pk, is_active=True)
        return JsonResponse({
            'id':       c.pk,
            'code':     c.pk,
            'name':     c.full_name,
            'doc':      c.doc_number,
            'phone':    c.phone_display,
        })
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)


@login_required
def customer_search_api(request):
    """Busca clientes activos por nombre, apellido o documento. q='*' devuelve todos."""
    q = request.GET.get('q', '').strip()
    base_qs = Customer.objects.filter(is_active=True).order_by('last_name', 'first_name')
    if not q or q == '*':
        customers = base_qs[:50]
    else:
        customers = base_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(doc_number__icontains=q) |
            Q(pk__icontains=q)
        )[:20]
    results = [
        {'id': c.pk, 'code': c.pk, 'name': c.full_name, 'doc': c.doc_number}
        for c in customers
    ]
    return JsonResponse({'results': results})


# ──────────────────────────────────────────
# PDF — Estado de cuenta por cliente
# ──────────────────────────────────────────

def _gs(value):
    """Formatea número como Gs. con puntos de miles."""
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        v = 0
    return f'Gs. {v:,}'.replace(',', '.')


@login_required
def customer_statement_pdf(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    sales = Sale.objects.filter(customer=customer) \
                        .exclude(status=Sale.STATUS_CANCELLED) \
                        .prefetch_related('items__product', 'payments') \
                        .order_by('-date', '-pk')

    total_ventas = sum(s.total      for s in sales)
    total_pagado = sum(s.total_paid for s in sales)
    total_saldo  = sum(s.balance    for s in sales if s.status != Sale.STATUS_CANCELLED)

    # ── Colores ────────────────────────────────────────────────────────────
    NAVY    = colors.HexColor('#171c26')
    STEEL   = colors.HexColor('#8faab0')
    LIGHT   = colors.HexColor('#f0f4f5')
    WHITE   = colors.white
    RED     = colors.HexColor('#c0392b')
    GREEN   = colors.HexColor('#27ae60')
    GREY    = colors.HexColor('#6b7280')
    BORDER  = colors.HexColor('#d1d9db')

    # ── Estilos ────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def style(name, **kw):
        kw.setdefault('parent', styles['Normal'])
        return ParagraphStyle(name, **kw)

    s_title    = style('Title',    fontSize=16, textColor=NAVY,  leading=20, spaceAfter=2)
    s_subtitle = style('Sub',      fontSize=9,  textColor=GREY,  leading=12)
    s_label    = style('Label',    fontSize=7,  textColor=GREY,  leading=9,  spaceAfter=1)
    s_value    = style('Value',    fontSize=9,  textColor=NAVY,  leading=11, fontName='Helvetica-Bold')
    s_section  = style('Section',  fontSize=8,  textColor=WHITE, leading=10, fontName='Helvetica-Bold')
    s_normal   = style('Norm',     fontSize=8,  textColor=NAVY,  leading=10)
    s_muted    = style('Muted',    fontSize=7,  textColor=GREY,  leading=9,  fontStyle='italic')
    s_right    = style('Right',    fontSize=8,  textColor=NAVY,  leading=10, alignment=TA_RIGHT)
    s_bold_r   = style('BoldR',    fontSize=8,  textColor=NAVY,  leading=10, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    s_total    = style('Total',    fontSize=9,  textColor=NAVY,  leading=11, fontName='Helvetica-Bold')
    s_total_r  = style('TotalR',   fontSize=9,  textColor=NAVY,  leading=11, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    s_saldo    = style('Saldo',    fontSize=9,  textColor=RED,   leading=11, fontName='Helvetica-Bold', alignment=TA_RIGHT)

    # ── Documento ──────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    W = doc.width
    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────
    story.append(Paragraph('c6 Store', style('Brand', fontSize=10, textColor=STEEL, fontName='Helvetica-Bold')))
    story.append(Paragraph('Estado de Cuenta', s_title))
    story.append(Paragraph(
        f'{customer.full_name} &mdash; {customer.get_doc_type_display()} {customer.doc_number}',
        s_subtitle,
    ))
    story.append(Paragraph(
        f'Teléfono: {customer.phone_display} &nbsp;&nbsp; Generado: {date_type.today().strftime("%d/%m/%Y")}',
        s_muted,
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=10, spaceBefore=6))

    # ── Resumen ────────────────────────────────────────────────────────────
    resumen_data = [
        [
            Paragraph('Total facturado', s_label),
            Paragraph('Total pagado',    s_label),
            Paragraph('Saldo pendiente', s_label),
            Paragraph('N° de ventas',    s_label),
        ],
        [
            Paragraph(_gs(total_ventas), s_value),
            Paragraph(_gs(total_pagado), style('VP', parent=s_value, textColor=GREEN, fontName='Helvetica-Bold')),
            Paragraph(_gs(total_saldo),  style('VS', parent=s_value, textColor=(RED if total_saldo > 0 else GREEN), fontName='Helvetica-Bold')),
            Paragraph(str(sales.count()), s_value),
        ],
    ]
    resumen_table = Table(resumen_data, colWidths=[W/4]*4, hAlign='LEFT')
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT),
        ('BACKGROUND', (0,1), (-1,1), WHITE),
        ('BOX',        (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT, WHITE]),
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 14))

    # ── Ventas ─────────────────────────────────────────────────────────────
    STATUS_LABELS = {
        Sale.STATUS_PENDING:   'Pendiente',
        Sale.STATUS_PARTIAL:   'Pago parcial',
        Sale.STATUS_PAID:      'Pagado',
        Sale.STATUS_CANCELLED: 'Cancelado',
    }

    for sale in sales:
        cancelled = sale.status == Sale.STATUS_CANCELLED

        # Cabecera de la venta
        status_txt = STATUS_LABELS.get(sale.status, sale.status)
        header_data = [[
            Paragraph(f'Venta #{sale.pk}', s_section),
            Paragraph(sale.date.strftime('%d/%m/%Y'), style('DH', parent=s_section, alignment=TA_CENTER)),
            Paragraph(status_txt, style('SH', parent=s_section, alignment=TA_RIGHT)),
        ]]
        header_color = GREY if cancelled else NAVY
        header_table = Table(header_data, colWidths=[W*0.4, W*0.3, W*0.3])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), header_color),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
            ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ]))
        story.append(header_table)

        if sale.notes:
            story.append(Paragraph(f'Nota: {sale.notes}', style('Note', parent=s_muted, leftIndent=4, spaceBefore=2)))

        # Productos
        items_data = [[
            Paragraph('Producto', s_section),
            Paragraph('Cant.', style('CH', parent=s_section, alignment=TA_RIGHT)),
            Paragraph('Precio unit.', style('CH', parent=s_section, alignment=TA_RIGHT)),
            Paragraph('Subtotal', style('CH', parent=s_section, alignment=TA_RIGHT)),
        ]]
        for item in sale.items.all():
            items_data.append([
                Paragraph(item.product.description, s_normal),
                Paragraph(str(item.quantity), s_right),
                Paragraph(_gs(item.unit_price), s_right),
                Paragraph(_gs(item.subtotal), s_right),
            ])

        items_table = Table(
            items_data,
            colWidths=[W*0.46, W*0.1, W*0.22, W*0.22],
        )
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), STEEL),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT]),
            ('BOX',       (0,0), (-1,-1), 0.5, BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.3, BORDER),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ]))
        story.append(items_table)

        # Totales y pagos
        fin_data = []
        fin_data.append([
            Paragraph('Total venta', s_total),
            Paragraph(_gs(sale.total), s_total_r),
        ])
        for p in sale.payments.all():
            ref = f' ({p.reference})' if p.reference else ''
            label = f'{p.get_payment_type_display()} — {p.date.strftime("%d/%m/%Y")}{ref}'
            fin_data.append([
                Paragraph(label, style('PL', parent=s_normal, textColor=GREEN)),
                Paragraph(f'- {_gs(p.amount)}', style('PA', parent=s_right, textColor=GREEN)),
            ])
        saldo_style = s_saldo if (sale.balance > 0 and not cancelled) else s_total_r
        fin_data.append([
            Paragraph('Saldo', s_total),
            Paragraph(_gs(sale.balance), saldo_style),
        ])

        fin_table = Table(fin_data, colWidths=[W*0.78, W*0.22])
        fin_style = [
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('BOX',  (0,0), (-1,-1), 0.5, BORDER),
            ('LINEABOVE', (0,-1), (-1,-1), 0.8, BORDER),
            ('BACKGROUND', (0,0), (-1,0), LIGHT),
            ('BACKGROUND', (0,-1), (-1,-1), LIGHT),
        ]
        fin_table.setStyle(TableStyle(fin_style))
        story.append(fin_table)
        story.append(Spacer(1, 10))

    if not sales:
        story.append(Paragraph('Este cliente no tiene ventas registradas.', s_muted))

    doc.build(story)
    buf.seek(0)

    filename = f'estado_cuenta_{customer.pk}_{date_type.today().strftime("%Y%m%d")}.pdf'
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ──────────────────────────────────────────
# INFORMES — Resumen general
# ──────────────────────────────────────────

@login_required
def reports(request):
    # ── Compras ──────────────────────────────────────────────────────────
    purchase_items = PurchaseItem.objects.select_related('purchase')
    total_compras  = sum(
        i.subtotal for i in purchase_items
    )

    # ── Ventas (sin canceladas) ───────────────────────────────────────────
    sales_qs       = Sale.objects.exclude(status=Sale.STATUS_CANCELLED) \
                                 .prefetch_related('items', 'payments')
    total_ventas   = sum(s.total      for s in sales_qs)
    total_cobrado  = sum(s.total_paid for s in sales_qs)
    total_pendiente= sum(s.balance    for s in sales_qs)

    context = {
        'total_compras':    total_compras,
        'total_ventas':     total_ventas,
        'total_cobrado':    total_cobrado,
        'total_pendiente':  total_pendiente,
    }
    return render(request, 'sales/reports.html', context)
