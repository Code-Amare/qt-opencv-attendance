from django.urls import path

from .views import (
    CheckResetPasswordRequestView,
    ContactResponseView,
    ForgotPasswordRequestView,
    GoogleAuthView,
    GUILoginView,
    LoginView,
    LoginViaLinkView,
    LogoutView,
    MeView,
    RefreshTokenView,
    ResetPasswordView,
    VerifyUserView,
    RegisterView,
    EditProfileView,
)

urlpatterns = [
    # Session
    path("<int:user_id>/", EditProfileView.as_view()),
    path("me/", MeView.as_view(), name="me"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view()),
    # Login
    path("login/", LoginView.as_view(), name="login"),
    path("login/verify/", VerifyUserView.as_view(), name="login-verify"),
    path("login/gui/", GUILoginView.as_view(), name="login-gui"),
    path("login/email/<str:code>/", LoginViaLinkView.as_view(), name="login-email"),
    path("auth/google/", GoogleAuthView.as_view(), name="auth-google"),
    # Passwords
    path(
        "forgot-password/", ForgotPasswordRequestView.as_view(), name="forgot-password"
    ),
    path(
        "reset-password/check/",
        CheckResetPasswordRequestView.as_view(),
        name="reset-password-check",
    ),
    path(
        "reset-password/<str:code>/", ResetPasswordView.as_view(), name="reset-password"
    ),
    # Contact
    path("contact/", ContactResponseView.as_view(), name="contact"),
]
