from django.contrib import admin

from models import Task, Profile, AdminProfile, Answer

admin.site.register(Task)
admin.site.register(Profile)
admin.site.register(AdminProfile)
admin.site.register(Answer)
