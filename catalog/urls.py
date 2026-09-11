from django.urls import path

from . import views


urlpatterns = [
    path(
        "categorias/",
        views.category_list,
        name="category_list",
    ),

    path(
        "categorias/nova/",
        views.category_create,
        name="category_create",
    ),

    path(
    "categorias/<int:id>/editar/",
    views.category_edit,
    name="category_edit",
    ),

    path(
    "categorias/<int:id>/excluir/",
    views.category_delete,
    name="category_delete",
    ),

    path(
    "produtos/",
    views.product_list,
    name="product_list",
    ),

    path(
    "produtos/novo/",
    views.product_create,
    name="product_create",
    ),

    path(
    "produtos/<int:id>/editar/",
    views.product_edit,
    name="product_edit",    
    ),

    path(
    "produtos/<int:id>/excluir/",
    views.product_delete,
    name="product_delete",
    ),

    path(
    "produtos/<int:id>/variacoes/",
    views.product_variation_list,
    name="product_variation_list",
    ),

    path(
    "produtos/<int:id>/variacoes/nova/",
    views.product_variation_create,
    name="product_variation_create",
    ),

    path(
        "produtos/<int:product_id>/variacoes/<int:variation_id>/editar/",
        views.product_variation_edit,
        name="product_variation_edit",
    ),

    path(
        "produtos/<int:product_id>/variacoes/<int:variation_id>/excluir/",
        views.product_variation_delete,
        name="product_variation_delete",
    ),

    path(
        "produtos/<int:id>/adicionais/",
        views.addon_group_list,
        name="addon_group_list",
    ),

    path(
        "produtos/<int:id>/adicionais/novo/",
        views.addon_group_create,
        name="addon_group_create",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/editar/",
        views.addon_group_edit,
        name="addon_group_edit",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/excluir/",
        views.addon_group_delete,
        name="addon_group_delete",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/opcoes/",
        views.addon_list,
        name="addon_list",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/opcoes/nova/",
        views.addon_create,
        name="addon_create",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/opcoes/<int:addon_id>/editar/",
        views.addon_edit,
        name="addon_edit",
    ),

    path(
        "produtos/<int:product_id>/adicionais/<int:group_id>/opcoes/<int:addon_id>/excluir/",
        views.addon_delete,
        name="addon_delete",
    ),

    path(
        "r/<slug:slug>/",
        views.public_menu,
        name="public_menu",
    ),

    path(
        "r/<slug:slug>/produto/<int:product_id>/",
        views.public_product_detail,
        name="public_product_detail",
    ),

    path(
        "r/<slug:slug>/produto/<int:product_id>/adicionar/",
        views.add_to_cart,
        name="add_to_cart",
    ),

    path(
        "r/<slug:slug>/carrinho/",
        views.cart_detail,
        name="cart_detail",
    ),

    path(
        "r/<slug:slug>/carrinho/remover/<int:index>/",
        views.cart_remove,
        name="cart_remove",
    ),

    path(
        "r/<slug:slug>/carrinho/quantidade/<int:index>/<str:action>/",
        views.cart_quantity,
        name="cart_quantity",
    ),

    path(
        "r/<slug:slug>/checkout/",
        views.checkout,
        name="checkout",
    ),

    path(
        "r/<slug:slug>/pedido/<uuid:public_token>/",
        views.order_confirmation,
        name="order_confirmation",
    ),

    path(
        "r/<slug:slug>/mesa/<int:table_number>/",
        views.public_table_menu,
        name="public_table_menu",
    ),

    path(
        "r/<slug:slug>/mesa/remover/",
        views.remove_table_context,
        name="remove_table_context",
    ),

    path(
        "r/<slug:slug>/mesa/trocar/",
        views.change_table_context,
        name="change_table_context",
    ),

    path(
        "produtos/<int:product_id>/adicionais/copiar/",
        views.copy_product_addons,
        name="copy_product_addons",
    ),
]