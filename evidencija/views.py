from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest
from .models import Gradiliste, Dogadjaj, Dopis
from .forms import DogadjajForm, DopisForm, GradilisteForm
from datetime import date, datetime
from django.db.models import Min, Max, Prefetch

from django.utils import timezone

def due_badge(dopis, _ball_on_us_ignored, dogadjaj_status=None):
    """
    Vrati (bootstrap_klasa, label) za badge.
    Klasa je jedna od: text-bg-danger | text-bg-warning | text-bg-success | text-bg-secondary
    """
    # Dogadjaj zatvoren -> sivo
    if dogadjaj_status == "closed":
        return "text-bg-secondary", "—"

    # Ako dopis još ima svoje status polje i nije 'open' -> sivo
    if hasattr(dopis, "status") and getattr(dopis, "status", "open") in ("answered", "closed"):
        return "text-bg-secondary", "—"

    # Ako nema roka ili nije ulazni -> sivo
    if getattr(dopis, "vrsta", None) != "incoming" or not getattr(dopis, "razuman_rok", None):
        return "text-bg-secondary", "—"

    # Izračun roka
    days = (dopis.razuman_rok - timezone.localdate()).days
    if days < 0:
        return "text-bg-danger", f"Kasni {abs(days)} d"
    elif days <= 14:
        return "text-bg-warning", f"{days} d do roka"
    else:
        return "text-bg-success", f"{days} d do roka"

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
        ball_on_us = bool(last and getattr(last, "vrsta", None) == "incoming")
        d_status = getattr(d, "status", None)

        dopisi = []
        for dp in d.dopisi.all().order_by("broj", "id"):
            cls, label = due_badge(dp, ball_on_us, d_status)  # <-- pass status
            dopisi.append((dp, cls, label))
         
         # BOJANJE GLAVNOG REDA DOGAĐAJA — SAMO PO ZADNJEM DOPISU
        event_cls = ""
        d_status = getattr(d, "status", "open")  # sigurno čitanje (default 'open')

        if (
            last
            and d_status == "open"                       # ← bojamo SAMO ako je događaj otvoren
            and getattr(last, "vrsta", None) == "incoming"
            and getattr(last, "razuman_rok", None)
        ):
            days = (last.razuman_rok - timezone.localdate()).days
            if days < 0:
                event_cls = "table-danger"               # rok prošao
            elif days <= 14:
                event_cls = "table-warning"              # ≤14 dana do roka
            else:
                event_cls = ""                           # bez boje
        else:
            event_cls = ""                               # zatvoreno ili nema uvjeta → bez boje

        rows.append((d, dopisi, ball_on_us, last, event_cls))

    return render(request, "evidencija/dogadjaj_list.html", {
        "gradiliste": g,
        "rows": rows,
        "today": timezone.localdate(),
    })

def dogadjaj_detail(request, gradiliste_id, pk):
    d = get_object_or_404(Dogadjaj, pk=pk, gradiliste_id=gradiliste_id)
    d_status = getattr(d, "status", None)

    # zadnji dopis i tko je na potezu
    last = d.dopisi.order_by("-poslano", "-id").first()
    ball_on_us = bool(last and getattr(last, "vrsta", None) == "incoming")

    d_status = getattr(d, "status", None)

    rows = []
    for dp in d.dopisi.all().order_by("broj", "id"):  # prilagodi ordering po želji
        cls, label = due_badge(dp, ball_on_us, d_status)  # <-- pass status
        rows.append((dp, cls, label))

    return render(request, "evidencija/dogadjaj_detail.html", {
        "dogadjaj": d,
        "gradiliste": d.gradiliste,
        "ball_on_us": ball_on_us,
        "last": last,
        "rows": rows,
    })

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