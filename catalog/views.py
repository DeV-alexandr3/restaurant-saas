from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone

from restaurants.services import get_current_membership
from .models import (
    Category, 
    Product, 
    ProductVariation,
    AddonGroup,
    Addon,
    Order,
    OrderItem,
    OrderItemAddon,
    )
from restaurants.models import Restaurant
from restaurants.models import Table
from decimal import Decimal, InvalidOperation
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension
from PIL import Image, UnidentifiedImageError

@login_required
def category_list(request):
    membership = get_current_membership(request.user)

    if membership is None:
        return HttpResponse("Usuário não possui restaurante ativo.")

    categories = Category.objects.filter(
        restaurant=membership.restaurant
    )

    context = {
        "categories": categories,
        "restaurant": membership.restaurant,
    }

    return render(
        request,
        "catalog/category_list.html",
        context,
    )

@login_required
def category_create(request):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("category_list")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        position_value = request.POST.get("position", "0")
        is_active = request.POST.get("is_active") == "on"

        if not name:
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "error": "Informe o nome da categoria.",
                },
            )

        try:
            position = int(position_value)
        except ValueError:
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "error": "Informe uma posição válida.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if Category.objects.filter(
            restaurant=membership.restaurant,
            name__iexact=name,
        ).exists():
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "error": "Já existe uma categoria com esse nome.",
                },
            )

        Category.objects.create(
            restaurant=membership.restaurant,
            name=name,
            position=position,
            is_active=is_active,
        )

        return redirect("category_list")

    return render(
        request,
        "catalog/category_form.html",
        {
            "restaurant": membership.restaurant,
        },
    )

@login_required
def category_edit(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("category_list")

    category = get_object_or_404(
        Category,
        id=id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        position_value = request.POST.get("position", "0")
        is_active = request.POST.get("is_active") == "on"

        try:
            position = int(position_value)
        except ValueError:
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "category": category,
                    "error": "Informe uma posição válida.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/category_form.html",
                {
                    "restaurant": membership.restaurant,
                    "category": category,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if name:
            category.name = name
            category.position = position
            category.is_active = is_active
            category.save()

            return redirect("category_list")

    return render(
        request,
        "catalog/category_form.html",
        {
            "restaurant": membership.restaurant,
            "category": category,
        },
    )

@login_required
def category_delete(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("category_list")

    category = get_object_or_404(
        Category,
        id=id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        try:
            category.delete()

        except ProtectedError:
            messages.error(
                request,
                (
                    "Não é possível excluir esta categoria "
                    "porque existem produtos vinculados a ela."
                ),
            )

    return redirect("category_list")

@login_required
def product_list(request):
    membership = get_current_membership(request.user)

    if membership is None:
        return HttpResponse("Usuário não possui restaurante ativo.")

    products = Product.objects.filter(
        restaurant=membership.restaurant
    ).select_related("category")

    return render(
        request,
        "catalog/product_list.html",
        {
            "restaurant": membership.restaurant,
            "products": products,
        },
    )

@login_required
def product_create(request):

    membership = get_current_membership(
        request.user
    )

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    categories = Category.objects.filter(
        restaurant=membership.restaurant,
        is_active=True,
    )

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        price_value = request.POST.get(
            "price",
            ""
        ).strip()

        category_id = request.POST.get(
            "category"
        )

        is_available = (
            request.POST.get(
                "is_available"
            ) == "on"
        )

        image = request.FILES.get(
            "image"
        )

        if image:
            # Limite de tamanho: 5 MB
            if image.size > 5 * 1024 * 1024:
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "error": "A imagem deve ter no máximo 5 MB.",
                    },
                )

            # Tipos permitidos
            allowed_content_types = {
                "image/jpeg",
                "image/png",
                "image/webp",
            }

            if image.content_type not in allowed_content_types:
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "error": "Envie uma imagem JPG, PNG ou WEBP.",
                    },
                )

            # Confere se o conteúdo realmente é uma imagem
            try:
                opened_image = Image.open(image)
                opened_image.verify()

                if opened_image.format not in {
                    "JPEG",
                    "PNG",
                    "WEBP",
                }:
                    raise UnidentifiedImageError

                image.seek(0)

            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
            ):
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "error": "O arquivo enviado não é uma imagem válida.",
                    },
                )
            
        try:
            price = Decimal(
                price_value
            )

        except InvalidOperation:
            price = None

        if price is None or price < 0:
            return render(
                request,
                "catalog/product_form.html",
                {
                    "restaurant": (
                        membership.restaurant
                    ),
                    "categories": categories,
                    "error": (
                        "Informe um preço válido."
                    ),
                },
            )

        category = get_object_or_404(
            Category,
            id=category_id,
            restaurant=membership.restaurant,
        )

        if name:
            Product.objects.create(
                restaurant=membership.restaurant,
                category=category,
                name=name,
                description=description,
                image=image,
                price=price,
                is_available=is_available, 
            )

            return redirect(
                "product_list"
            )

        if not name:
            return render(
                request,
                "catalog/product_form.html",
                {
                    "restaurant": membership.restaurant,
                    "categories": categories,
                    "error": "Informe o nome do produto.",
                },
            )

    return render(
        request,
        "catalog/product_form.html",
        {
            "restaurant": membership.restaurant,
            "categories": categories,
        },
    )

@login_required
def product_edit(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    categories = Category.objects.filter(
        restaurant=membership.restaurant,
        is_active=True,
    )

    

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        price_value = request.POST.get("price", "").strip()
        category_id = request.POST.get("category")
        is_available = request.POST.get("is_available") == "on"

        image = request.FILES.get("image")

        if image:
            # Limite de tamanho: 5 MB
            if image.size > 5 * 1024 * 1024:
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "product": product,
                        "error": "A imagem deve ter no máximo 5 MB.",
                    },
                )

            # Tipos permitidos
            allowed_content_types = {
                "image/jpeg",
                "image/png",
                "image/webp",
            }

            if image.content_type not in allowed_content_types:
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "product": product,
                        "error": "Envie uma imagem JPG, PNG ou WEBP.",
                    },
                )

            # Confere se o conteúdo realmente é uma imagem
            try:
                opened_image = Image.open(image)
                opened_image.verify()

                if opened_image.format not in {
                    "JPEG",
                    "PNG",
                    "WEBP",
                }:
                    raise UnidentifiedImageError

                image.seek(0)

            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
            ):
                return render(
                    request,
                    "catalog/product_form.html",
                    {
                        "restaurant": membership.restaurant,
                        "categories": categories,
                        "product": product,
                        "error": "O arquivo enviado não é uma imagem válida.",
                    },
                )

        try:
            price = Decimal(price_value)

        except InvalidOperation:
            return render(
                request,
                "catalog/product_form.html",
                {
                    "restaurant": membership.restaurant,
                    "categories": categories,
                    "product": product,
                    "error": "Informe um preço válido.",
                },
            )

        if price < 0:
            return render(
                request,
                "catalog/product_form.html",
                {
                    "restaurant": membership.restaurant,
                    "categories": categories,
                    "product": product,
                    "error": "O preço não pode ser negativo.",
                },
            )

        category = get_object_or_404(
            Category,
            id=category_id,
            restaurant=membership.restaurant,
        )

        

        if name:
            product.name = name
            product.description = description
            product.price = price
            product.category = category
            product.is_available = is_available
            if image:
                product.image = image
            product.save()

            return redirect("product_list")

        if not name:
            return render(
                request,
                "catalog/product_form.html",
                {
                    "restaurant": membership.restaurant,
                    "categories": categories,
                    "product": product,
                    "error": "Informe o nome do produto.",
                },
            )

    return render(
        request,
        "catalog/product_form.html",
        {
            "restaurant": membership.restaurant,
            "categories": categories,
            "product": product,
        },
    )

@login_required
def product_delete(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        product.delete()

    return redirect("product_list")

@login_required
def product_variation_list(request, id):
    membership = get_current_membership(request.user)

    if membership is None:
        return HttpResponse("Usuário não possui restaurante ativo.")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    variations = ProductVariation.objects.filter(
        product=product
    )

    return render(
        request,
        "catalog/product_variation_list.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "variations": variations,
        },
    )

@login_required
def product_variation_create(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        price_value = request.POST.get("price", "").strip()
        position_value = request.POST.get("position", "0")
        is_available = request.POST.get("is_available") == "on"

        try:
            price = Decimal(
                price_value
            )

        except InvalidOperation:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Informe um preço válido.",
                },
            )

        if price < 0:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "O preço não pode ser negativo.",
                },
            )

        try:
            position = int(
                position_value
            )

        except ValueError:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Informe uma posição válida.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if name:
            ProductVariation.objects.create(
                product=product,
                name=name,
                price=price,
                position=position,
                is_available=is_available,
            )

            return redirect(
                "product_variation_list",
                id=product.id,
            )

    return render(
        request,
        "catalog/product_variation_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
        },
    )

@login_required
def product_variation_edit(request, product_id, variation_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    variation = get_object_or_404(
        ProductVariation,
        id=variation_id,
        product=product,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        price_value = request.POST.get("price", "").strip()
        position_value = request.POST.get("position", "0")
        is_available = request.POST.get("is_available") == "on"

        try:
            price = Decimal(price_value)
        except InvalidOperation:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "variation": variation,
                    "error": "Informe um preço válido.",
                },
            )

        if price < 0:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "variation": variation,
                    "error": "O preço não pode ser negativo.",
                },
            )

        try:
            position = int(position_value)
        except ValueError:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "variation": variation,
                    "error": "Informe uma posição válida.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/product_variation_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "variation": variation,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if name:
            variation.name = name
            variation.price = price
            variation.position = position
            variation.is_available = is_available
            variation.save()

            return redirect(
                "product_variation_list",
                id=product.id,
            )

    return render(
        request,
        "catalog/product_variation_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "variation": variation,
        },
    )

@login_required
def product_variation_delete(request, product_id, variation_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    variation = get_object_or_404(
        ProductVariation,
        id=variation_id,
        product=product,
    )

    if request.method == "POST":
        variation.delete()

    return redirect(
        "product_variation_list",
        id=product.id,
    )

@login_required
def addon_group_list(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    addon_groups = AddonGroup.objects.filter(
        product=product
    )

    source_products = Product.objects.filter(
        restaurant=membership.restaurant,
    ).exclude(
        id=product.id
    )

    return render(
        request,
        "catalog/addon_group_list.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "addon_groups": addon_groups,
            "source_products": source_products,
        },
    )

@login_required
def addon_group_create(request, id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=id,
        restaurant=membership.restaurant,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        min_choices_value = request.POST.get("min_choices", "0")
        max_choices_value = request.POST.get("max_choices", "1")
        position_value = request.POST.get("position", "0")
        is_active = request.POST.get("is_active") == "on"

        try:
            min_choices = int(min_choices_value)
            max_choices = int(max_choices_value)
            position = int(position_value)
        except ValueError:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Os valores mínimo, máximo e posição devem ser números inteiros.",
                },
            )

        if min_choices < 0 or max_choices < 0 or position < 0:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Os valores não podem ser negativos.",
                },
            )

        if min_choices > max_choices:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "O mínimo de escolhas não pode ser maior que o máximo.",
                },
            )

        if not name:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Informe o nome do grupo.",
                },
            )

        if AddonGroup.objects.filter(
            product=product,
            name=name,
        ).exists():
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "error": "Já existe um grupo com esse nome neste produto.",
                },
            )

        AddonGroup.objects.create(
            product=product,
            name=name,
            min_choices=min_choices,
            max_choices=max_choices,
            position=position,
            is_active=is_active,
        )

        return redirect(
            "addon_group_list",
            id=product.id,
        )

    return render(
        request,
        "catalog/addon_group_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
        },
    )

@login_required
def addon_group_edit(request, product_id, group_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        min_choices_value = request.POST.get("min_choices", "0")
        max_choices_value = request.POST.get("max_choices", "1")
        position_value = request.POST.get("position", "0")
        is_active = request.POST.get("is_active") == "on"

        try:
            min_choices = int(min_choices_value)
            max_choices = int(max_choices_value)
            position = int(position_value)
        except ValueError:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Os valores mínimo, máximo e posição devem ser números inteiros.",
                },
            )

        if min_choices < 0 or max_choices < 0 or position < 0:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Os valores não podem ser negativos.",
                },
            )

        if min_choices > max_choices:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "O mínimo de escolhas não pode ser maior que o máximo.",
                },
            )

        if not name:
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Informe o nome do grupo.",
                },
            )

        if AddonGroup.objects.filter(
            product=product,
            name=name,
        ).exclude(id=group.id).exists():
            return render(
                request,
                "catalog/addon_group_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Já existe um grupo com esse nome neste produto.",
                },
            )

        group.name = name
        group.min_choices = min_choices
        group.max_choices = max_choices
        group.position = position
        group.is_active = is_active

        group.save()

        return redirect(
            "addon_group_list",
            id=product.id,
        )

    return render(
        request,
        "catalog/addon_group_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "group": group,
        },
    )

@login_required
def addon_group_delete(request, product_id, group_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    if request.method == "POST":
        group.delete()

    return redirect(
        "addon_group_list",
        id=product.id,
    )

@login_required
@transaction.atomic
def copy_product_addons(request, product_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    destination_product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    if request.method != "POST":
        return redirect(
            "addon_group_list",
            id=destination_product.id,
        )

    source_product_id = request.POST.get(
        "source_product"
    )

    source_product = get_object_or_404(
        Product,
        id=source_product_id,
        restaurant=membership.restaurant,
    )

    if source_product.id == destination_product.id:
        messages.error(
            request,
            "Não é possível copiar adicionais do mesmo produto.",
        )

        return redirect(
            "addon_group_list",
            id=destination_product.id,
        )

    source_groups = (
        AddonGroup.objects
        .filter(product=source_product)
        .prefetch_related("addons")
    )

    copied_groups = 0
    copied_addons = 0

    for source_group in source_groups:

        # Procura um grupo com o mesmo nome no produto destino
        destination_group = AddonGroup.objects.filter(
            product=destination_product,
            name__iexact=source_group.name,
        ).first()

        # =========================================================
        # SE O GRUPO JÁ EXISTE, ATUALIZA
        # =========================================================
        if destination_group:

            destination_group.name = source_group.name
            destination_group.min_choices = source_group.min_choices
            destination_group.max_choices = source_group.max_choices
            destination_group.position = source_group.position
            destination_group.is_active = source_group.is_active

            destination_group.save()

            # Remove as opções antigas desse grupo
            destination_group.addons.all().delete()

            # Copia novamente as opções da origem
            for source_addon in source_group.addons.all():

                Addon.objects.create(
                    group=destination_group,
                    name=source_addon.name,
                    price=source_addon.price,
                    position=source_addon.position,
                    is_available=source_addon.is_available,
                )

                copied_addons += 1

            copied_groups += 1


        # =========================================================
        # SE O GRUPO NÃO EXISTE, CRIA NORMALMENTE
        # =========================================================
        else:

            new_group = AddonGroup.objects.create(
                product=destination_product,
                name=source_group.name,
                min_choices=source_group.min_choices,
                max_choices=source_group.max_choices,
                position=source_group.position,
                is_active=source_group.is_active,
            )

            copied_groups += 1

            for source_addon in source_group.addons.all():

                Addon.objects.create(
                    group=new_group,
                    name=source_addon.name,
                    price=source_addon.price,
                    position=source_addon.position,
                    is_available=source_addon.is_available,
                )

                copied_addons += 1

    source_variations = ProductVariation.objects.filter(
        product=source_product
    )

    copied_variations = 0

    for source_variation in source_variations:

        destination_variation = ProductVariation.objects.filter(
            product=destination_product,
            name__iexact=source_variation.name,
        ).first()

        # =========================================================
        # SE A VARIAÇÃO JÁ EXISTE, ATUALIZA
        # =========================================================
        if destination_variation:

            destination_variation.name = source_variation.name
            destination_variation.price = source_variation.price
            destination_variation.position = source_variation.position
            destination_variation.is_available = source_variation.is_available

            destination_variation.save()

        # =========================================================
        # SE NÃO EXISTE, CRIA
        # =========================================================
        else:

            ProductVariation.objects.create(
                product=destination_product,
                name=source_variation.name,
                price=source_variation.price,
                position=source_variation.position,
                is_available=source_variation.is_available,
            )

        copied_variations += 1

    messages.success(
        request,
        (
            f"Configurações sincronizadas com {source_product.name}. "
            f"{copied_groups} grupo(s), "
            f"{copied_addons} adicional(is) e "
            f"{copied_variations} variação(ões) processados."
        ),
    )

    return redirect(
        "addon_group_list",
        id=destination_product.id,
    )

@login_required
def addon_list(request, product_id, group_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    addons = Addon.objects.filter(
        group=group
    )

    return render(
        request,
        "catalog/addon_list.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "group": group,
            "addons": addons,
        },
    )

@login_required
def addon_create(request, product_id, group_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        price_value = request.POST.get("price", "0").strip()
        position_value = request.POST.get("position", "0")

        is_available = request.POST.get("is_available") == "on"

        try:
            price = Decimal(price_value or "0")
            position = int(position_value or 0)
        except (InvalidOperation, ValueError):
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Preço e posição devem ser valores válidos.",
                },
            )

        if price < 0:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "O preço não pode ser negativo.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if not name:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Informe o nome do adicional.",
                },
            )

        if Addon.objects.filter(
            group=group,
            name=name,
        ).exists():
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "error": "Já existe um adicional com esse nome neste grupo.",
                },
            )

        Addon.objects.create(
            group=group,
            name=name,
            price=price,
            position=position,
            is_available=is_available,
        )

        return redirect(
            "addon_list",
            product_id=product.id,
            group_id=group.id,
        )
    
    return render(
        request,
        "catalog/addon_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "group": group,
        },
    )

@login_required
def addon_edit(request, product_id, group_id, addon_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    addon = get_object_or_404(
        Addon,
        id=addon_id,
        group=group,
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        price_value = request.POST.get("price", "0").strip()
        position_value = request.POST.get("position", "0")

        is_available = request.POST.get("is_available") == "on"

        try:
            price = Decimal(price_value or "0")
            position = int(position_value or 0)
        except (InvalidOperation, ValueError):
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "addon": addon,
                    "error": "Preço e posição devem ser valores válidos.",
                },
            )

        if price < 0:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "addon": addon,
                    "error": "O preço não pode ser negativo.",
                },
            )

        if position < 0:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "addon": addon,
                    "error": "A posição não pode ser negativa.",
                },
            )

        if not name:
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "addon": addon,
                    "error": "Informe o nome do adicional.",
                },
            )

        if Addon.objects.filter(
            group=group,
            name=name,
        ).exclude(id=addon.id).exists():
            return render(
                request,
                "catalog/addon_form.html",
                {
                    "restaurant": membership.restaurant,
                    "product": product,
                    "group": group,
                    "addon": addon,
                    "error": "Já existe um adicional com esse nome neste grupo.",
                },
            )

        addon.name = name
        addon.price = price
        addon.position = position
        addon.is_available = is_available

        addon.save()

        return redirect(
            "addon_list",
            product_id=product.id,
            group_id=group.id,
        )

    return render(
        request,
        "catalog/addon_form.html",
        {
            "restaurant": membership.restaurant,
            "product": product,
            "group": group,
            "addon": addon,
        },
    )

@login_required
def addon_delete(request, product_id, group_id, addon_id):
    membership = get_current_membership(request.user)

    if not membership:
        return redirect("login")

    if membership.role != "ADMIN":
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=membership.restaurant,
    )

    group = get_object_or_404(
        AddonGroup,
        id=group_id,
        product=product,
    )

    addon = get_object_or_404(
        Addon,
        id=addon_id,
        group=group,
    )

    if request.method == "POST":
        addon.delete()

    return redirect(
        "addon_list",
        product_id=product.id,
        group_id=group.id,
    )

def public_menu(request, slug):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).prefetch_related(
        "products"
    )

    table_context = request.session.get("table_context")

    current_table = None

    if (
        table_context
        and table_context.get("restaurant_id") == restaurant.id
    ):
        current_table = Table.objects.filter(
            id=table_context.get("table_id"),
            restaurant=restaurant,
            is_active=True,
        ).first()

    active_tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).order_by("number")

    print(
        "Mesa da sessão:",
        request.session.get("table_context")
    )

    last_order = None

    last_order_token = request.session.get("last_order_token")
    last_order_restaurant_id = request.session.get(
        "last_order_restaurant_id"
    )

    if (
        last_order_token
        and last_order_restaurant_id == restaurant.id
    ):
        limit_time = timezone.now() - timedelta(hours=24)
        
        last_order = Order.objects.filter(
            public_token=last_order_token,
            restaurant=restaurant,
            created_at__gte=limit_time,
        ).first()

    cart = request.session.get("cart", {})

    cart_count = 0

    if cart.get("restaurant_id") == restaurant.id:
        for item in cart.get("items", []):
            try:
                cart_count += int(
                    item.get("quantity", 1)
                )
            except (TypeError, ValueError):
                cart_count += 1

    return render(
        request,
        "catalog/public/menu.html",
        {
            "restaurant": restaurant,
            "categories": categories,
            "current_table": current_table,
            "active_tables": active_tables,
            "last_order": last_order,
            "cart_count": cart_count,
        },
    )

def public_product_detail(request, slug, product_id):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=restaurant,
        is_available=True,
    )

    variations = ProductVariation.objects.filter(
        product=product,
        is_available=True,
    )

    addon_groups = AddonGroup.objects.filter(
        product=product,
        is_active=True,
    ).prefetch_related(
        "addons"
    )

    cart = request.session.get("cart", {})

    cart_count = 0

    if cart.get("restaurant_id") == restaurant.id:
        for item in cart.get("items", []):
            try:
                cart_count += int(
                    item.get("quantity", 1)
                )
            except (TypeError, ValueError):
                cart_count += 1

    return render(
        request,
        "catalog/public/product_detail.html",
        {
            "restaurant": restaurant,
            "product": product,
            "variations": variations,
            "addon_groups": addon_groups,
            "cart_count": cart_count,
        },
    )

def add_to_cart(request, slug, product_id):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    product = get_object_or_404(
        Product,
        id=product_id,
        restaurant=restaurant,
        is_available=True,
    )

    if request.method != "POST":
        return redirect(
            "public_product_detail",
            slug=restaurant.slug,
            product_id=product.id,
        )

    variation_id = request.POST.get("variation")
    addon_ids = request.POST.getlist("addon")

    addon_groups = AddonGroup.objects.filter(
        product=product,
        is_active=True,
    ).prefetch_related(
        "addons"
    )

    for key, value in request.POST.items():
        if key.startswith("addon_group_") and value:
            addon_ids.append(value)

    selected_addon_ids = set(
        int(addon_id)
        for addon_id in addon_ids
        if str(addon_id).isdigit()
    )

    for group in addon_groups:
        valid_group_addon_ids = set(
            group.addons.filter(
                is_available=True
            ).values_list(
                "id",
                flat=True,
            )
        )

        selected_in_group = (
            selected_addon_ids
            & valid_group_addon_ids
        )

        selected_count = len(
            selected_in_group
        )

        if selected_count < group.min_choices:
            messages.error(
                request,
                (
                    f"Escolha pelo menos "
                    f"{group.min_choices} opção(ões) "
                    f"em {group.name}."
                ),
            )

            return redirect(
                "public_product_detail",
                slug=restaurant.slug,
                product_id=product.id,
            )

        if selected_count > group.max_choices:
            messages.error(
                request,
                (
                    f"Escolha no máximo "
                    f"{group.max_choices} opção(ões) "
                    f"em {group.name}."
                ),
            )

            return redirect(
                "public_product_detail",
                slug=restaurant.slug,
                product_id=product.id,
            )

    variation = None

    if variation_id:
        variation = get_object_or_404(
            ProductVariation,
            id=variation_id,
            product=product,
            is_available=True,
        )

    addons = Addon.objects.filter(
        id__in=selected_addon_ids,
        group__product=product,
        group__is_active=True,
        is_available=True,
    )

    if variation:
        total = variation.price
    else:
        total = product.price

    for addon in addons:
        total += addon.price

    cart = request.session.get("cart")

    if not cart:
        cart = {
            "restaurant_id": restaurant.id,
            "items": [],
        }

    if cart["restaurant_id"] != restaurant.id:
        cart = {
            "restaurant_id": restaurant.id,
            "items": [],
        }

    item = {
        "product_id": product.id,
        "variation_id": variation.id if variation else None,
        "addon_ids": [addon.id for addon in addons],
        "quantity": 1,
    }

    cart["items"].append(item)

    request.session["cart"] = cart
    request.session.modified = True

    return redirect(
        "public_product_detail",
        slug=restaurant.slug,
        product_id=product.id,
    )

def cart_detail(request, slug):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    cart = request.session.get("cart")

    cart_items = []
    cart_total = 0

    if cart and cart.get("restaurant_id") == restaurant.id:

        for index, item in enumerate(cart.get("items", [])):

            product = Product.objects.filter(
                id=item["product_id"],
                restaurant=restaurant,
                is_available=True,
            ).first()

            if not product:
                continue

            variation = None

            if item.get("variation_id"):
                variation = ProductVariation.objects.filter(
                    id=item["variation_id"],
                    product=product,
                    is_available=True,
                ).first()

            addons = Addon.objects.filter(
                id__in=item.get("addon_ids", []),
                group__product=product,
                is_available=True,
            )

            if variation:
                unit_price = variation.price
            else:
                unit_price = product.price

            for addon in addons:
                unit_price += addon.price

            quantity = item.get("quantity", 1)

            item_total = unit_price * quantity

            cart_total += item_total

            cart_items.append(
                {
                    "index": index,
                    "product": product,
                    "variation": variation,
                    "addons": addons,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total": item_total,
                }
            )

    return render(
        request,
        "catalog/public/cart.html",
        {
            "restaurant": restaurant,
            "cart_items": cart_items,
            "cart_total": cart_total,
        },
    )

def cart_remove(request, slug, index):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    if request.method != "POST":
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    cart = request.session.get("cart")

    if not cart:
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    if cart.get("restaurant_id") != restaurant.id:
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    items = cart.get("items", [])

    if 0 <= index < len(items):
        items.pop(index)

    cart["items"] = items

    request.session["cart"] = cart
    request.session.modified = True

    return redirect(
        "cart_detail",
        slug=restaurant.slug,
    )

def cart_quantity(request, slug, index, action):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    if request.method != "POST":
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    cart = request.session.get("cart")

    if not cart:
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    if cart.get("restaurant_id") != restaurant.id:
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )

    items = cart.get("items", [])

    if 0 <= index < len(items):

        if action == "increase":
            items[index]["quantity"] += 1

        elif action == "decrease":
            if items[index]["quantity"] > 1:
                items[index]["quantity"] -= 1
            else:
                items.pop(index)

    cart["items"] = items

    request.session["cart"] = cart
    request.session.modified = True

    return redirect(
        "cart_detail",
        slug=restaurant.slug,
    )

def checkout(request, slug):

    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    cart = request.session.get("cart")

    if (
        not cart
        or cart.get("restaurant_id") != restaurant.id
        or not cart.get("items")
    ):
        return redirect(
            "cart_detail",
            slug=restaurant.slug,
        )


    # =========================
    # MESA DA SESSÃO
    # =========================

    table_context = request.session.get(
        "table_context"
    )

    session_table = None

    if (
        table_context
        and table_context.get(
            "restaurant_id"
        ) == restaurant.id
    ):
        session_table = Table.objects.filter(
            id=table_context.get("table_id"),
            restaurant=restaurant,
            is_active=True,
        ).first()


    # =========================
    # VALIDAR ITENS DO CARRINHO
    # =========================

    prepared_items = []
    checkout_subtotal = Decimal("0")

    for cart_item in cart["items"]:

        product = get_object_or_404(
            Product,
            id=cart_item["product_id"],
            restaurant=restaurant,
            is_available=True,
        )

        variation = None

        if cart_item.get("variation_id"):
            variation = get_object_or_404(
                ProductVariation,
                id=cart_item["variation_id"],
                product=product,
                is_available=True,
            )


        # -------------------------
        # ADICIONAIS
        # -------------------------

        selected_addon_ids = set(
            int(addon_id)
            for addon_id in cart_item.get(
                "addon_ids",
                []
            )
            if str(addon_id).isdigit()
        )

        addon_groups = AddonGroup.objects.filter(
            product=product,
            is_active=True,
        ).prefetch_related(
            "addons"
        )

        for group in addon_groups:

            valid_group_addon_ids = set(
                group.addons.filter(
                    is_available=True
                ).values_list(
                    "id",
                    flat=True,
                )
            )

            selected_in_group = (
                selected_addon_ids
                & valid_group_addon_ids
            )

            selected_count = len(
                selected_in_group
            )

            if (
                selected_count
                < group.min_choices
            ):
                messages.error(
                    request,
                    (
                        f"O produto {product.name} "
                        f"precisa de pelo menos "
                        f"{group.min_choices} opção(ões) "
                        f"em {group.name}."
                    ),
                )

                return redirect(
                    "cart_detail",
                    slug=restaurant.slug,
                )

            if (
                selected_count
                > group.max_choices
            ):
                messages.error(
                    request,
                    (
                        f"O produto {product.name} "
                        f"permite no máximo "
                        f"{group.max_choices} opção(ões) "
                        f"em {group.name}."
                    ),
                )

                return redirect(
                    "cart_detail",
                    slug=restaurant.slug,
                )


        addons = Addon.objects.filter(
            id__in=selected_addon_ids,
            group__product=product,
            group__is_active=True,
            is_available=True,
        )


        # -------------------------
        # PREÇO
        # -------------------------

        if variation:
            unit_price = variation.price
        else:
            unit_price = product.price

        for addon in addons:
            unit_price += addon.price


        # -------------------------
        # QUANTIDADE
        # -------------------------

        try:
            quantity = int(
                cart_item.get(
                    "quantity",
                    1
                )
            )

        except (TypeError, ValueError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        if quantity > 100:
            quantity = 100


        item_total = (
            unit_price * quantity
        )

        checkout_subtotal += item_total


        prepared_items.append({
            "product": product,
            "variation": variation,
            "addons": list(addons),
            "quantity": quantity,
            "unit_price": unit_price,
            "total": item_total,
        })


    # =========================
    # FINALIZAR PEDIDO
    # =========================

    if request.method == "POST":

        customer_name = request.POST.get(
            "name",
            ""
        ).strip()

        customer_phone = request.POST.get(
            "phone",
            ""
        ).strip()

        order_type = request.POST.get(
            "order_type"
        )

        address = request.POST.get(
            "address",
            ""
        ).strip()

        address_number = request.POST.get(
            "number",
            ""
        ).strip()

        complement = request.POST.get(
            "complement",
            ""
        ).strip()

        table_number = request.POST.get(
            "table_number"
        )

        notes = request.POST.get("notes", "").strip()

        selected_table = session_table


        # -------------------------
        # TIPOS DE PEDIDO PERMITIDOS
        # -------------------------

        allowed_order_types = []

        if restaurant.accepts_pickup:
            allowed_order_types.append(
                "pickup"
            )

        if restaurant.accepts_delivery:
            allowed_order_types.append(
                "delivery"
            )

        if restaurant.accepts_table_orders:
            allowed_order_types.append(
                "table"
            )

        if (
            order_type
            not in allowed_order_types
        ):
            return redirect(
                "checkout",
                slug=restaurant.slug,
            )


        # -------------------------
        # CLIENTE
        # -------------------------

        if (
            not customer_name
            or not customer_phone
        ):
            messages.error(
                request,
                "Informe nome e telefone."
            )

            return redirect(
                "checkout",
                slug=restaurant.slug,
            )


        # -------------------------
        # ENTREGA
        # -------------------------

        if order_type == "delivery":

            if (
                not address
                or not address_number
            ):
                messages.error(
                    request,
                    (
                        "Informe o endereço "
                        "para entrega."
                    ),
                )

                return redirect(
                    "checkout",
                    slug=restaurant.slug,
                )


        # -------------------------
        # MESA
        # -------------------------

        if (
            order_type == "table"
            and not selected_table
        ):

            if not table_number:
                messages.error(
                    request,
                    "Selecione uma mesa."
                )

                return redirect(
                    "checkout",
                    slug=restaurant.slug,
                )

            selected_table = (
                get_object_or_404(
                    Table,
                    restaurant=restaurant,
                    number=table_number,
                    is_active=True,
                )
            )


        # Se não for pedido de mesa,
        # não salva nenhuma mesa no pedido.

        if order_type != "table":
            selected_table = None


        # -------------------------
        # PEDIDO MÍNIMO
        # -------------------------

        if (
            checkout_subtotal
            < restaurant.minimum_order
        ):

            missing_amount = (
                restaurant.minimum_order
                - checkout_subtotal
            )

            messages.error(
                request,
                (
                    f"Pedido mínimo: "
                    f"R$ {restaurant.minimum_order}. "
                    f"Seu carrinho: "
                    f"R$ {checkout_subtotal}. "
                    f"Faltam R$ {missing_amount} "
                    f"para finalizar."
                ),
            )

            return redirect(
                "cart_detail",
                slug=restaurant.slug,
            )


        # -------------------------
        # TOTAL FINAL
        # -------------------------

        final_total = checkout_subtotal

        if order_type == "delivery":
            final_total += (
                restaurant.delivery_fee
            )


        # =========================
        # CRIAR PEDIDO
        # =========================

        with transaction.atomic():

            order = Order.objects.create(
                restaurant=restaurant,

                customer_name=customer_name,
                customer_phone=customer_phone,

                order_type=order_type,
                notes=notes,
                address=(
                    address
                    if order_type == "delivery"
                    else ""
                ),

                address_number=(
                    address_number
                    if order_type == "delivery"
                    else ""
                ),

                complement=(
                    complement
                    if order_type == "delivery"
                    else ""
                ),

                table=selected_table,

                table_number=(
                    selected_table.number
                    if selected_table
                    else None
                ),

                delivery_fee=(
                    restaurant.delivery_fee
                    if order_type == "delivery"
                    else 0
                ),

                estimated_time_minutes=(
                    restaurant
                    .estimated_time_minutes
                ),

                total=final_total,
            )


            for prepared_item in prepared_items:

                product = (
                    prepared_item["product"]
                )

                variation = (
                    prepared_item["variation"]
                )

                addons = (
                    prepared_item["addons"]
                )

                quantity = (
                    prepared_item["quantity"]
                )

                unit_price = (
                    prepared_item["unit_price"]
                )

                item_total = (
                    prepared_item["total"]
                )


                order_item = (
                    OrderItem.objects.create(
                        order=order,

                        product=product,

                        product_name=(
                            product.name
                        ),

                        variation_name=(
                            variation.name
                            if variation
                            else ""
                        ),

                        unit_price=unit_price,

                        quantity=quantity,

                        total=item_total,
                    )
                )


                for addon in addons:

                    OrderItemAddon.objects.create(
                        order_item=order_item,

                        addon_name=addon.name,

                        addon_price=addon.price,
                    )


        # =========================
        # LIMPAR CARRINHO
        # =========================

        request.session.pop(
            "cart",
            None
        )

        request.session[
            "last_order_token"
        ] = str(
            order.public_token
        )

        request.session[
            "last_order_restaurant_id"
        ] = restaurant.id


        return redirect(
            "order_confirmation",
            slug=restaurant.slug,
            public_token=order.public_token,
        )


    # =========================
    # GET DO CHECKOUT
    # =========================

    tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).order_by(
        "number"
    )

    notes = request.POST.get("notes", "").strip()

    return render(
        request,
        "catalog/public/checkout.html",
        {
            "restaurant": restaurant,
            "tables": tables,
            "session_table": session_table,
            "checkout_subtotal": (
                checkout_subtotal
            ),
            "notes": notes,
        },
    )

def order_confirmation(request, slug, public_token):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    order = get_object_or_404(
        Order,
        public_token=public_token,
        restaurant=restaurant,
    )

    return render(
        request,
        "catalog/public/order_confirmation.html",
        {
            "restaurant": restaurant,
            "order": order,
        },
    )

def public_table_menu(request, slug, table_number):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    table = get_object_or_404(
        Table,
        restaurant=restaurant,
        number=table_number,
        is_active=True,
    )

    request.session["table_context"] = {
        "restaurant_id": restaurant.id,
        "table_id": table.id,
        "table_number": table.number,
    }

    return redirect(
        "public_menu",
        slug=restaurant.slug,
    )

def remove_table_context(request, slug):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    if request.method == "POST":
        table_context = request.session.get("table_context")

        if (
            table_context
            and table_context.get("restaurant_id") == restaurant.id
        ):
            request.session.pop("table_context", None)

    return redirect(
        "public_menu",
        slug=restaurant.slug,
    )

def change_table_context(request, slug):
    restaurant = get_object_or_404(
        Restaurant,
        slug=slug,
        is_active=True,
    )

    if request.method == "POST":
        table_id = request.POST.get("table_id")

        table = get_object_or_404(
            Table,
            id=table_id,
            restaurant=restaurant,
            is_active=True,
        )

        request.session["table_context"] = {
            "restaurant_id": restaurant.id,
            "table_id": table.id,
            "table_number": table.number,
        }

        request.session.pop("table_context", None)
        request.session.modified = True

    return redirect(
        "public_menu",
        slug=restaurant.slug,
    )
