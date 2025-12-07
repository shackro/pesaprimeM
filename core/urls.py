from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path("switch-currency/", views.switch_currency, name="switch_currency"),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('contact/success/', views.contact_success_view, name='contact_success'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('faq/', views.faq_view, name='faq'),
    path('newsletter/', views.newsletter_view, name='newsletter'),
    path('number-carousel/', views.number_carousel_view, name='number_carousel'),
]