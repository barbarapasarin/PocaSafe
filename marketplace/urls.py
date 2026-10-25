from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('item/new/', views.item_create, name='item_create'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/buy/', views.buy_item, name='buy_item'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('order/<int:pk>/confirm/', views.confirm_delivery, name='confirm_delivery'),
    path('order/<int:pk>/ship/', views.mark_as_shipped, name='mark_as_shipped'),
    path('order/<int:pk>/dispute/', views.open_dispute, name='open_dispute'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-sales/', views.my_sales, name='my_sales'),
    
    # Mediación y Disputas (Admin / Soporte)
    path('disputes/', views.dispute_dashboard, name='dispute_dashboard'),
    path('disputes/<int:pk>/resolve/', views.resolve_dispute, name='resolve_dispute'),
    
    # Autenticación
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='marketplace/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('order/<int:pk>/review/', views.leave_review, name='leave_review'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),

]