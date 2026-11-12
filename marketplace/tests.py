from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import CollectibleItem, Order, Profile, Review


class EscrowTransactionTestCase(TestCase):
    def setUp(self):
        # 1. Crear usuarios de prueba (vendedor y comprador)
        self.seller = User.objects.create_user(username='vendedora_test', password='password123')
        self.buyer = User.objects.create_user(username='compradora_test', password='password123')
        
        # Guardamos las instancias en atributos para que Pylance reconozca el tipo Profile sin warnings
        self.seller_profile = Profile.objects.create(user=self.seller, city='Santiago')
        self.buyer_profile = Profile.objects.create(user=self.buyer, city='San Bernardo')

        # 2. Crear ítem de prueba disponible
        self.item = CollectibleItem.objects.create(
            seller=self.seller,
            title='Photocard BTS RM Butter',
            category='photocard',
            tags='BTS, RM, Butter',
            price=15000,
            status='available'
        )

    def test_item_default_status(self):
        """Verifica que un coleccionable inicie disponible por defecto y normalice tags"""
        self.item.clean()
        self.assertEqual(self.item.status, 'available')
        self.assertIn('Bts', self.item.tags)

    def test_escrow_lifecycle_and_reputation(self):
        """Prueba el ciclo completo: retención en custodia, envío, entrega y cálculo de reputación"""
        # Paso A: Creación de la orden con fondos en custodia y datos de courier
        order = Order.objects.create(
            item=self.item,
            buyer=self.buyer,
            shipping_name='Compradora Test',
            shipping_rut='21.345.678-9',
            shipping_phone='+56912345678',
            shipping_address='Sucursal Starken San Bernardo',
            shipping_city='San Bernardo',
            status='paid_escrow'
        )
        self.item.status = 'in_escrow'
        self.item.save()

        self.assertEqual(order.status, 'paid_escrow')
        self.assertEqual(self.item.status, 'in_escrow')
        self.assertEqual(order.shipping_rut, '21.345.678-9')

        # Paso B: Despacho por parte del vendedor
        order.tracking_number = 'STARKEN-9847123'
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
            comment='Excelente estado, bien protegida en toploader y rápido envío.'
        )
        
        # Refrescamos directamente la instancia Profile (elimina el warning de Pylance)
        self.seller_profile.refresh_from_db()
        self.assertEqual(self.seller_profile.total_reviews, 1)
        self.assertEqual(self.seller_profile.reputation_score, Decimal('5.00'))

    def test_checkout_saves_courier_data_and_blocks_self_purchase(self):
        """Verifica bloqueo de auto-compra y auto-guardado de RUT/teléfono en el perfil al comprar"""
        buy_url = reverse('buy_item', args=[self.item.pk])

        # 1. El vendedor intenta comprar su propio ítem -> Debe ser bloqueado
        self.client.login(username='vendedora_test', password='password123')
        self.client.post(buy_url, {
            'shipping_name': 'Vendedora',
            'shipping_address': 'Calle Falsa 123',
        })
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'available')
        self.assertFalse(Order.objects.filter(item=self.item).exists())
        self.client.logout()

        # 2. La compradora legítima realiza la compra con datos de courier -> Pasa a custodia y actualiza su perfil
        self.client.login(username='compradora_test', password='password123')
        self.client.post(buy_url, {
            'shipping_name': 'Bárbara Test',
            'shipping_rut': '21.111.222-3',
            'shipping_phone': '+56987654321',
            'shipping_address': 'Av. Colón 456',
            'shipping_city': 'San Bernardo',
        })
        
        self.item.refresh_from_db()
        self.buyer_profile.refresh_from_db()
        
        self.assertEqual(self.item.status, 'in_escrow')
        self.assertEqual(self.buyer_profile.rut, '21.111.222-3')
        self.assertEqual(self.buyer_profile.phone, '+56987654321')