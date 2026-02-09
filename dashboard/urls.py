from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('boshqaruv/', views.home_view, name='home'),
    path('boshqaruv/foydalanuvchilar/', views.users_view, name='users'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/premium/', views.user_toggle_premium, name='user_toggle_premium'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/ban/', views.user_toggle_ban, name='user_toggle_ban'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('boshqaruv/reklama/', views.broadcast_view, name='broadcast'),
    path('boshqaruv/tarix/', views.history_view, name='history'),
]
