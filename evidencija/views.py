from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest
from .models import Gradiliste, Dogadjaj, Dopis
from .forms import DogadjajForm, DopisForm, GradilisteForm
from datetime import date, datetime
from django.db.models import Min, Max, Prefetch

def due_badge(dopis, ball_on_us, dogadjaj_status=None):
    """
    Vraća (cls, label) za prikaz roka dopisa.
    - Ako je događaj zatvoren -> nema 'kasni'
    - Ako dopis ima status i nije 'open' -> nema 'kasni'
    - Ako nije na nama potez ili nema roka -> nema 'kasni'
    """
    if dogadjaj_status == "closed":
        return "bg-muted", "—"
    if hasattr(dopis, "status") and dopis.status in ("answered", "closed"):
        return "bg-muted", "—"
    if not ball_on_us or not getattr(dopis, "razuman_rok", None):
        return "bg-muted", "—"

    days = (dopis.razuman_rok - timezone.localdate()).days
    if days < 0:
        return "bg-red", f"Kasni {abs(days)} d"
    elif days <= 14:
        return "bg-yellow", f"{days} d do roka"
    else:
        return "bg-green", f"{days} d do roka"

def gradiliste_list(request):
    gradilista = Gradiliste.objects.all()
    return render(request, "evidencija/gradiliste_list.html", {"gradilista": gradilista})

def gradiliste_create(request):
    if request.method == "POST":
        form = GradilisteForm(request.POST)
        if form.is_valid():
            g = form.save()
            return redirect("dogadjaj_list", gradiliste_id=g.id)
    else:
        form = GradilisteForm()
    return render(request, "evidencija/form.html", {"title": "Novo gradilište", "form": form})

from datetime import datetime  # ako već nije uvezeno

def dogadjaj_list(request, gradiliste_id):
    g = get_object_or_404(Gradiliste, pk=gradiliste_id)

    # Učitaj sve događaje za gradilište (možeš dodati ordering po potrebi)
    dogadjaji = Dogadjaj.objects.filter(gradiliste=g).order_by("broj", "id")

    rows = []
    for d in dogadjaji:
        # zadnji dopis i tko je na potezu
        last = d.dopisi.order_by("-poslano", "-id").first()
        ball_on_us = False
        if last:
            ball_on_us = (getattr(last, "vrsta", None) == "incoming")

        # dopisi za prikaz u "skrivenoj" podtablici
        dopisi = []
        for dp in d.dopisi.all().order_by("broj", "id"):
            cls, label = due_badge(dp, ball_on_us, d.status)
            dopisi.append((dp, cls, label))

        # klasa za bojanje reda događaja (samo ako nije zatvoren)
        event_cls = ""
        if d.status != "closed" and ball_on_us and last and getattr(last, "razuman_rok", None):
            days = (last.razuman_rok - timezone.localdate()).days
            if days < 0:
                event_cls = "table-danger"   # crveno
            elif days <= 14:
                event_cls = "table-warning"  # narančasto/žuto
            else:
                event_cls = ""               # bez boje

        rows.append((d, dopisi, ball_on_us, last, event_cls))

    ctx = {
        "gradiliste": g,
        "rows": rows,
        "today": timezone.localdate(),
        # zadrži i postojeće varijable za sort ako ih koristiš (sort, d_sort, …)
    }
    return render(request, "evidencija/dogadjaj_list.html", ctx)

def dogadjaj_detail(request, gradiliste_id, pk):
    d = get_object_or_404(Dogadjaj, pk=pk, gradiliste_id=gradiliste_id)

    # zadnji dopis i tko je na potezu
    last = d.dopisi.order_by("-poslano", "-id").first()
    ball_on_us = False
    if last:
        # ako je zadnji bio 'incoming' (ulazni) -> na nama je potez
        ball_on_us = (getattr(last, "vrsta", None) == "incoming")

    # složi redove za tablicu dopisa: (dopis, cls, label)
    rows = []
    for dp in d.dopisi.all().order_by("broj", "id"):  # prilagodi ako sortiraš drugačije
        cls, label = due_badge(dp, ball_on_us, d.status)
        rows.append((dp, cls, label))

    ctx = {
        "dogadjaj": d,
        "ball_on_us": ball_on_us,
        "last": last,
        "rows": rows,
    }
    return render(request, "evidencija/dogadjaj_detail.html", ctx)

# ---------- FORME (bez admina) ----------
def dogadjaj_create(request, gradiliste_id):
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    if request.method == "POST":
        form = DogadjajForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.gradiliste = gradiliste
            obj.save()
            return redirect("dogadjaj_detail", gradiliste_id=gradiliste.id, pk=obj.id)
    else:
        form = DogadjajForm()
    return render(request, "evidencija/form.html", {"title": f"Novi događaj – {gradiliste.naziv}", "form": form})

def dogadjaj_update(request, gradiliste_id, pk):
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    obj = get_object_or_404(Dogadjaj, pk=pk, gradiliste=gradiliste)
    if request.method == "POST":
        form = DogadjajForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("dogadjaj_list", gradiliste_id=gradiliste.id)
    else:
        form = DogadjajForm(instance=obj)
    return render(request, "evidencija/form.html", {"title": f"Uredi događaj – {gradiliste.naziv}", "form": form})

def dopis_create_for_event(request, gradiliste_id, dogadjaj_id):
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    dogadjaj = get_object_or_404(Dogadjaj, pk=dogadjaj_id, gradiliste=gradiliste)

    if request.method == "POST":
        form = DopisForm(request.POST)
        if form.is_valid():
            dopis = form.save(commit=False)
            dopis.dogadjaj = dogadjaj   # vežemo na odabrani događaj, ignorira se što god je u formi
            dopis.save()
            return redirect("dogadjaj_detail", gradiliste_id=gradiliste.id, pk=dogadjaj.id)
    else:
        # ako tvoj DopisForm ima polje 'dogadjaj', bolje ga maknuti iz forme (exclude) ili ga ostaviti readonly
        form = DopisForm(initial={"dogadjaj": dogadjaj})

    return render(
        request,
        "evidencija/form.html",
        {"title": f"Novi dopis – {dogadjaj.naziv}", "form": form},
    )

def dopis_update(request, gradiliste_id, pk):
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    dopis = get_object_or_404(Dopis, pk=pk)
    # sigurnosna provjera da dopis pripada gradilištu:
    if dopis.dogadjaj.gradiliste_id != gradiliste.id:
        return redirect("dogadjaj_list", gradiliste_id=gradiliste.id)
    if request.method == "POST":
        form = DopisForm(request.POST, instance=dopis)
        if form.is_valid():
            form.save()
            return redirect("dogadjaj_list", gradiliste_id=gradiliste.id)
    else:
        form = DopisForm(instance=dopis)
    return render(request, "evidencija/form.html", {"title": f"Uredi dopis – {gradiliste.naziv}", "form": form})