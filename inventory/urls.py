from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.inventory_list,
        name="inventory_list",
    ),

    path(
        "novo/",
        views.inventory_create,
        name="inventory_create",
    ),

    path(
        "<int:item_id>/editar/",
        views.inventory_edit,
        name="inventory_edit",
    ),

    path(
        "<int:item_id>/status/",
        views.inventory_toggle_status,
        name="inventory_toggle_status",
    ),

    path(
        "<int:item_id>/movimentar/",
        views.stock_movement_create,
        name="stock_movement_create",
    ),

    path(
        "movimentacoes/",
        views.stock_movement_list,
        name="stock_movement_list",
    ),

    path(
        "produto/<int:product_id>/ficha-tecnica/",
        views.product_recipe,
        name="product_recipe",
    ),

    path(
        "ficha-tecnica/ingrediente/<int:ingredient_id>/remover/",
        views.product_recipe_remove,
        name="product_recipe_remove",
    ),

    path(
        "ficha-tecnica/ingrediente/<int:ingredient_id>/editar/",
        views.product_recipe_edit,
        name="product_recipe_edit",
    ),

    path(
        "compras/",
        views.purchase_list,
        name="purchase_list",
    ),

    path(
        "compras/nova/",
        views.purchase_create,
        name="purchase_create",
    ),

    path(
        "compras/<int:purchase_id>/",
        views.purchase_detail,
        name="purchase_detail",
    ),

    path(
        "compras/<int:purchase_id>/cancelar/",
        views.purchase_cancel,
        name="purchase_cancel",
    ),
]