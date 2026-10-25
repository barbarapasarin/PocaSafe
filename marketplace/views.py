from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import CollectibleItem, Order, Profile, Review
from .forms import CollectibleItemForm, OrderCreateForm, RegisterForm, ReviewForm


@login_required
def open_dispute(request, pk):
    """Permite al comprador abrir un reclamo antes de liberar los fondos"""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    
    # Solo se puede disputar si la orden está pagada o enviada
    if order.status not in ['paid_escrow', 'shipped']:
        messages.error(request, 'No es posible abrir disputa en el estado actual de la orden.')
        return redirect('order_detail', pk=order.pk)
        
    if request.method == 'POST':
        reason = request.POST.get('dispute_reason', '').strip()
        if reason:
            with transaction.atomic():
                order.status = 'disputed'
                order.dispute_reason = reason
                order.dispute_created_at = timezone.now()
                order.save()
                messages.warning(request, f'Se ha abierto una disputa formal para la Orden #{order.pk}. Los fondos quedan congelados hasta mediación.')
                return redirect('order_detail', pk=order.pk)
        else:
            messages.error(request, 'Debes detallar el motivo del reclamo.')

    return render(request, 'marketplace/dispute_form.html', {'order': order})


@staff_member_required
def dispute_dashboard(request):
    """Panel de mediación exclusivo para administradores/soporte"""
    disputed_orders = Order.objects.filter(status='disputed').order_by('-dispute_created_at')
    return render(request, 'marketplace/dispute_dashboard.html', {'orders': disputed_orders})


@staff_member_required
def resolve_dispute(request, pk):
    """Permite al mediador resolver: liberar fondos al vendedor o reembolsar al comprador"""
    order = get_object_or_404(Order, pk=pk, status='disputed')
    
    if request.method == 'POST':
        resolution = request.POST.get('resolution')  # 'release_seller' o 'refund_buyer'
        admin_notes = request.POST.get('admin_notes', '').strip()
        
        with transaction.atomic():
            order.admin_notes = admin_notes
            if resolution == 'release_seller':
                order.status = 'delivered'
                order.item.status = 'sold'
                order.save()
                order.item.save()
                messages.success(request, f'Disputa #{order.pk} resuelta: Fondos liberados al vendedor.')
            elif resolution == 'refund_buyer':
                order.status = 'cancelled'
                order.item.status = 'available'
                order.save()
                order.item.save()
                messages.info(request, f'Disputa #{order.pk} resuelta: Fondos devueltos al comprador.')
                
            return redirect('dispute_dashboard')

    return render(request, 'marketplace/dispute_resolve.html', {'order': order})


def register(request):
    """Permite el registro de nuevos usuarios en la plataforma"""
    if request.user.is_authenticated:
        return redirect('item_list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenida a PocaSafe, {user.username}!')
            return redirect('item_list')
    else:
        form = RegisterForm()

    return render(request, 'marketplace/register.html', {'form': form})


def item_list(request):
    """Vista principal: Catálogo con soporte de filtros por categoría, tag y texto"""
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category')
    tag_filter = request.GET.get('tag', '').strip()

    items = CollectibleItem.objects.filter(status='available').order_by('-created_at')

    # Filtro de categoría fija (photocard / tcg / other)
    if category_filter:
        items = items.filter(category=category_filter)

    # Filtro directo por tag (ej. al pinchar chip de BTS o ATEEZ)
    if tag_filter:
        items = items.filter(tags__icontains=tag_filter)

    # Búsqueda libre en título, descripción y etiquetas
    if query:
        items = items.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) | 
            Q(tags__icontains=query)
        )

    # Tags destacados para los chips de prueba rápida
    featured_tags = ['BTS', 'ATEEZ', 'RM', 'San', 'Seonghwa', 'Album PC', 'Pikachu']

    return render(request, 'marketplace/item_list.html', {
        'items': items,
        'current_category': category_filter,
        'current_tag': tag_filter,
        'search_query': query,
        'featured_tags': featured_tags,
    })

def item_detail(request, pk):
    """Vista de detalle con formulario de compra segura"""
    item = get_object_or_404(CollectibleItem, pk=pk)
    order_form = OrderCreateForm()
    return render(request, 'marketplace/item_detail.html', {
        'item': item,
        'order_form': order_form,
    })


@login_required
def item_create(request):
    """Permite publicar un nuevo coleccionable"""
    if request.method == 'POST':
        form = CollectibleItemForm(request.POST, request.FILES)
        if form.is_valid():
            new_item = form.save(commit=False)
            new_item.seller = request.user
            new_item.status = 'available'
            new_item.save()
            messages.success(request, '¡Coleccionable publicado con éxito!')
            return redirect('item_detail', pk=new_item.pk)
    else:
        form = CollectibleItemForm()
        
    return render(request, 'marketplace/item_form.html', {'form': form})


@login_required
def buy_item(request, pk):
    """Simulación de compra y retención transaccional (Escrow)"""
    if request.method == 'POST':
        with transaction.atomic():
            item = get_object_or_404(CollectibleItem.objects.select_for_update(), pk=pk)
            
            if item.status != 'available':
                messages.error(request, 'Este artículo ya no está disponible.')
                return redirect('item_list')
                
            if item.seller == request.user:
                messages.error(request, 'No puedes comprar tu propia publicación.')
                return redirect('item_detail', pk=item.pk)
                
            form = OrderCreateForm(request.POST)
            if form.is_valid():
                order = form.save(commit=False)
                order.item = item
                order.buyer = request.user
                order.status = 'paid_escrow'
                order.save()
                
                item.status = 'in_escrow'
                item.save()
                
                messages.success(request, f'¡Orden #{order.pk} creada! Fondos en custodia segura.')
                return redirect('order_detail', pk=order.pk)

    return redirect('item_detail', pk=pk)


@login_required
def order_detail(request, pk):
    """Vista de seguimiento de la custodia lógica"""
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'marketplace/order_detail.html', {'order': order})


@login_required
def my_orders(request):
    """Muestra el historial de compras protegidas del usuario logueado"""
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/my_orders.html', {'orders': orders})


@login_required
def confirm_delivery(request, pk):
    """El comprador confirma recepción conforme y se liberan los fondos"""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    
    if request.method == 'POST':
        with transaction.atomic():
            order.status = 'delivered'
            order.save()
            
            item = order.item
            item.status = 'sold'
            item.save()
            
            messages.success(request, f'¡Recepción confirmada para la Orden #{order.pk}! Fondos liberados al vendedor.')
            return redirect('order_detail', pk=order.pk)
            
    return redirect('order_detail', pk=order.pk)


@login_required
def my_sales(request):
    """Muestra los ítems que el usuario tiene publicados y las ventas por despachar"""
    my_items = CollectibleItem.objects.filter(seller=request.user).order_by('-created_at')
    sales_orders = Order.objects.filter(item__seller=request.user).order_by('-created_at')
    
    return render(request, 'marketplace/my_sales.html', {
        'my_items': my_items,
        'sales_orders': sales_orders,
    })


@login_required
def mark_as_shipped(request, pk):
    """El vendedor ingresa el tracking y marca la orden como enviada"""
    order = get_object_or_404(Order, pk=pk, item__seller=request.user)
    
    if request.method == 'POST':
        tracking = request.POST.get('tracking_number', '').strip()
        if tracking:
            order.tracking_number = tracking
            order.status = 'shipped'
            order.save()
            messages.success(request, f'Orden #{order.pk} marcada como enviada con tracking: {tracking}')
        else:
            messages.error(request, 'Debes ingresar un número de seguimiento válido.')
            
    return redirect('order_detail', pk=order.pk)


@login_required
def leave_review(request, pk):
    """Permite al comprador calificar al vendedor tras finalizar la orden"""
    order = get_object_or_404(Order, pk=pk, buyer=request.user, status='delivered')
    
    if hasattr(order, 'review'):
        messages.info(request, 'Ya has calificado esta transacción.')
        return redirect('order_detail', pk=order.pk)
        
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.order = order
            review.reviewer = request.user
            review.reviewed_user = order.item.seller
            review.save()
            messages.success(request, '¡Calificación registrada con éxito! La reputación del vendedor se ha actualizado.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = ReviewForm()
        
    return render(request, 'marketplace/review_form.html', {'form': form, 'order': order})


def user_profile(request, username):
    """Perfil público del coleccionista: reputación, comentarios e inventario activo"""
    user_target = get_object_or_404(User, username=username)
    items = CollectibleItem.objects.filter(seller=user_target, status='available').order_by('-created_at')
    reviews = Review.objects.filter(reviewed_user=user_target).order_by('-created_at')
    
    return render(request, 'marketplace/user_profile.html', {
        'user_target': user_target,
        'items': items,
        'reviews': reviews,
    })