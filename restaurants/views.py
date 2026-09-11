from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.http import JsonResponse
import io
import qrcode
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from inventory.services import process_order_stock
from django.contrib import messages
from django.db.models import F
from inventory.models import InventoryItem
from decimal import Decimal, InvalidOperation
from .models import RestaurantMember
from .models import Table
from catalog.models import Order, OrderItem
from .services import get_current_membership
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension
import re

User = get_user_model()

@login_required
def test_current_restaurant(request):
    membership = get_current_membership(request.user)

    if membership is None:
        return HttpResponse("Usuário não possui restaurante ativo.")

    return HttpResponse(
        f"""
        <h1>Teste Multi-Restaurante</h1>

        <p><strong>Usuário:</strong> {request.user.email}</p>
        <p><strong>Restaurante:</strong> {membership.restaurant.name}</p>
        <p><strong>Função:</strong> {membership.get_role_display()}</p>
        """
    )

@login_required
def order_list(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    new_orders_count = Order.objects.filter(
        restaurant=restaurant,
        status="NEW",
    ).count()

    status_filter = request.GET.get("status", "").strip()

    orders = Order.objects.filter(
        restaurant=restaurant
    )

    search = request.GET.get("search", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    period = request.GET.get("period", "").strip()

    if search:
        search_filter = (
            Q(customer_name__icontains=search)
            | Q(customer_phone__icontains=search)
        )

        if search.isdigit():
            search_filter |= Q(id=int(search))

        orders = orders.filter(search_filter)

    if date_from:
        orders = orders.filter(
            created_at__date__gte=date_from
        )

    if date_to:
        orders = orders.filter(
            created_at__date__lte=date_to
        )

    if period == "today":
        today = timezone.localdate()    
        orders = orders.filter(
            created_at__date=today
        )

    elif period == "7days":
        start_date = timezone.localdate() - timedelta(days=6)
        orders = orders.filter(
            created_at__date__gte=start_date
        )

    elif period == "30days":
        start_date = timezone.localdate() - timedelta(days=29)
        orders = orders.filter(
            created_at__date__gte=start_date
        )

    valid_statuses = {
        value for value, label in Order.STATUS_CHOICES
    }

    if (
        status_filter
        and status_filter in valid_statuses
    ):
        orders = orders.filter(
            status=status_filter
        )

    valid_orders = orders.exclude(
        status__in=["REJECTED", "CANCELLED"]
    )

    summary = orders.aggregate(
        total_orders=Count("id"),
    )

    sales_summary = valid_orders.aggregate(
        total_sales=Sum("total"),
        average_ticket=Avg("total"),
    )

    orders = orders.order_by("-created_at")

    paginator = Paginator(orders, 20)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)
   
    return render(
        request,
        "restaurants/order_list.html",
        {
            "restaurant": restaurant,
            "orders": page_obj,
            "page_obj": page_obj,
            "status_filter": status_filter,
            "status_choices": Order.STATUS_CHOICES,
            "new_orders_count": new_orders_count,
            "search": search,
            "date_from": date_from,
            "date_to": date_to,
            "period": period,
            "summary": summary,
            "sales_summary": sales_summary,
        },
    )

@login_required
def order_detail(request, order_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    order = get_object_or_404(
        Order.objects.prefetch_related("items__addons"),
        id=order_id,
        restaurant=restaurant,
    )

    return render(
        request,
        "restaurants/order_detail.html",
        {
            "restaurant": restaurant,
            "order": order,
        },
    )

@login_required
def order_update_status(request, order_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    if request.method != "POST":
        return redirect(
            "order_detail",
            order_id=order_id,
        )

    new_status = request.POST.get("status")

    if not new_status:
        messages.error(
            request,
            "Selecione um status válido.",
        )
        return redirect(
            "order_detail",
            order_id=order_id,
        )

    allowed_transitions = {
        "NEW": [
            "CONFIRMED",
            "REJECTED",
            "CANCELLED",
        ],
        "CONFIRMED": [
            "PREPARING",
            "CANCELLED",
        ],
        "PREPARING": [
            "READY",
            "CANCELLED",
        ],
        "READY": [
            "OUT_FOR_DELIVERY",
            "FINISHED",
            "CANCELLED",
        ],
        "OUT_FOR_DELIVERY": [
            "FINISHED",
        ],
        "FINISHED": [],
        "REJECTED": [],
        "CANCELLED": [],
    }

    try:
        with transaction.atomic():

            # Bloqueia o pedido durante a alteração.
            order = get_object_or_404(
                Order.objects.select_for_update(),
                id=order_id,
                restaurant=restaurant,
            )

            current_status = order.status

            allowed_next_statuses = allowed_transitions.get(
                current_status,
                [],
            ).copy()

            # Retirada e mesa não podem "sair para entrega".
            if (
                order.order_type != "delivery"
                and "OUT_FOR_DELIVERY" in allowed_next_statuses
            ):
                allowed_next_statuses.remove(
                    "OUT_FOR_DELIVERY"
                )

            if new_status not in allowed_next_statuses:
                messages.error(
                    request,
                    "Essa alteração de status não é permitida.",
                )
                return redirect(
                    "order_detail",
                    order_id=order.id,
                )

            low_stock_items = []

            # O estoque só é processado ao finalizar.
            if (
                new_status == "FINISHED"
                and not order.stock_processed
            ):
                low_stock_items = process_order_stock(
                    order,
                    user=request.user,
                )

            # Só altera o status depois do estoque dar certo.
            order.status = new_status
            order.save(
                update_fields=["status"]
            )

    except ValueError as error:
        messages.error(
            request,
            str(error),
        )
        return redirect(
            "order_detail",
            order_id=order_id,
        )

    if low_stock_items:
        messages.warning(
            request,
            "Estoque baixo: "
            + ", ".join(low_stock_items)
            + ".",
        )

    return redirect(
        "order_detail",
        order_id=order_id,
    )

@login_required
def new_orders_count(request):
    membership = get_current_membership(request.user)

    if not membership:
        return JsonResponse(
            {
                "error": "Usuário não possui restaurante ativo.",
                "count": 0,
                "latest_order_id": None,
            },
            status=403,
        )

    new_orders = Order.objects.filter(
        restaurant=membership.restaurant,
        status="NEW",
    )

    count = new_orders.count()

    latest_order = new_orders.order_by(
        "-created_at"
    ).first()

    return JsonResponse({
        "count": count,
        "latest_order_id": (
            latest_order.id
            if latest_order
            else None
        ),
    })

@login_required
def table_list(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    tables = Table.objects.filter(
        restaurant=restaurant
    ).order_by("number")

    return render(
        request,
        "restaurants/table_list.html",
        {
            "restaurant": restaurant,
            "tables": tables,
        },
    )

@login_required
def table_create(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("table_list")

    restaurant = membership.restaurant

    if request.method == "POST":
        number = request.POST.get("number")
        name = request.POST.get("name", "").strip()

        if Table.objects.filter(
            restaurant=restaurant,
            number=number,
        ).exists():
            return render(
                request,
                "restaurants/table_form.html",
                {
                    "restaurant": restaurant,
                    "error": (
                        f"A mesa {number} já existe "
                        f"neste restaurante."
                    ),
                },
            )

        Table.objects.create(
            restaurant=restaurant,
            number=number,
            name=name,
            is_active=True,
        )

        return redirect("table_list")

    return render(
        request,
        "restaurants/table_form.html",
        {
            "restaurant": restaurant,
        },
    )

@login_required 
def table_edit(request, table_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("table_list")

    restaurant = membership.restaurant

    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant,
    )

    if request.method == "POST":
        number = request.POST.get("number")
        name = request.POST.get("name", "").strip()

        if Table.objects.filter(
            restaurant=restaurant,
            number=number,
        ).exclude(
            id=table.id
        ).exists():

            return render(
                request,
                "restaurants/table_form.html",
                {
                    "restaurant": restaurant,
                    "table": table,
                    "error": (
                        f"A mesa {number} já existe "
                        f"neste restaurante."
                    ),
                },
            )

        table.number = number
        table.name = name

        table.save()

        return redirect("table_list")

    return render(
        request,
        "restaurants/table_form.html",
        {
            "restaurant": restaurant,
            "table": table,
        },
    )

@login_required
def table_toggle_status(request, table_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("table_list")

    restaurant = membership.restaurant

    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant,
    )

    if request.method == "POST":
        table.is_active = not table.is_active
        table.save(update_fields=["is_active"])

    return redirect("table_list")

@login_required
def table_qr_code(request, table_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant,
        is_active=True,
    )

    table_url = request.build_absolute_uri(
        f"/r/{restaurant.slug}/mesa/{table.number}/"
    )

    qr = qrcode.make(table_url)

    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")

    buffer.seek(0)

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

@login_required
def table_qr_page(request, table_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    table = get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant,
    )

    table_url = request.build_absolute_uri(
        f"/r/{restaurant.slug}/mesa/{table.number}/"
    )

    return render(
        request,
        "restaurants/table_qr_page.html",
        {
            "restaurant": restaurant,
            "table": table,
            "table_url": table_url,
        },
    )

@login_required
def employee_list(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("order_list")

    restaurant = membership.restaurant

    employees = RestaurantMember.objects.filter(
        restaurant=restaurant,
    ).select_related("user").order_by("user__email")

    return render(
        request,
        "restaurants/employee_list.html",
        {
            "restaurant": restaurant,
            "employees": employees,
        },
    )

@login_required
def employee_create(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("order_list")

    restaurant = membership.restaurant

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role")

        if role not in ["ADMIN", "EMPLOYEE"]:
            role = "EMPLOYEE"

        if not email:
            return render(
                request,
                "restaurants/employee_form.html",
                {
                    "restaurant": restaurant,
                    "error": "Informe o e-mail do funcionário.",
                },
            )

        if not password:
            return render(
                request,
                "restaurants/employee_form.html",
                {
                    "restaurant": restaurant,
                    "error": "Informe uma senha.",
                },
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():
            return render(
                request,
                "restaurants/employee_form.html",
                {
                    "restaurant": restaurant,
                    "error": "Já existe um usuário com esse e-mail.",
                },
            )

        with transaction.atomic():

            user = User.objects.create_user(
                email=email,
                password=password,
            )

            RestaurantMember.objects.create(
                user=user,
                restaurant=restaurant,
                role=role,
                is_active=True,
            )

        return redirect("employee_list")

    return render(
        request,
        "restaurants/employee_form.html",
        {
            "restaurant": restaurant,
        },
    )

def logout_view(request):
    logout(request)

    return redirect("login")

def login_view(request):
    if request.user.is_authenticated:
        return redirect("order_list")

    error = None

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            email=email,
            password=password,
        )

        if user is not None:
            membership = get_current_membership(user)

            if membership:
                login(request, user)

                return redirect("order_list")

            error = "Este usuário não está vinculado a nenhum restaurante."

        else:
            error = "E-mail ou senha inválidos."

    return render(
        request,
        "restaurants/login.html",
        {
            "error": error,
        },
    )

@login_required
def employee_edit(request, member_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("order_list")

    restaurant = membership.restaurant

    employee = get_object_or_404(
        RestaurantMember,
        id=member_id,
        restaurant=restaurant,
    )

    if request.method == "POST":
        role = request.POST.get("role")

        if role not in ["ADMIN", "EMPLOYEE"]:
            role = "EMPLOYEE"

        # Evita o admin remover o próprio acesso administrativo
        if employee.user == request.user and role != "ADMIN":
            return redirect(
                "employee_list"
            )

        employee.role = role
        employee.save(update_fields=["role"])

        return redirect("employee_list")

    return render(
        request,
        "restaurants/employee_edit.html",
        {
            "restaurant": restaurant,
            "employee": employee,
        },
    )

@login_required
def employee_toggle_status(request, member_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("order_list")

    restaurant = membership.restaurant

    employee = get_object_or_404(
        RestaurantMember,
        id=member_id,
        restaurant=restaurant,
    )

    if request.method == "POST":

        # Não deixa o admin desativar a própria conta
        if employee.user == request.user:
            messages.error(
                request,
                "Você não pode desativar a própria conta.",
            )
            return redirect("employee_list")
    
        employee.is_active = not employee.is_active

        employee.save(
            update_fields=["is_active"]
        )

    return redirect("employee_list")

@login_required
def restaurant_settings(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("order_list")

    restaurant = membership.restaurant

    if request.method == "POST":
        restaurant.name = request.POST.get("name", "").strip()
        restaurant.phone = request.POST.get("phone", "").strip()
        minimum_order_value = request.POST.get("minimum_order", "0")
        delivery_fee_value = request.POST.get("delivery_fee", "0")
        estimated_time_value = request.POST.get("estimated_time_minutes", "30")

        restaurant.accepts_pickup = (
            request.POST.get("accepts_pickup") == "on"
        )

        restaurant.accepts_delivery = (
            request.POST.get("accepts_delivery") == "on"
        )

        restaurant.accepts_table_orders = (
            request.POST.get("accepts_table_orders") == "on"
        )

        try:
            minimum_order = Decimal(
                minimum_order_value or "0"
            )

            delivery_fee = Decimal(
                delivery_fee_value or "0"
            )

            estimated_time_minutes = int(
                estimated_time_value or 30
            )

        except (InvalidOperation, ValueError):
            return render(
                request,
                "restaurants/restaurant_settings.html",
                {
                    "restaurant": restaurant,
                    "error": "Confira os valores informados.",
                },
            )

        if minimum_order < 0 or delivery_fee < 0:
            return render(
                request,
                "restaurants/restaurant_settings.html",
                {
                    "restaurant": restaurant,
                    "error": (
                        "Pedido mínimo e taxa de entrega "
                        "não podem ser negativos."
                    ),
                },
            )

        if estimated_time_minutes <= 0:
            return render(
                request,
                "restaurants/restaurant_settings.html",
                {
                    "restaurant": restaurant,
                    "error": (
                        "O tempo estimado deve ser maior que zero."
                    ),
                },
            )

        restaurant.minimum_order = minimum_order
        restaurant.delivery_fee = delivery_fee
        restaurant.estimated_time_minutes = (
            estimated_time_minutes
        )


        primary_color = request.POST.get(
            "primary_color",
            "#111827",
        )

        background_color = request.POST.get(
            "background_color",
            "#f6f7f9",
        )

        color_pattern = r"^#[0-9A-Fa-f]{6}$"

        if not re.match(color_pattern, primary_color):
            return render(
                request,
                "restaurants/restaurant_settings.html",
                {
                    "restaurant": restaurant,
                    "error": "A cor principal informada é inválida.",
                },
            )

        if not re.match(color_pattern, background_color):
            return render(
                request,
                "restaurants/restaurant_settings.html",
                {
                    "restaurant": restaurant,
                    "error": "A cor de fundo informada é inválida.",
                },
            )

        restaurant.primary_color = primary_color
        restaurant.background_color = background_color

        logo = request.FILES.get("logo")
        banner = request.FILES.get("banner")

        for image, label in [
            (logo, "logo"),
            (banner, "banner"),
        ]:
            if image:
                try:
                    validate_image_file_extension(image)
                except ValidationError:
                    return render(
                        request,
                        "restaurants/restaurant_settings.html",
                        {
                            "restaurant": restaurant,
                            "error": f"O arquivo enviado para {label} não é uma imagem válida.",
                        },
                    )

                if image.size > 5 * 1024 * 1024:
                    return render(
                        request,
                        "restaurants/restaurant_settings.html",
                        {
                            "restaurant": restaurant,
                            "error": f"A imagem de {label} deve ter no máximo 5 MB.",
                        },
                    )

        remove_logo = request.POST.get("remove_logo")
        remove_banner = request.POST.get("remove_banner")

        if remove_logo:
            restaurant.logo = None
        elif logo:
            restaurant.logo = logo

        if remove_banner:
            restaurant.banner = None
        elif banner:
            restaurant.banner = banner

        restaurant.save()

        return redirect("restaurant_settings")

    return render(
        request,
        "restaurants/restaurant_settings.html",
        {
            "restaurant": restaurant,
        },
    )

@login_required
def dashboard(request):

    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    restaurant = membership.restaurant

    today = timezone.localdate()

    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today,
    )

    valid_today_orders = today_orders.exclude(
        status__in=["REJECTED", "CANCELLED"]
    )

    dashboard_summary = valid_today_orders.aggregate(
        total_sales=Sum("total"),
        average_ticket=Avg("total"),
    )

    today_orders_count = today_orders.count()

    new_orders_count = today_orders.filter(
        status="NEW"
    ).count()

    recent_orders = Order.objects.filter(
        restaurant=restaurant
    ).order_by("-created_at")[:5]

    sales_labels = []
    sales_values = []

    for days_ago in range(6, -1, -1):

        day = timezone.localdate() - timedelta(days=days_ago)

        day_sales = Order.objects.filter(
            restaurant=restaurant,
            created_at__date=day,
        ).exclude(
            status__in=["REJECTED", "CANCELLED"]
        ).aggregate(
            total=Sum("total")
        )["total"] or 0

        sales_labels.append(
            day.strftime("%d/%m")
        )

        sales_values.append(
            float(day_sales)
        )

    status_labels = [
        "Novo",
        "Confirmado",
        "Em preparo",
        "Pronto",
        "Saiu para entrega",
        "Finalizado",
        "Recusado",
        "Cancelado",
    ]

    status_counts = {
        item["status"]: item["count"]
        for item in (
            Order.objects.filter(
                restaurant=restaurant
            )
            .values("status")
            .annotate(
                count=Count("id")
            )
        )
    }

    status_values = [
        status_counts.get("NEW", 0),
        status_counts.get("CONFIRMED", 0),
        status_counts.get("PREPARING", 0),
        status_counts.get("READY", 0),
        status_counts.get("OUT_FOR_DELIVERY", 0),
        status_counts.get("FINISHED", 0),
        status_counts.get("REJECTED", 0),
        status_counts.get("CANCELLED", 0),
    ]

    products_period = request.GET.get(
        "products_period",
        "7days"
    )

    products_start_date = None

    if products_period == "today":
        products_start_date = timezone.localdate()

    elif products_period == "7days":
        products_start_date = (
            timezone.localdate()
            - timedelta(days=6)
        )

    elif products_period == "30days":
        products_start_date = (
            timezone.localdate()
            - timedelta(days=29)
        )

    top_products_query = OrderItem.objects.filter(
        order__restaurant=restaurant
    ).exclude(
        order__status__in=[
            "REJECTED",
            "CANCELLED",
        ]
    )

    if products_start_date:
        top_products_query = top_products_query.filter(
            order__created_at__date__gte=products_start_date
        )

    top_products = (
        top_products_query
        .values("product_name")
        .annotate(
            total_quantity=Sum("quantity")
        )
        .order_by("-total_quantity")[:5]
    )

    top_product_labels = [
        item["product_name"]
        for item in top_products
    ]

    top_product_values = [
        item["total_quantity"]
        for item in top_products
    ]

    order_type_labels = [
        "Entrega",
        "Retirada",
        "Mesa",
    ]

    order_type_counts = {
        item["order_type"]: item["count"]
        for item in (
            Order.objects.filter(
                restaurant=restaurant
            )
            .values("order_type")
            .annotate(
                count=Count("id")
            )
        )
    }

    order_type_values = [
        order_type_counts.get("delivery", 0),
        order_type_counts.get("pickup", 0),
        order_type_counts.get("table", 0),
    ]

    low_stock_items = InventoryItem.objects.filter(
        restaurant=restaurant,
        is_active=True,
        quantity__lte=F("minimum_quantity"),
    ).order_by("quantity")

    return render(
        request,
        "restaurants/dashboard.html",
        {
            "today_orders_count": today_orders_count,
            "today_total_sales": dashboard_summary["total_sales"] or 0,
            "today_average_ticket": dashboard_summary["average_ticket"] or 0,
            "today_new_orders_count": new_orders_count,
            "recent_orders": recent_orders,
            "sales_labels": sales_labels,
            "sales_values": sales_values,
            "status_labels": status_labels,
            "status_values": status_values,
            "top_product_labels": top_product_labels,
            "top_product_values": top_product_values,
            "products_period": products_period,
            "order_type_labels": order_type_labels,
            "order_type_values": order_type_values,
            "low_stock_items": low_stock_items,
            "low_stock_count": low_stock_items.count(),
        },
    )
