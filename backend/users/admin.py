from django.contrib import admin
from .models import User, EmailLoginLink, EmailLoginCode, ForgotPasswordRequest

admin.site.register([User, EmailLoginLink, EmailLoginCode, ForgotPasswordRequest])
