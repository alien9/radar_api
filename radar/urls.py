from django.contrib import admin
from django.urls import path
from api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.api_login),
    path('logout/', views.api_logout),
    path('signup/', views.signup),
    path('renew/', views.renew),
    path('map/', views.map),
    path('', views.map),
    path('validate/<signup_token>/', views.validate),
    path('getLocais', views.get_locais),
    path('getLocais/', views.get_locais),
    path('getLocais/<d>/', views.get_locais_por_data),
    path('getTrajetos/<data>/<codigo>/', views.get_trajetos),
    path('getTrajetos/<viagem_id>/', views.get_trajetos_por_viagem),
    path('getViagens/<data>/<codigo>/', views.get_viagens),
    path('getDetalhes/<codigo>/', views.get_detalhes),
    path('getContagens/<data>/<codigo>/', views.get_contagens),
    path('getVelocidades/<data>/<codigo>/', views.get_velocidades),
    path('getDatas/', views.get_datas),
]
