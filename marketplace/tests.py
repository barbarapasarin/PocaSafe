from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import CollectibleItem, Order, Profile, Review, EscrowAuditLog


class EscrowTransactionTestCase(TestCase):
    def setUp(self):
        # 1. Crear usuarios de prueba (vendedor y comprador)
        self.seller = User.objects.create_user(username='vendedora_test', password='password123')
        self.buyer = User.objects.create_user(username='compradora_test', password='password123')

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

        order.tracking_number = 'STARKEN-9847123'
        order.status = 'shipped'
        order.save()
        self.assertEqual(order.status, 'shipped')

        order.status = 'delivered'
        order.save()
        self.item.status = 'sold'
        self.item.save()

        self.assertEqual(order.status, 'delivered')
        self.assertEqual(self.item.status, 'sold')

        Review.objects.create(
            order=order,
            reviewer=self.buyer,
            reviewed_user=self.seller,
            rating=5,
            comment='Excelente estado, bien protegida en toploader y rápido envío.'
        )

        updated_seller_profile = Profile.objects.get(pk=self.seller_profile.pk)
        self.assertEqual(updated_seller_profile.total_reviews, 1)
        self.assertEqual(updated_seller_profile.reputation_score, Decimal('5.00'))

    def test_checkout_saves_courier_data_and_blocks_self_purchase(self):
        """Verifica bloqueo de auto-compra y auto-guardado de RUT/teléfono en el perfil al comprar"""
        buy_url = reverse('buy_item', args=[self.item.pk])

        # 1. El vendedor intenta comprar su propio ítem -> Debe ser bloqueado
        self.client.login(username='vendedora_test', password='password123')
        self.client.post(buy_url, {
            'shipping_name': 'Vendedora',
            'shipping_address': 'Calle Falsa 123',
        })
        item_after_self = CollectibleItem.objects.get(pk=self.item.pk)
        self.assertEqual(item_after_self.status, 'available')
        self.assertFalse(Order.objects.filter(item=self.item).exists())
        self.client.logout()

        # 2. La compradora legítima realiza la compra -> Se crea la orden pendiente
        self.client.login(username='compradora_test', password='password123')
        self.client.post(buy_url, {
            'shipping_name': 'Bárbara Test',
            'shipping_rut': '21.111.222-3',
            'shipping_phone': '+56987654321',
            'shipping_address': 'Av. Colón 456',
            'shipping_city': 'San Bernardo',
        })

        order = Order.objects.get(item=self.item)
        self.assertEqual(order.status, 'pending')

        # 3. Pago aprobado en pasarela
        success_url = reverse('payment_success', args=[order.pk])
        self.client.get(success_url)

        item_after_pay = CollectibleItem.objects.get(pk=self.item.pk)
        buyer_profile_after_pay = Profile.objects.get(pk=self.buyer_profile.pk)
        order_after_pay = Order.objects.get(pk=order.pk)

        self.assertEqual(order_after_pay.status, 'paid_escrow')
        self.assertEqual(item_after_pay.status, 'in_escrow')
        self.assertEqual(buyer_profile_after_pay.rut, '21.111.222-3')
        self.assertEqual(buyer_profile_after_pay.phone, '+56987654321')

    def test_order_detail_restricts_unauthorized_user(self):
        """Verifica que un usuario ajeno a la orden no pueda acceder a order_detail"""
        User.objects.create_user(username='tercero_test', password='password123')
        order = Order.objects.create(
            item=self.item,
            buyer=self.buyer,
            shipping_name='Compradora Test',
            shipping_address='Av. Siempre Viva 742',
            status='paid_escrow',
        )

        self.client.login(username='tercero_test', password='password123')
        response = self.client.get(reverse('order_detail', args=[order.pk]), follow=True)
        self.assertRedirects(response, reverse('item_list'))
        self.assertContains(response, 'No tienes permiso para ver esta orden.')

    def test_ship_confirm_and_audit_log_via_views(self):
        """Prueba despacho y confirmación por vistas verificando registros en EscrowAuditLog"""
        order = Order.objects.create(
            item=self.item,
            buyer=self.buyer,
            shipping_name='Compradora Test',
            shipping_address='Sucursal Starken San Bernardo',
            status='paid_escrow',
        )
        self.item.status = 'in_escrow'
        self.item.save()

        self.client.login(username='vendedora_test', password='password123')
        self.client.post(
            reverse('mark_as_shipped', args=[order.pk]),
            {'tracking_number': 'CHX-554433'},
        )
        order_shipped = Order.objects.get(pk=order.pk)
        self.assertEqual(order_shipped.status, 'shipped')
        self.assertEqual(order_shipped.tracking_number, 'CHX-554433')
        self.client.logout()

        self.client.login(username='compradora_test', password='password123')
        self.client.post(reverse('confirm_delivery', args=[order.pk]))
        order_delivered = Order.objects.get(pk=order.pk)
        item_sold = CollectibleItem.objects.get(pk=self.item.pk)
        self.assertEqual(order_delivered.status, 'delivered')
        self.assertEqual(item_sold.status, 'sold')

        logs = EscrowAuditLog.objects.filter(order=order)
        self.assertEqual(logs.count(), 2)

    def test_dispute_refund_buyer_releases_item(self):
        """Verifica que abrir disputa congela fondos y reembolsar al comprador libera el ítem"""
        User.objects.create_user(
            username='mediadora_test',
            password='password123',
            is_staff=True,
        )
        order = Order.objects.create(
            item=self.item,
            buyer=self.buyer,
            shipping_name='Compradora Test',
            shipping_address='Av. Colón 456',
            status='shipped',
            tracking_number='STARKEN-112233',
        )
        self.item.status = 'in_escrow'
        self.item.save()

        self.client.login(username='compradora_test', password='password123')
        self.client.post(
            reverse('open_dispute', args=[order.pk]),
            {'dispute_reason': 'El paquete llegó vacío.'},
        )
        order_disputed = Order.objects.get(pk=order.pk)
        self.assertEqual(order_disputed.status, 'disputed')
        self.client.logout()

        self.client.login(username='mediadora_test', password='password123')
        self.client.post(
            reverse('resolve_dispute', args=[order.pk]),
            {
                'resolution': 'refund_buyer',
                'admin_notes': 'Se valida reclamo del comprador.',
            },
        )
        order_resolved = Order.objects.get(pk=order.pk)
        item_released = CollectibleItem.objects.get(pk=self.item.pk)
        self.assertEqual(order_resolved.status, 'cancelled')
        self.assertEqual(item_released.status, 'available')