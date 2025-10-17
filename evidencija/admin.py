from django.contrib import admin
from .models import Dogadjaj, Dopis, Biljeska, Prilog

class BiljeskaInline(admin.TabularInline):
    model = Biljeska
    extra = 0

class PrilogInline(admin.TabularInline):
    model = Prilog
    extra = 0

class DopisInline(admin.TabularInline):
    model = Dopis
    extra = 0
    fields = ('broj','vrsta','poslano','razuman_rok','status','sadrzaj')

@admin.register(Dopis)
class DopisAdmin(admin.ModelAdmin):
    list_display = ("id", 'dogadjaj', "kategorija", "rb_po_kategoriji", 'broj','vrsta','poslano','razuman_rok','status','due_badge')
    list_filter = ('dogadjaj__gradiliste', "kategorija", 'vrsta','status','razuman_rok')
    search_fields = ('broj','sadrzaj')
    ordering = ("dogadjaj__gradiliste", "kategorija", "rb_po_kategoriji", "id")

    def due_badge(self, obj):
        d = obj.days_to_due
        if d is None: return "—"
        if d < 0: return f"⚠️ Kasni {abs(d)} d"
        if d == 0: return "⏳ Rok danas"
        if d <= 2: return f"⏳ {d} d"
        return f"{d} d"
    due_badge.short_description = "Rok"

@admin.register(Dogadjaj)
class DogadjajAdmin(admin.ModelAdmin):
    list_display = ('broj','naziv','preporucena_radnja','datum')
    inlines = [DopisInline]
