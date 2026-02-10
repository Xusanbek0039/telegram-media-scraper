from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 1. Dashboard
    path('boshqaruv/', views.home_view, name='home'),

    # 2. Users
    path('boshqaruv/foydalanuvchilar/', views.users_view, name='users'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/premium/', views.user_toggle_premium, name='user_toggle_premium'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/ban/', views.user_toggle_ban, name='user_toggle_ban'),
    path('boshqaruv/foydalanuvchilar/<int:pk>/', views.user_detail_view, name='user_detail'),

    # 3. Media & Music
    path('boshqaruv/media/', views.media_view, name='media'),
    path('boshqaruv/music/', views.music_view, name='music'),

    # 4. Ads & Marketing
    path('boshqaruv/reklama/', views.broadcast_view, name='broadcast'),
    path('boshqaruv/kampaniyalar/', views.ads_view, name='ads'),

    # 5. Premium / Monetization
    path('boshqaruv/premium/', views.premium_view, name='premium'),

    # 6. Settings
    path('boshqaruv/sozlamalar/', views.settings_view, name='settings'),

    # 7. Analytics
    path('boshqaruv/analytics/', views.analytics_view, name='analytics'),

    # 8. Logs
    path('boshqaruv/logs/', views.logs_view, name='logs'),
    path('boshqaruv/logs/<int:pk>/resolve/', views.resolve_error, name='resolve_error'),

    # Legacy
    path('boshqaruv/tarix/', views.history_view, name='history'),

    # API
    path('api/stats/', views.api_stats, name='api_stats'),
]
