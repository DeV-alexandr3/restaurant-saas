from django.urls import path

from . import views


urlpatterns = [
    path(
        "teste-restaurante/",
        views.test_current_restaurant,
        name="test_current_restaurant",
    ),

    path(
        "pedidos/",
        views.order_list,
        name="order_list",
    ),

    path(
        "pedidos/<int:order_id>/",
        views.order_detail,
        name="order_detail",
    ),

    path(
        "pedidos/<int:order_id>/status/",
        views.order_update_status,
        name="order_update_status",
    ),

    path(
        "pedidos/novos/contador/",
        views.new_orders_count,
        name="new_orders_count",
    ),

    path(
        "mesas/",
        views.table_list,
        name="table_list",
    ),

    path(
        "mesas/nova/",
        views.table_create,
        name="table_create",
    ),

    path(
        "mesas/<int:table_id>/editar/",
        views.table_edit,
        name="table_edit",
    ),

    path(
        "mesas/<int:table_id>/status/",
        views.table_toggle_status,
        name="table_toggle_status",
    ),

    path(
        "mesas/<int:table_id>/qr/",
        views.table_qr_code,
        name="table_qr_code",
    ),

    path(
        "mesas/<int:table_id>/qr/pagina/",
        views.table_qr_page,
        name="table_qr_page",
    ),

    path(
        "funcionarios/",
        views.employee_list,
        name="employee_list",
    ),

    path(
        "funcionarios/novo/",
        views.employee_create,
        name="employee_create",
    ),

    path(
        "sair/",
        views.logout_view,
        name="logout",
    ),

    path(
        "entrar/",
        views.login_view,
        name="login",
    ),

    path(
        "funcionarios/<int:member_id>/editar/",
        views.employee_edit,
        name="employee_edit",
    ),

    path(
        "funcionarios/<int:member_id>/status/",
        views.employee_toggle_status,
        name="employee_toggle_status",
    ),

    path(
        "configuracoes/",
        views.restaurant_settings,
        name="restaurant_settings",
    ),

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

]