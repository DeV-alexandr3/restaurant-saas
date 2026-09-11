from catalog.models import Order
from .services import get_current_membership


def restaurant_panel_data(request):
    if not request.user.is_authenticated:
        return {}

    membership = get_current_membership(request.user)

    if not membership:
        return {}

    new_orders_count = Order.objects.filter(
        restaurant=membership.restaurant,
        status="NEW",
    ).count()

    return {
        "new_orders_count": new_orders_count,
        "membership": membership,
    }