from django.contrib import admin
from .models import Profile, CollectibleItem, Order

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'city', 'reputation_score')

@admin.register(CollectibleItem)
class CollectibleItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'status', 'seller', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('title', 'description', 'seller__username')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'buyer', 'status', 'tracking_number', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('item__title', 'buyer__username', 'shipping_name', 'tracking_number')
    readonly_fields = ('created_at', 'updated_at', 'dispute_created_at')
    fieldsets = (
        ('Detalles de la Orden', {
            'fields': ('item', 'buyer', 'status')
        }),
        ('Información de Envío', {
            'fields': ('shipping_name', 'shipping_address', 'tracking_number')
        }),
        ('Gestión de Disputas y Mediación', {
            'fields': ('dispute_reason', 'dispute_created_at', 'admin_notes')
        }),
        ('Marcas de Tiempo', {
            'fields': ('created_at', 'updated_at')
        }),
    )