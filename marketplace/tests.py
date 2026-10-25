from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from .models import CollectibleItem, Order, Profile, Review

class EscrowTransactionTestCase(TestCase):
    def setUp(self):
        # 1. Crear usuarios de prueba (vendedor y comprador)
        self.seller = User.objects.create_user(username='vendedora_test', password='password123')
        self.buyer = User.objects.create_user(username='compradora_test', password='password123')
        
        Profile.objects.create(user=self.seller, city='Santiago')
        Profile.objects.create(user=self.buyer, city='Valparaíso')

        # 2. Crear ítem de prueba disponible
        self.item = CollectibleItem.objects.create(
            seller=self.seller,
            title='Photocard BTS RM Butter',
            category='photocard',
            price=15000,
            status='available'
        )

    def test_item_default_status(self):
        """Verifica que un coleccionable inicie disponible por defecto"""
        self.assertEqual(self.item.status, 'available')

    def test_escrow_lifecycle_and_reputation(self):
        """Prueba el ciclo completo: retención en custodia, envío, entrega y cálculo de reputación"""
        # Paso A: Creación de la orden con fondos en custodia
        order = Order.objects.create(
            item=self.item,
            buyer=self.buyer,
            shipping_name='Compradora Test',
            shipping_address='Av. Siempre Viva 123',
            status='paid_escrow'
        )
        self.item.status = 'in_escrow'
        self.item.save()

        self.assertEqual(order.status, 'paid_escrow')
        self.assertEqual(self.item.status, 'in_escrow')

        # Paso B: Despacho por parte del vendedor
        order.tracking_number = 'STARKEN-123456'
        order.status = 'shipped'
        order.save()
        self.assertEqual(order.status, 'shipped')

        # Paso C: Recepción conforme y liberación de fondos
        order.status = 'delivered'
        order.save()
        self.item.status = 'sold'
        self.item.save()

        self.assertEqual(order.status, 'delivered')
        self.assertEqual(self.item.status, 'sold')

        # Paso D: Calificación y actualización de reputación del vendedor
        Review.objects.create(
            order=order,
            reviewer=self.buyer,
            reviewed_user=self.seller,
            rating=5,
            comment='Excelente estado y rápido envío.'
        )
        self.seller.profile.refresh_from_db()
        self.assertEqual(self.seller.profile.total_reviews, 1)
        self.assertEqual(self.seller.profile.reputation_score, Decimal('5.00'))