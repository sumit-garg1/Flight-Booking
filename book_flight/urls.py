from django.urls import path
from . import views

urlpatterns = [
    path('book/<int:offer_id>/', views.book_flight, name='book_flight'),
    path("traveler/<int:offer_id>/", views.traveler_form_view, name="traveler_form"),

]