# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

c6 Store is a Django (server-rendered) back-office for a small retail business: customers, products/stock, sales with payments, purchases from suppliers, reports, and a quote calculator. The UI, model verbose names, URL paths, messages, and commit messages are all in **Spanish**. Currency is the Paraguayan Guaraní (Gs., no decimals, `.` as thousands separator), even though settings use `LANGUAGE_CODE='es-co'` / `America/Bogota`.

## Commands

```bash
pip install -r requirements.txt
python manage.py runserver
python manage.py makemigrations <app>
python manage.py migrate
python manage.py test                        # creates/destroys test_carbono_db; accounts, purchases, quotes, sales have no tests
python manage.py test store.tests.StoreCategoryTests.test_filtra_por_subcategoria
```

`requirements.txt` pins Django 6.0.3, and the migrations were generated with it (BigAutoField ids). Settings has no `DEFAULT_AUTO_FIELD`, so under Django < 6 every command prints `models.W042` warnings (harmless) and `makemigrations` proposes spurious `Alter field id` migrations for every app; don't commit those.

The database is a local PostgreSQL (`carbono_db` on localhost:5432), configured directly in `c6_store/settings.py`; there is no `.env` / local_settings mechanism.

A Django superuser is **not** an app admin: `admin_required` only checks `user.profile.role == 'admin'`, and `UserProfile` is not registered in Django admin. Promote a user via the app's user-management screen or `python manage.py shell`.

## Architecture

Single Django project (`c6_store/`) with one app per domain: `accounts`, `customers`, `products`, `sales`, `purchases`, `suppliers`, `quotes`, plus `store` (the public online shop, no models of its own). All views are function-based. Templates live in the project-level `templates/<app>/`, not in app directories.

Non-obvious placement:
- The public site (no login) is `/` (`home`, a `TemplateView` of `templates/landing.html`) and `/tienda/<slug>/` (`store`). Both extend `templates/store/base.html` (shared header/footer, `lp-` classes in `static/css/landing.css`); the catalog adds `static/css/store.css` (`st-` classes). Both CSS files reuse the palette variables from `main.css`. The "Iniciar sesión" buttons lead to the portal login.
- The brand logo is `static/img/c6-logo.svg` (gray mark, always shown on a black circle like the Instagram profile: `.lp-brand-mark`/`.lp-hero-logo` on the landing, `.brand-logo` on login, `.brand-logo-sm` in the sidebar). `static/img/c6-logo.png` (transparent) is the raster copy used in the ReportLab PDF header. Favicons are declared in `base.html` and `base_dashboard.html`.
- The dashboard view is `accounts.views.dashboard_view`; the reports page ("Informes") is `sales.views.reports`.
- URL prefixes are Spanish (`clientes/`, `productos/`, `ventas/`, `compras/`, `proveedores/`, `presupuestos/`), see `c6_store/urls.py`. Route names are English (`sale_list`, `product_edit`, ...).

### Stock is maintained by model side effects

`Product.quantity` is never edited through forms (`ProductForm.clean_quantity` locks it; new products start at 0). It changes only through `Product.add_stock(qty, talle='')` (SQL `F()` update, clamped at 0), called from:
- `SaleItem.save()/delete()` — decrements/restores stock by the quantity diff (or reverts the old line and applies the new one if the product/size changed).
- `PurchaseItem.save()/delete()` — increments/reverts stock the same way.
- `sales.views.sale_cancel` — restores stock for every item (sale items are kept).

Clothing products have stock per size in `ProductSize` rows (`product.sizes`, one per offered size). When a line has a `talle`, `add_stock` moves that size and recomputes `Product.quantity` as the sum of the sizes, so the total stays valid everywhere else (store filter, lists, APIs).

Because the logic lives in `save()`/`delete()`, bulk queryset operations (`.update()`, `QuerySet.delete()`, cascade deletes) bypass it. That is why `purchase_delete` deletes items one by one before deleting the purchase. Keep this in mind for any new code that removes or edits items.

Sales and purchases have no edit views, and neither app registers its models in Django admin: a sale can only be cancelled and a purchase only deleted. Today nothing reaches the "edit an existing line" branch of `SaleItem.save()`/`PurchaseItem.save()`, so test it if you add editing.

### Sale totals and status

`Sale.total`, `total_paid`, and `balance` are Python properties summing related rows (nothing is stored), so list/report views aggregate in Python and must `prefetch_related('items', 'payments')` to avoid N+1 queries. `Sale.status` (pending/partial/paid) is derived by `Sale.update_status()`, which `Payment.save()` calls automatically; code that deletes payments must call it explicitly. `cancelled` is sticky, and cancelled sales are excluded from statements, the PDF, and reports. A discount is modeled as a `Payment` with `payment_type='DSC'`, so it counts toward `total_paid`.

### Money and date handling

- Guaraní amounts are stored in `DecimalField`s but treated as integers. In templates, `{% load guarani %}` provides the `|gs` ("Gs. 1.500.000") and `|gs_plain` filters (`products/templatetags/guarani.py`); `sales/views.py` has its own `_gs()` for ReportLab output.
- `ProductForm` declares its price fields as `CharField`s with the `gs-input` CSS class (a JS thousands-dot mask), then strips the dots in `_parse_gs`. Follow this pattern for new masked Gs. inputs, because a `DecimalField` form field would reject `1.500.000`.
- Date inputs use `DD/MM/YYYY`: widget `format='%d/%m/%Y'`, class `date-dmy`, and `input_formats = ['%d/%m/%Y', '%Y-%m-%d']` set in the form's `__init__`.

### Permissions

`UserProfile` (role `admin` | `operator`) is auto-created by a `post_save` signal on `User`. The `admin_required` decorator in `accounts/views.py` is stacked under `@login_required` and gates user management plus the category and origin screens (which live in the `products` app). Everything else only requires login, including product create/edit/delete. `base_dashboard.html` hides the admin-only sidebar links with `request.user.profile.is_admin`.

### Frontend

There is no build step and no npm. `static/js/` is empty: all JavaScript is inline in each template's `{% block extra_js %}`. Portal pages extend `base_dashboard.html` (sidebar layout) and fill the blocks `title`, `header_title`, `content`, `extra_js`, plus `nav_<section>` set to `active` to highlight the sidebar link. Portal styling is in `static/css/main.css`. Every stylesheet link carries a cache-busting `?v=N` query (`base.html` and `base_dashboard.html` for `main.css`, `store/base.html` for `landing.css`, `store/category.html` for `store.css`), so bump the matching number after CSS changes.

Sale and purchase forms are keyboard-driven, inline formsets (`SaleItemFormSet` / `PurchaseItemFormSet`, prefix `items`) where rows are added in JS by incrementing `items-TOTAL_FORMS`. Products and customers are picked by numeric code (the PK) through JSON endpoints under `ventas/api/...` and `compras/api/...`: `q='*'` returns up to 50 records, and pressing `*` opens a search modal. The sales product API returns only active, in-stock products priced at `distributor_price`; the purchases API returns all active products with `cost`. JS gets endpoint URLs from `{% url 'name' 0 %}` and strips the `0`.

### Quotes

`SupplierQuoteConfig.fields_config` is a per-supplier JSON list that defines the calculator's dynamic fields (`key`, `label`, `type`: number|percent|auto, `default`, `base`, `formula`, `in_total`). It is edited in Django admin (see the example in `quotes/admin.py`). The calculation itself runs client-side in `templates/quotes/calculator.html`; `quote_save` only persists the posted results.

### Online store (`store` app)

- `Category` has an optional `parent` (one level only, enforced in `CategoryForm`) and a unique `slug` generated from the name on first save. Subcategories inherit `tipo` from the parent (`Category.save()` also propagates it down). `str(category)` / `full_name` is `"Camisetas › Polo"`; use `Category.objects.tree()` to list parents followed by their children.
- `/tienda/<slug>/` shows a main category with its subcategories as tabs (`?sub=<slug>`) and sort (`?orden=recientes|precio-asc|precio-desc`), 24 per page. A subcategory slug redirects to its parent's tab.
- Each card has a "Comprar por WhatsApp" form (GET to `store_whatsapp_order`, `/tienda/pedido/<pk>/?talle=M`). If the product has sizes, the customer must pick one with stock (sold-out sizes render crossed out and disabled): JS shows an inline error, and the view re-checks it and redirects back to the store if it is missing, invalid or out of stock. Otherwise the view redirects to `wa.me/<settings.STORE_WHATSAPP>` with the order pre-written (description, chosen size, price, product code = PK, photo URL), built by `store.views.whatsapp_url`. An empty `STORE_WHATSAPP` hides the button and 404s the endpoint.
- A product is listed only if `is_active` and `quantity > 0`. Because stock only enters through Compras, a new product shows up in the store once a purchase is registered. The public price is `list_price`. Sales in the portal default to `distributor_price`, which the sales API fills in; `SaleItem.save()` falls back to `list_price` only when `unit_price` is empty.
- `Product.image` is an `ImageField` (`upload_to='productos/'`, needs Pillow). Uploads go to `MEDIA_ROOT = media/` (gitignored), which Django serves only while `DEBUG`; production needs the web server to serve `/media/`.
- The landing's Vestimenta card and the header nav link to `store_category 'camisetas'` (created by data migration `products/0008`, which renamed the old "Remeras" category).
- On PostgreSQL, adding a unique `SlugField` to an existing table must be done as nullable with `db_index=False`, then filled, then altered to unique (see `products/0007`); otherwise the `_like` index is created twice and the migration fails.

### PDF

The customer statement PDF (`customer_statement_pdf` in `sales/views.py`) is built inline with ReportLab platypus.

## Conventions

- Commit messages: `<Module>: <description in Spanish>`, e.g. `Sales: fila de totales ...`, `Compras/Ventas: ...`.
- Models use aligned `=` columns, Spanish verbose names, and `*_CHOICES` constants on the class. Section banners in views use `# ──────` comment blocks.
- Delete views never rely on catching `ProtectedError`. They check the protecting relations with `.exists()` (e.g. a customer's `sales`, a product's `saleitem_set`/`purchaseitem_set`, a supplier's `quotes`, a category's `products`/`children`). If a relation exists, the POST shows a `messages.error` and redirects to the list, and the confirm template shows a warning and hides the "Sí, eliminar" button. New delete views should do the same.
- `Category.tipo` drives conditional product fields: `CAL` (Calzado) requires `calce` (EU, with optional US/UK), and `VES` (Vestimenta) requires at least one of `talles`. `ProductForm.clean` blanks out the fields that don't apply to the category.
- Sizes are modeled differently per type. A shoe is one product per pair with a single `calce`. A clothing product is offered in several sizes: `ProductForm.talles` is a non-model checkbox field synced to `ProductSize` rows in `_save_m2m` (so views that use `commit=False` must call `form.save_m2m()`). A size with stock can't be unchecked. `Product.talles` is a read-only list of offered sizes (ordered XS→3XL via `ProductSize.position`). `SaleItem`/`PurchaseItem` have a `talle` that is required when the product has sizes; sales validate stock per size. The sale/purchase product APIs return `sizes: [{talle, stock}]` (sales only sizes with stock), and the forms' JS (`setRowSizes`) enables the row's Talle select only for those products.
