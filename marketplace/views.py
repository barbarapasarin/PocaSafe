from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import CollectibleItem, Order
from .forms import CollectibleItemForm, OrderCreateForm, RegisterForm
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required

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
                order.item.status = 'available'  # El ítem vuelve a estar disponible o se descarta
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
            login(request, user)  # Inicia sesión automáticamente tras registrarse
            messages.success(request, f'¡Bienvenida a PocaSafe, {user.username}!')
            return redirect('item_list')
    else:
        form = RegisterForm()

    return render(request, 'marketplace/register.html', {'form': form})

def item_list(request):
    """Vista principal: Catálogo de ítems disponibles"""
    category_filter = request.GET.get('category')
    items = CollectibleItem.objects.all().order_by('-created_at')
    
    if category_filter:
        items = items.filter(category=category_filter)
        
    return render(request, 'marketplace/item_list.html', {
        'items': items,
        'current_category': category_filter,
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
        # select_for_update bloquea la fila en la BD para evitar compras concurrentes
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
                order.status = 'paid_escrow'  # Fondos retenidos bajo custodia
                order.save()
                
                # Actualizar el ítem para que nadie más lo compre
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
            # Actualizar estado de la orden
            order.status = 'delivered'
            order.save()
            
            # El ítem pasa a vendido definitivamente
            item = order.item
            item.status = 'sold'
            item.save()
            
            messages.success(request, f'¡Recepción confirmada para la Orden #{order.pk}! Fondos liberados al vendedor.')
            return redirect('order_detail', pk=order.pk)
            
    return redirect('order_detail', pk=order.pk)

@login_required
def my_sales(request):
    """Muestra los ítems que el usuario tiene publicados y las ventas por despachar"""
    # Ítems que el usuario tiene en venta o ya vendidos
    my_items = CollectibleItem.objects.filter(seller=request.user).order_by('-created_at')
    
    # Órdenes donde el usuario es el vendedor
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