from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JWTCookieAuthentication(JWTAuthentication):

    cookie_name = "access_token"

    def authenticate(self, request):

        access_token = request.COOKIES.get(self.cookie_name)

        if not access_token:
            return None

        try:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)

            return user, validated_token

        except (InvalidToken, TokenError):

            raise AuthenticationFailed(
                "Invalid or expired token."
            )


