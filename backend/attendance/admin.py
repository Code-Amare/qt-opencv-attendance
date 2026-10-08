from django.contrib import admin
from .models import AttendanceSession, Attendance

admin.site.register([Attendance, AttendanceSession])
