from django.urls import path
from .views import BulkUserCreateView, RecognitionMapView



urlpatterns = [
    path('create/bulk/', BulkUserCreateView.as_view()),
    path('recognition-map/', RecognitionMapView.as_view()),
]