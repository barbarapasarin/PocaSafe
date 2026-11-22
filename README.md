# PocaSafe

Marketplace C2C enfocado en la compraventa segura de coleccionables (photocards de K-Pop y cartas TCG) mediante un sistema de **Custodia Lógica (Escrow)**, privacidad progresiva de datos de despacho, resolución de disputas, reputación de usuarios y registro de auditoría.

## Características principales

- **Custodia lógica (Escrow):** Retención lógica de fondos y control de estados de la orden (`pending` → `paid_escrow` → `shipped` → `delivered`, además de `disputed` y `cancelled`) protegiendo la disponibilidad del ítem (`available` → `in_escrow` → `sold`).
- **Integración de pagos con respaldo:** Integración con Mercado Pago SDK (Checkout Pro) y flujo de respaldo/simulación local (`order_sandbox_pay`) cuando no se utiliza la pasarela externa.
- **Privacidad progresiva para envíos:** Los datos de despacho por courier (nombre, RUT, teléfono, dirección/sucursal y comuna/ciudad) se auto-completan desde el perfil y se habilitan para el vendedor una vez que los fondos entran en custodia.
- **Mediación y disputas:** Flujo para que el comprador abra disputas congelando la orden y para que un mediador (`staff`) resuelva a favor del vendedor (liberar fondos / ítem vendido) o del comprador (cancelar orden / ítem disponible nuevamente).
- **Reputación y reseñas:** Cálculo automático del puntaje promedio de reputación y total de evaluaciones a partir de las reseñas en órdenes entregadas.
- **Bitácora de auditoría (`EscrowAuditLog`):** Registro cronológico de eventos relevantes en cada orden (creación, pago en custodia, despacho con tracking, confirmación de recepción, disputas y resoluciones).

## Stack tecnológico

- **Backend:** Python, Django 6.1
- **Base de datos:** PostgreSQL en producción (`dj-database-url`) y SQLite en desarrollo local
- **Almacenamiento multimedia:** Cloudinary (`django-cloudinary-storage`) y archivos estáticos con WhiteNoise
- **Frontend:** Plantillas Django con Bulma CSS
- **Despliegue:** Render
