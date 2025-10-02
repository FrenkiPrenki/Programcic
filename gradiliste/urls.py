from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from evidencija.views import (
    dogadjaj_list, dogadjaj_detail,
    dogadjaj_create, dogadjaj_update,
    dopis_create, dopis_update,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", dogadjaj_list, name="dogadjaj_list"),
    path("dogadjaj/<int:pk>/", dogadjaj_detail, name="dogadjaj_detail"),
    path("dogadjaj/novi/", dogadjaj_create, name="dogadjaj_create"),
    path("dogadjaj/<int:pk>/uredi/", dogadjaj_update, name="dogadjaj_update"),

    path("dopis/novi/", dopis_create, name="dopis_create"),
    path("dopis/novi/<int:dogadjaj_id>/", dopis_create, name="dopis_create_for_event"),
    path("dopis/<int:pk>/uredi/", dopis_update, name="dopis_update"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
