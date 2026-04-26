from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Home points to global home.html
    path('airport-routes/', views.airport_routes_view, name='airport_routes'),
]
