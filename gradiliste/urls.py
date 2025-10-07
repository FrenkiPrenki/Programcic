# gradiliste/urls.py
from django.contrib import admin
from django.urls import path
from evidencija import views  # naše view funkcije iz app-a "evidencija"

urlpatterns = [
    # Početna → lista gradilišta
    path("", views.gradiliste_list, name="gradiliste_list"),

    # Gradilišta
    path("gradilista/novo/", views.gradiliste_create, name="gradiliste_create"),

    # Događaji unutar gradilišta
    path("gradilista/<int:gradiliste_id>/", views.dogadjaj_list, name="dogadjaj_list"),
    path("gradilista/<int:gradiliste_id>/dogadjaj/<int:pk>/", views.dogadjaj_detail, name="dogadjaj_detail"),

    # Admin (ako koristiš)
    path("admin/", admin.site.urls),
]
