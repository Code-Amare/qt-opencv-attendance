from django.urls import path

from .views import (
    BulkUserCreateView,
    RecognitionMapView,
    UsersListView,
    LoginView,
    LoginViaLinkView,
    SaveFaceEmbeddingView,
    RecognitionMapFileView,
    GoogleAuthView,
    ContactResponseView,
    ForgotPasswordRequestView,
    CheckResetPasswordRequestView,
    ResetPasswordView,
    MeView,
    RefreshTokenView,
    VerifyUserView,
    GUILoginView,
)

urlpatterns = [
    path("me/", MeView.as_view()),
    path("token/refresh/", RefreshTokenView.as_view()),
    path("create/bulk/", BulkUserCreateView.as_view()),
    path("recognition-map/", RecognitionMapView.as_view()),
    path("face-embedding/add/<int:user_id>/", SaveFaceEmbeddingView.as_view()),
    path("face-embedding/download/", RecognitionMapFileView.as_view()),
    path("login/", LoginView.as_view()),
    path("login/verify/", VerifyUserView.as_view()),
    path("login/gui/", GUILoginView.as_view()),
    path("login/email/<str:code>/", LoginViaLinkView.as_view()),
    path("auth/google/", GoogleAuthView.as_view()),
    path("forgot-password/", ForgotPasswordRequestView.as_view()),
    path("reset-password/check/", CheckResetPasswordRequestView.as_view()),
    path("reset-password/<str:code>/", ResetPasswordView.as_view()),
    path("contact/", ContactResponseView.as_view()),
    path("", UsersListView.as_view()),
]
