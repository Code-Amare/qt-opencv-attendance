from django.urls import path
from .views import BulkUserCreateView, RecognitionMapView, UsersListView

urlpatterns = [
    path("", UsersListView.as_view()),
    path("create/bulk/", BulkUserCreateView.as_view()),
    path("recognition-map/", RecognitionMapView.as_view()),
]
