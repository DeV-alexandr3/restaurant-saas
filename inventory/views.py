from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404

from restaurants.models import RestaurantMember
from .models import InventoryItem, ProductIngredient, StockMovement, Purchase, PurchaseItem
from decimal import Decimal, InvalidOperation
from django.db import models
from django.db import transaction
from catalog.models import Product
from django.core.paginator import Paginator
from .services import calculate_product_cost
from django.contrib import messages
from django.utils import timezone


def is_compatible_unit(stock_unit, recipe_unit):

    compatible_units = {
        "KG": ["KG", "G"],
        "G": ["G", "KG"],

        "L": ["L", "ML"],
        "ML": ["ML", "L"],

        "UN": ["UN"],
    }

    return recipe_unit in compatible_units.get(
        stock_unit,
        []
    )

@login_required
def inventory_list(request):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    items = InventoryItem.objects.filter(
        restaurant=restaurant
    )

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if search:
        items = items.filter(
            name__icontains=search
        )

    if status_filter == "low":
        items = items.filter(
            quantity__lte=models.F("minimum_quantity"),
            is_active=True,
        )

    elif status_filter == "active":
        items = items.filter(
            is_active=True
        )

    elif status_filter == "inactive":
        items = items.filter(
            is_active=False
        )

    total_inventory_value = 0
    
    for item in items:
        value = item.stock_value()

        if value is not None:
            total_inventory_value += value

    paginator = Paginator(items, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_items = items.count()

    low_stock_count = items.filter(
        quantity__lte=models.F("minimum_quantity"),
        is_active=True,
    ).count()

    inactive_count = items.filter(
        is_active=False
    ).count()

    low_stock_items = InventoryItem.objects.filter(
        restaurant=restaurant,
        is_active=True,
        quantity__lte=models.F("minimum_quantity"),
    ).order_by("quantity")

    return render(
        request,
        "inventory/inventory_list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "membership": membership,
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "inactive_count": inactive_count,
            "search": search,
            "status_filter": status_filter,
            "low_stock_items": low_stock_items,
            "total_inventory_value": total_inventory_value,
        },
    )

@login_required 
def inventory_create(request):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("inventory_list")

    restaurant = membership.restaurant

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        unit = request.POST.get("unit", "UN")
        quantity = request.POST.get("quantity", "0")
        minimum_quantity = request.POST.get("minimum_quantity", "0")

        try:
            quantity = Decimal(quantity)
            minimum_quantity = Decimal(minimum_quantity)
        except InvalidOperation:
            return render(
                request,
                "inventory/inventory_form.html",
                {
                    "error": "Quantidade inválida."
                },
            )

        InventoryItem.objects.create(
            restaurant=restaurant,
            name=name,
            unit=unit,
            quantity=quantity,
            minimum_quantity=minimum_quantity,
        )

        return redirect("inventory_list")

    return render(
        request,
        "inventory/inventory_form.html",
    )

@login_required
def inventory_edit(request, item_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("inventory_list")

    restaurant = membership.restaurant

    item = get_object_or_404(
        InventoryItem,
        id=item_id,
        restaurant=restaurant,
    )

    if request.method == "POST":
        item.name = request.POST.get("name", "").strip()
        item.unit = request.POST.get("unit", "UN")
        quantity_value = request.POST.get(
            "quantity",
            "0"
        )

        minimum_quantity_value = request.POST.get(
            "minimum_quantity",
            "0"
        )

        try:
            quantity = Decimal(quantity_value)
            minimum_quantity = Decimal(
                minimum_quantity_value
            )

        except InvalidOperation:
            return render(
                request,
                "inventory/inventory_edit.html",
                {
                    "item": item,
                    "error": "Quantidade inválida.",
                },
            )

        item.quantity = quantity
        item.minimum_quantity = minimum_quantity

        item.save()

        return redirect("inventory_list")

    return render(
        request,
        "inventory/inventory_edit.html",
        {
            "item": item,
        },
    )

@login_required
def inventory_toggle_status(request, item_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("inventory_list")

    item = get_object_or_404(
        InventoryItem,
        id=item_id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        item.is_active = not item.is_active
        item.save(update_fields=["is_active"])

    return redirect("inventory_list")

@login_required
def stock_movement_create(request, item_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("inventory_list")

    item = get_object_or_404(
        InventoryItem,
        id=item_id,
        restaurant=membership.restaurant,
    )

    error = None

    if request.method == "POST":

        movement_type = request.POST.get(
            "movement_type"
        )

        quantity_value = request.POST.get(
            "quantity",
            "0"
        )

        reason = request.POST.get(
            "reason",
            ""
        ).strip()

        supplier = request.POST.get(
            "supplier",
            ""
        ).strip()

        total_cost_value = request.POST.get(
            "total_cost",
            ""
        )

        try:
            quantity = Decimal(quantity_value)

        except InvalidOperation:
            quantity = None
            error = "Digite uma quantidade válida."

        if quantity is not None:

            if movement_type in ["IN", "OUT"] and quantity <= 0:
                error = "A quantidade deve ser maior que zero."

            elif movement_type == "ADJUST" and quantity < 0:
                error = "O estoque não pode ficar negativo."

            elif movement_type not in ["IN", "OUT", "ADJUST"]:
                error = "Tipo de movimentação inválido."

        total_cost = None

        if movement_type == "IN" and total_cost_value:
            try:
                total_cost = Decimal(total_cost_value)
            except InvalidOperation:
                error = "Informe um valor de compra válido."

            if total_cost is not None and total_cost < 0:
                error = "O valor da compra não pode ser negativo."

        if not error:

            with transaction.atomic():

                locked_item = InventoryItem.objects.select_for_update().get(
                    id=item.id,
                    restaurant=membership.restaurant,
                )

                if movement_type == "IN":

                    locked_item.quantity += quantity

                elif movement_type == "OUT":

                    if quantity > locked_item.quantity:
                        error = "A saída é maior que o estoque disponível."

                    else:
                        locked_item.quantity -= quantity

                elif movement_type == "ADJUST":

                    locked_item.quantity = quantity

                if not error:

                    locked_item.save(
                        update_fields=["quantity"]
                    )

                    StockMovement.objects.create(
                        item=locked_item,
                        movement_type=movement_type,
                        quantity=quantity,
                        reason=reason,
                        supplier=supplier if movement_type == "IN" else "",
                        total_cost=total_cost if movement_type == "IN" else None,
                        user=request.user,
                    )

                    return redirect(
                        "inventory_list"
                    )

    return render(
        request,
        "inventory/stock_movement_form.html",
        {
            "item": item,
            "error": error,
        },
    )

@login_required
def stock_movement_list(request):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("inventory_list")

    movements = StockMovement.objects.filter(
        item__restaurant=membership.restaurant
    ).select_related(
        "item",
        "user"
    ).order_by("-created_at")

    search = request.GET.get("search", "").strip()
    movement_type = request.GET.get("type", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if search:
        movements = movements.filter(
            models.Q(item__name__icontains=search)
            | models.Q(reason__icontains=search)
            | models.Q(user__email__icontains=search)
        )

    if movement_type in ["IN", "OUT", "ADJUST"]:
        movements = movements.filter(
            movement_type=movement_type
        )

    if date_from:
        movements = movements.filter(
            created_at__date__gte=date_from
        )

    if date_to:
        movements = movements.filter(
            created_at__date__lte=date_to
        )

    paginator = Paginator(
        movements,
        20
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "inventory/stock_movement_list.html",
        {
            "movements": page_obj,
            "page_obj": page_obj,

            "search": search,
            "movement_type": movement_type,

            "date_from": date_from,
            "date_to": date_to,
        },
    )

@login_required
def product_recipe(request, product_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    restaurant = membership.restaurant

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=restaurant,
    )

    ingredients = ProductIngredient.objects.filter(
        product=product
    ).select_related("inventory_item")

    inventory_items = InventoryItem.objects.filter(
        restaurant=restaurant,
        is_active=True
    )

    if request.method == "POST":

        inventory_item_id = request.POST.get(
            "inventory_item"
        )

        quantity_value = request.POST.get(
            "quantity",
            ""
        )

        unit = request.POST.get(
            "unit",
            "UN"
        )

        inventory_item = get_object_or_404(
            InventoryItem,
            id=inventory_item_id,
            restaurant=restaurant,
            is_active=True,
        )

        try:
            quantity = Decimal(quantity_value)
        except InvalidOperation:
            quantity = None

        if quantity is None or quantity <= 0:
            return render(
                request,
                "inventory/product_recipe.html",
                {
                    "product": product,
                    "ingredients": ingredients,
                    "inventory_items": inventory_items,
                    "error": "Informe uma quantidade maior que zero.",
                },
            )

        if not is_compatible_unit(
                inventory_item.unit,
                unit,
            ):
                return render(
                    request,
                    "inventory/product_recipe.html",
                    {
                        "product": product,
                        "ingredients": ingredients,
                        "inventory_items": inventory_items,
                        "error": (
                            "A unidade escolhida não é compatível "
                            "com a unidade do item de estoque."
                        ),
                    },
                )   

        ProductIngredient.objects.update_or_create(
            product=product,
            inventory_item=inventory_item,
            defaults={
                "quantity": quantity,
                "unit": unit,
            },
        )

        return redirect(
            "product_recipe",
            product_id=product.id,
        )

    cost_data = calculate_product_cost(
        product
    )

    estimated_cost = cost_data["total_cost"]

    has_missing_cost = cost_data["has_missing_cost"]

    gross_margin = (
        product.price - estimated_cost
    )

    missing_cost_items = cost_data["missing_cost_items"]

    if has_missing_cost:
        gross_margin = None
        gross_margin_percentage = None
    else:
        gross_margin = product.price - estimated_cost

        if product.price > 0:
            gross_margin_percentage = (
                gross_margin / product.price
            ) * 100
        else:
            gross_margin_percentage = 0

    return render(
        request,
        "inventory/product_recipe.html",
        {
            "product": product,
            "ingredients": ingredients,
            "inventory_items": inventory_items,
            "estimated_cost": estimated_cost,
            "gross_margin": gross_margin,
            "ingredient_costs": cost_data["ingredient_costs"],
            "gross_margin_percentage": gross_margin_percentage,
            "has_missing_cost": has_missing_cost,
            "missing_cost_items": missing_cost_items,
        },
    )

@login_required
def product_recipe_remove(request, ingredient_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    ingredient = get_object_or_404(
        ProductIngredient,
        id=ingredient_id,
        product__restaurant=membership.restaurant,
    )

    product_id = ingredient.product.id

    if request.method == "POST":
        ingredient.delete()

    return redirect(
        "product_recipe",
        product_id=product_id,
    )

@login_required
def product_recipe_edit(request, ingredient_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    ingredient = get_object_or_404(
        ProductIngredient,
        id=ingredient_id,
        product__restaurant=membership.restaurant,
    )

    if request.method == "POST":

        quantity_value = request.POST.get(
            "quantity",
            ""
        )

        unit = request.POST.get(
            "unit",
            ingredient.unit,
        )

        try:
            quantity = Decimal(quantity_value)
        except InvalidOperation:
            quantity = None

        if quantity is None or quantity <= 0:
            return render(
                request,
                "inventory/product_recipe_edit.html",
                {
                    "ingredient": ingredient,
                    "error": "Informe uma quantidade maior que zero.",
                },
            )

        valid_units = [
            "UN",
            "KG",
            "G",
            "L",
            "ML",
        ]

        if unit not in valid_units:
            return render(
                request,
                "inventory/product_recipe_edit.html",
                {
                    "ingredient": ingredient,
                    "error": "Unidade inválida.",
                },
            )

        if not is_compatible_unit(
            ingredient.inventory_item.unit,
            unit,
        ):
            return render(
                request,
                "inventory/product_recipe_edit.html",
                {
                    "ingredient": ingredient,
                    "error": (
                        "A unidade escolhida não é compatível "
                        "com a unidade do item de estoque."
                    ),
                },
            )

        ingredient.quantity = quantity
        ingredient.unit = unit

        ingredient.save(
            update_fields=[
                "quantity",
                "unit",
            ]
        )

        return redirect(
            "product_recipe",
            product_id=ingredient.product.id,
        )

    return render(
        request,
        "inventory/product_recipe_edit.html",
        {
            "ingredient": ingredient,
        },
    )

@login_required
def purchase_list(request):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True,
    ).first()

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    purchases = Purchase.objects.filter(
        restaurant=restaurant
    ).select_related(
        "created_by"
    )

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if search:
        purchases = purchases.filter(
            supplier__icontains=search
        )

    if status:
        purchases = purchases.filter(
            status=status
        )

    if date_from:
        purchases = purchases.filter(
            purchase_date__gte=date_from
        )

    if date_to:
        purchases = purchases.filter(
            purchase_date__lte=date_to
        )

    return render(
        request,
        "inventory/purchase_list.html",
        {
            "purchases": purchases,
            "search": search,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )

@login_required
def purchase_create(request):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True,
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("purchase_list")

    restaurant = membership.restaurant

    inventory_items = InventoryItem.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).order_by("name")

    if request.method == "POST":

        supplier = request.POST.get(
            "supplier",
            ""
        ).strip()

        purchase_date = request.POST.get(
            "purchase_date"
        )

        item_ids = request.POST.getlist(
            "inventory_item"
        )

        quantities = request.POST.getlist(
            "quantity"
        )

        unit_prices = request.POST.getlist(
            "unit_price"
        )

        purchase_rows = []

        total_purchase = Decimal("0")

        for item_id, quantity_value, unit_price_value in zip(
            item_ids,
            quantities,
            unit_prices,
        ):

            if not item_id:
                continue

            try:
                quantity = Decimal(quantity_value)
                unit_price = Decimal(unit_price_value)

            except InvalidOperation:
                continue

            if quantity <= 0 or unit_price < 0:
                continue

            inventory_item = get_object_or_404(
                InventoryItem,
                id=item_id,
                restaurant=restaurant,
                is_active=True,
            )

            item_total = quantity * unit_price

            total_purchase += item_total

            purchase_rows.append({
                "inventory_item": inventory_item,
                "quantity": quantity,
                "unit_price": unit_price,
                "total": item_total,
            })

        if not purchase_rows:
            return render(
                request,
                "inventory/purchase_create.html",
                {
                    "inventory_items": inventory_items,
                    "error": "Adicione pelo menos um item válido.",
                },
            )

        with transaction.atomic():

            purchase = Purchase.objects.create(
                restaurant=restaurant,
                supplier=supplier,
                purchase_date=purchase_date,
                total=total_purchase,
                created_by=request.user,
            )

            for row in purchase_rows:

                inventory_item = (
                    InventoryItem.objects
                    .select_for_update()
                    .get(
                        id=row["inventory_item"].id,
                        restaurant=restaurant,
                    )
                )

                PurchaseItem.objects.create(
                    purchase=purchase,
                    inventory_item=inventory_item,
                    quantity=row["quantity"],
                    unit_price=row["unit_price"],
                    total=row["total"],
                )

                inventory_item.quantity += row["quantity"]

                inventory_item.save(
                    update_fields=["quantity"]
                )

                StockMovement.objects.create(
                    item=inventory_item,
                    movement_type="IN",
                    quantity=row["quantity"],
                    reason=f"Compra #{purchase.id}",
                    user=request.user,
                    supplier=supplier,
                    total_cost=row["total"],
                    purchase=purchase,
                )

        return redirect("purchase_list")

    return render(
        request,
        "inventory/purchase_create.html",
        {
            "inventory_items": inventory_items,
        },
    )

@login_required
def purchase_detail(request, purchase_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True,
    ).first()

    if not membership:
        return redirect("login")

    purchase = get_object_or_404(
        Purchase.objects.select_related(
            "created_by",
            "restaurant",
        ),
        id=purchase_id,
        restaurant=membership.restaurant,
    )

    purchase_items = PurchaseItem.objects.filter(
        purchase=purchase
    ).select_related(
        "inventory_item"
    )

    return render(
        request,
        "inventory/purchase_detail.html",
        {
            "purchase": purchase,
            "purchase_items": purchase_items,
        },
    )

@login_required
def purchase_cancel(request, purchase_id):

    membership = RestaurantMember.objects.filter(
        user=request.user,
        is_active=True,
    ).first()

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("purchase_list")

    purchase = get_object_or_404(
        Purchase,
        id=purchase_id,
        restaurant=membership.restaurant,
    )

    if request.method != "POST":
        return redirect(
            "purchase_detail",
            purchase_id=purchase.id,
        )

    if purchase.status == "CANCELLED":
        messages.error(
            request,
            "Essa compra já foi cancelada."
        )

        return redirect(
            "purchase_detail",
            purchase_id=purchase.id,
        )

    purchase_items = PurchaseItem.objects.filter(
        purchase=purchase
    ).select_related(
        "inventory_item"
    )

    with transaction.atomic():

        locked_items = []

        for purchase_item in purchase_items:

            inventory_item = (
                InventoryItem.objects
                .select_for_update()
                .get(
                    id=purchase_item.inventory_item_id,
                    restaurant=membership.restaurant,
                )
            )

            if inventory_item.quantity < purchase_item.quantity:
                messages.error(
                    request,
                    (
                        f"Não é possível cancelar a compra. "
                        f"O estoque de {inventory_item.name} "
                        f"é menor que a quantidade que entrou "
                        f"nessa compra."
                    ),
                )

                return redirect(
                    "purchase_detail",
                    purchase_id=purchase.id,
                )

            locked_items.append(
                (inventory_item, purchase_item)
            )

        for inventory_item, purchase_item in locked_items:

            inventory_item.quantity -= (
                purchase_item.quantity
            )

            inventory_item.save(
                update_fields=["quantity"]
            )

            StockMovement.objects.create(
                item=inventory_item,
                movement_type="OUT",
                quantity=purchase_item.quantity,
                reason=(
                    f"Estorno da Compra #{purchase.id}"
                ),
                user=request.user,
            )

        purchase.status = "CANCELLED"
        purchase.cancelled_at = timezone.now()
        purchase.cancelled_by = request.user

        purchase.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
            ]
        )

    messages.success(
        request,
        f"Compra #{purchase.id} cancelada com sucesso."
    )

    return redirect(
        "purchase_detail",
        purchase_id=purchase.id,
    )