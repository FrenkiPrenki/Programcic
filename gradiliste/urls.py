from django.contrib import admin
from django.urls import path
from evidencija import views

urlpatterns = [
    path("", views.gradiliste_list, name="gradiliste_list"),
    path("gradilista/novo/", views.gradiliste_create, name="gradiliste_create"),

    path("gradilista/<int:gradiliste_id>/", views.dogadjaj_list, name="dogadjaj_list"),
    path("gradilista/<int:gradiliste_id>/dogadjaj/<int:pk>/", views.dogadjaj_detail, name="dogadjaj_detail"),

    # ⬇⬇⬇ DODANO
    path("gradilista/<int:gradiliste_id>/dogadjaj/novo/", views.dogadjaj_create, name="dogadjaj_create"),
    path("gradilista/<int:gradiliste_id>/dogadjaj/<int:pk>/uredi/", views.dogadjaj_update, name="dogadjaj_update"),
    path(
    "gradilista/<int:gradiliste_id>/dogadjaj/<int:dogadjaj_id>/dopis/novo/",
    views.dopis_create_for_event,
    name="dopis_create_for_event",
),
    path("gradilista/<int:gradiliste_id>/dopis/<int:pk>/uredi/", views.dopis_update, name="dopis_update"),

    path("admin/", admin.site.urls),
    # ... ostale rute iznad ...
    path(
    "gradilista/<int:gradiliste_id>/dogadjaj/<int:dogadjaj_id>/dopis/novo/",
    views.dopis_create_for_event,
    name="dopis_create_for_event",
    ),
# ... update ruta ostaje ista:
    path(
    "gradilista/<int:gradiliste_id>/dopis/<int:pk>/uredi/",
    views.dopis_update,
    name="dopis_update",
    ),
]
