from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User

# 1. Perfil / Datos de usuario
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rut = models.CharField(max_length=12, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    total_reviews = models.PositiveIntegerField(default=0)
    reputation_score = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('5.00'))

    def __str__(self):
        return self.user.username


# 2. Ítem Coleccionable (Stock único)
class CollectibleItem(models.Model):
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('in_escrow', 'En Custodia / En Proceso'),
        ('sold', 'Vendido / Entregado'),
    ]
    
    CATEGORY_CHOICES = [
        ('photocard', 'Photocard K-Pop'),
        ('tcg', 'Carta TCG'),
        ('other', 'Otro Coleccionable'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items_for_sale')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='photocard')
    price = models.PositiveIntegerField(help_text="Precio en CLP")
    image = models.ImageField(upload_to='collectibles/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - ${self.price} ({self.status})"


# 3. Orden con Custodia Lógica (Escrow)
class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pendiente de Pago'),
        ('paid_escrow', 'Pagada / Fondos en Custodia'),
        ('shipped', 'Enviado con Courier'),
        ('delivered', 'Recibido Conforme / Pago Liberado'),
        ('disputed', 'En Mediación / Disputa'),
        ('cancelled', 'Cancelado / Reembolsado'),
    ]

    item = models.OneToOneField(CollectibleItem, on_delete=models.PROTECT, related_name='order')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    shipping_name = models.CharField(max_length=150)
    shipping_address = models.CharField(max_length=255)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='paid_escrow')  # <-- Corregido ORDER_STATUS
    
    # Nuevos campos para mediación y disputas
    dispute_reason = models.TextField(blank=True, null=True)
    dispute_created_at = models.DateTimeField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True, help_text="Resolución del mediador/administrador")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orden #{self.pk} - {self.item.title} ({self.status})"

    from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

# Agrega este modelo al final de marketplace/models.py
class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    reviewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación de 1 a 5 estrellas"
    )
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalcular automáticamente el promedio de reputación del usuario evaluado
        profile = self.reviewed_user.profile
        avg_score = Review.objects.filter(reviewed_user=self.reviewed_user).aggregate(Avg('rating'))['rating__avg']
        if avg_score is not None:
            profile.reputation_score = round(Decimal(avg_score), 2)
            profile.total_reviews = Review.objects.filter(reviewed_user=self.reviewed_user).count()
            profile.save()

    def __str__(self):
        return f"Calificación de {self.reviewer.username} a {self.reviewed_user.username} ({self.rating}★)"
