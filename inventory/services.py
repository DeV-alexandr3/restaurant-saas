from decimal import Decimal

from django.db import transaction

from .models import InventoryItem, ProductIngredient, StockMovement
from django.db.models import Q, Sum


@transaction.atomic
def process_order_stock(order, user=None):

    # Evita processar o mesmo pedido novamente
    if order.stock_processed:
        return []

    order_items = order.items.select_related(
        "product"
    ).all()

    # =========================
    # CALCULAR NECESSIDADES
    # =========================

    requirements = {}

    for order_item in order_items:

        if not order_item.product:
            continue

        ingredients = ProductIngredient.objects.filter(
            product=order_item.product
        ).select_related(
            "inventory_item"
        )

        for ingredient in ingredients:

            converted_quantity = convert_quantity(
                ingredient.quantity,
                ingredient.unit,
                ingredient.inventory_item.unit,
            )

            required_quantity = (
                converted_quantity
                * order_item.quantity
            )

            item_id = ingredient.inventory_item_id

            if item_id not in requirements:
                requirements[item_id] = Decimal("0")

            requirements[item_id] += required_quantity

    # =========================
    # TRAVAR E VALIDAR ESTOQUE
    # =========================

    inventory_items = {}

    for item_id, required_quantity in requirements.items():

        inventory_item = (
            InventoryItem.objects
            .select_for_update()
            .get(
                id=item_id,
                restaurant=order.restaurant,
            )
        )

        if inventory_item.quantity < required_quantity:
            raise ValueError(
                f"Estoque insuficiente de {inventory_item.name}. "
                f"Necessário: {required_quantity} "
                f"{inventory_item.get_unit_display()}. "
                f"Disponível: {inventory_item.quantity}."
            )

        inventory_items[item_id] = inventory_item

    # =========================
    # BAIXAR ESTOQUE
    # =========================

    low_stock_items = []

    for item_id, required_quantity in requirements.items():

        inventory_item = inventory_items[item_id]

        inventory_item.quantity -= required_quantity

        inventory_item.save(
            update_fields=["quantity"]
        )

        StockMovement.objects.create(
            item=inventory_item,
            movement_type="OUT",
            quantity=required_quantity,
            reason=f"Baixa automática - Pedido #{order.id}",
            user=user,
        )

        # Verifica estoque baixo depois da saída
        if (
            inventory_item.quantity
            <= inventory_item.minimum_quantity
        ):
            low_stock_items.append(
                inventory_item.name
            )

    # =========================
    # MARCAR PEDIDO PROCESSADO
    # =========================

    order.stock_processed = True

    order.save(
        update_fields=["stock_processed"]
    )

    return low_stock_items

def convert_quantity(quantity, from_unit, to_unit):

    quantity = Decimal(quantity)

    if from_unit == to_unit:
        return quantity

    conversions = {
        ("G", "KG"): Decimal("0.001"),
        ("KG", "G"): Decimal("1000"),
        ("ML", "L"): Decimal("0.001"),
        ("L", "ML"): Decimal("1000"),
    }

    factor = conversions.get(
        (from_unit, to_unit)
    )

    if factor is None:
        raise ValueError(
            f"Não é possível converter {from_unit} para {to_unit}."
        )

    return quantity * factor

def calculate_product_cost(product): 

    ingredients = ProductIngredient.objects.filter(
        product=product
    ).select_related(
        "inventory_item"
    )

    total_cost = Decimal("0")
    ingredient_costs = []
    has_missing_cost = False
    missing_cost_items = []

    for ingredient in ingredients:

        inventory_item = ingredient.inventory_item

        purchase_totals = StockMovement.objects.filter(
            item=inventory_item,
            movement_type="IN",
            total_cost__isnull=False,
            quantity__gt=0,
        ).filter(
            Q(purchase__isnull=True)
            | Q(purchase__status="ACTIVE")
        ).aggregate(
            total_quantity=Sum("quantity"),
            total_cost=Sum("total_cost"),
        )

        total_purchased_quantity = (
            purchase_totals["total_quantity"]
        )

        total_purchased_cost = (
            purchase_totals["total_cost"]
        )

        if (
            not total_purchased_quantity
            or total_purchased_cost is None
        ):
            has_missing_cost = True

            missing_cost_items.append(
                ingredient.inventory_item.name
            )

            ingredient_costs.append({
                "ingredient": ingredient,
                "unit_cost": None,
                "cost": None,
            })

            continue

        unit_cost = (
            total_purchased_cost
            / total_purchased_quantity
        )

        converted_quantity = convert_quantity(
            ingredient.quantity,
            ingredient.unit,
            inventory_item.unit,
        )

        ingredient_cost = (
            converted_quantity
            * unit_cost
        )

        total_cost += ingredient_cost

        ingredient_costs.append({
            "ingredient": ingredient,
            "unit_cost": unit_cost,
            "cost": ingredient_cost,
        })

    return {
        "ingredient": ingredient,
        "total_cost": total_cost,
        "ingredient_costs": ingredient_costs,
        "has_missing_cost": has_missing_cost,
        "missing_cost_items": missing_cost_items,
    }