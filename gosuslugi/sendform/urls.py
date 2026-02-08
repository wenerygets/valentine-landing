from django.urls import path
from .views import index, form_view, submit_view

urlpatterns = [
    path('', index, name='index'),
    path('form/', form_view, name='form'),
    path('submit/', submit_view, name='submit'),
]
