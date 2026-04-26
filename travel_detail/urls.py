from django.urls import path,include
from . import views
urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('download-ticket/<str:pnr>/', views.download_ticket, name='download_ticket'),  # ADD THIS LINE
    path('booking/<str:pnr>/', views.booking_detail, name='booking_detail'), 
]