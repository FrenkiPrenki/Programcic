# evidencija/admin.py
from django.contrib import admin
from .models import Gradiliste, Dogadjaj, Dopis

# --- Inlines ---
class DopisInline(admin.TabularInline):
    model = Dopis
    extra = 0
    fields = ("kategorija", "oznaka", "vrsta", "poslano", "razuman_rok")
    ordering = ("poslano", "id")
    show_change_link = True

# --- Admini ---
@admin.register(Gradiliste)
class GradilisteAdmin(admin.ModelAdmin):
    list_display = ("id", "naziv")
    search_fields = ("naziv",)
    ordering = ("id",)

@admin.register(Dogadjaj)
class DogadjajAdmin(admin.ModelAdmin):
    list_display = ("id", "gradiliste", "broj", "naziv", "status", "preporucena_radnja", "datum")
    list_filter  = ("gradiliste", "status", "preporucena_radnja")
    search_fields = ("broj", "naziv", "opis")
    ordering = ("gradiliste", "broj", "id")
    inlines = [DopisInline]

@admin.register(Dopis)
class DopisAdmin(admin.ModelAdmin):
    list_display  = ("id", "dogadjaj", "kategorija", "oznaka", "vrsta", "poslano", "razuman_rok")
    list_filter   = ("dogadjaj__gradiliste", "kategorija", "vrsta", "poslano")
    search_fields = ("broj", "oznaka", "sadrzaj")
    ordering      = ("dogadjaj__gradiliste", "dogadjaj", "kategorija", "oznaka", "poslano", "id")
    autocomplete_fields = ("dogadjaj",)
