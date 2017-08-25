from django.conf.urls import url

from main import views

urlpatterns = [
    url(r'^$',                            views.index),
    url(r'^profile/$',                    views.profile),
    url(r'^admin_panel/$',                views.admin_panel),
    url(r'^create_task/$',                views.create_task),
    url(r'^edit_task/(?P<task_id>\d+)/$', views.edit_task),
    url(r'^users/$',                      views.users),
    url(r'^money/$',                      views.money),
    url(r'^logout/$',                     views.logout),

    # API methods

    url(r'^api/get_balance/$', views.api_get_balance),
    url(r'^api/deposit/$',     views.api_deposit),
    url(r'^api/withdraw/$',    views.api_withdraw),
]
