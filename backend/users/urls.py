from django.urls import path
from .views import (
    BulkUserCreateView,
    RecognitionMapView,
    UsersListView,
    LoginView,
    SaveFaceEmbeddingView,
)

urlpatterns = [
    path("", UsersListView.as_view()),
    path("create/bulk/", BulkUserCreateView.as_view()),
    path("recognition-map/", RecognitionMapView.as_view()),
    path("login/", LoginView.as_view()),
    path("face-embedding/add/", SaveFaceEmbeddingView.as_view()),
]
