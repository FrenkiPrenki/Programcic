import re
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest
from .models import Gradiliste, Dogadjaj, Dopis
from .forms import DogadjajForm, DopisForm, GradilisteForm
from datetime import date, datetime, timedelta
from django.db.models import Min, Max, Prefetch
from django.utils import timezone


def due_badge(dp, ball_on_us: bool, dogadjaj_status: str):
    """
    Vraća (cls, label) za badge u tablici dopisa.
    Bojanje je relevantno samo ako je loptica na nama (zadnji dopis ulazni),
    i ako događaj nije zatvoren.
    """
    # Ako je događaj zatvoren, ništa ne forsiramo
    if dogadjaj_status == "zatvoreno":
        return ("text-bg-secondary", "Zatvoreno")

    # Ako loptica nije na nama, rok nije hitan
    if not ball_on_us:
        return ("text-bg-secondary", "Kod njih je potez")

    today = timezone.localdate()

    # Ako dopis ima razuman_rok, koristi njega
    if dp.razuman_rok:
        due = dp.razuman_rok
    else:
        # fallback: 7 dana od 'poslano' ako postoji
        if dp.poslano:
            due = dp.poslano + timedelta(days=7)
        else:
            return ("text-bg-secondary", "Bez roka")

    days_left = (due - today).days

    if days_left < 0:
        return ("text-bg-danger", f"Kasnimo {abs(days_left)}d")
    if days_left <= 2:
        return ("text-bg-warning", f"Rok {days_left}d")
    return ("text-bg-success", f"Ima {days_left}d")


def gradiliste_list(request):
    gradilista = Gradiliste.objects.all()
    return render(
        request, "evidencija/gradiliste_list.html", {"gradilista": gradilista}
    )


def gradiliste_create(request):
    if request.method == "POST":
        form = GradilisteForm(request.POST)
        if form.is_valid():
            g = form.save()
            return redirect("dogadjaj_list", gradiliste_id=g.id)
    else:
        form = GradilisteForm()
    return render(
        request, "evidencija/form.html", {"title": "Novo gradilište", "form": form}
    )


from datetime import datetime  # ako već nije uvezeno


def dogadjaj_list(request, gradiliste_id):
    g = get_object_or_404(Gradiliste, pk=gradiliste_id)

    # --- čitaj sort parametre iz URL-a ---
    sort = request.GET.get("sort", "broj_asc")  # za događaje
    d_sort = request.GET.get("d_sort", "poslano_asc")  # za dopise

    # mapiranja tipki -> order_by klauzule
    SORT_MAP = {
        "broj_asc": ("broj", "id"),
        "broj_desc": ("-broj", "id"),
        "datum_asc": ("datum", "id"),
        "datum_desc": ("-datum", "id"),
    }
    D_SORT_MAP = {
        "broj_asc": ("broj", "id"),
        "broj_desc": ("-broj", "id"),
        "poslano_asc": ("poslano", "id"),
        "poslano_desc": ("-poslano", "id"),
        "rok_asc": ("razuman_rok", "id"),
        "rok_desc": ("-razuman_rok", "id"),
    }

    order = SORT_MAP.get(sort, ("broj", "id"))
    dopisi_order = D_SORT_MAP.get(d_sort, ("poslano", "id"))

    # --- dohvati događaje s traženim sortiranjem ---
    dogadjaji = Dogadjaj.objects.filter(gradiliste=g).order_by(*order)

    rows = []
    for d in dogadjaji:
        # zadnji dopis i tko je na potezu
        last = d.dopisi.order_by("-poslano", "-id").first()
        ball_on_us = bool(last and getattr(last, "vrsta", None) == "incoming")
        d_status = getattr(d, "status", "open")

        # dopisi u traženom poretku
        dopisi = []
        for dp in d.dopisi.all().order_by(*dopisi_order):
            cls, label = due_badge(dp, ball_on_us, d_status)
            dopisi.append((dp, cls, label))

        # BOJANJE GLAVNOG REDA DOGAĐAJA — SAMO PO ZADNJEM DOPISU
        event_cls = ""

        # 1) Ako je događaj zatvoren -> zeleno
        if d_status in "zatvoreno":
            event_cls = "table-success"

        # 2) Ako je odgovoreno -> bez boje
        elif d_status == "odgovoreno":
            event_cls = ""

        # 3) Inače (otvoreno) bojamo po zadnjem dopisu
        else:
            if last and getattr(last, "vrsta", None) == "incoming":
                due = getattr(last, "razuman_rok", None)
                if not due and getattr(last, "poslano", None):
                    due = last.poslano + timedelta(days=7)

                if due:
                    days = (due - timezone.localdate()).days
                    if days < 0:
                        event_cls = "table-danger"  # rok prošao
                    elif days <= 14:
                        event_cls = "table-warning"  # ≤ 14 dana do roka

        rows.append((d, dopisi, ball_on_us, last, event_cls))

    return render(
        request,
        "evidencija/dogadjaj_list.html",
        {
            "gradiliste": g,
            "rows": rows,
            "today": timezone.localdate(),
            "sort": sort,
            "d_sort": d_sort,
        },
    )


def dogadjaj_detail(request, gradiliste_id, pk):
    d = get_object_or_404(Dogadjaj, pk=pk, gradiliste_id=gradiliste_id)
    d_status = getattr(d, "status", None)

    # zadnji dopis i tko je na potezu
    last = d.dopisi.order_by("-poslano", "-id").first()
    ball_on_us = bool(last and last.get_vrsta_display() == "Ulazno")

    d_status = getattr(d, "status", None)

    rows = []
    for dp in d.dopisi.all().order_by("poslano", "id"):  # prilagodi ordering po želji
        cls, label = due_badge(dp, ball_on_us, d_status)  # <-- pass status
        rows.append((dp, cls, label))

    return render(
        request,
        "evidencija/dogadjaj_detail.html",
        {
            "dogadjaj": d,
            "gradiliste": d.gradiliste,
            "ball_on_us": ball_on_us,
            "last": last,
            "rows": rows,
        },
    )


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
    return render(
        request,
        "evidencija/form.html",
        {"title": f"Novi događaj – {gradiliste.naziv}", "form": form},
    )


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
    return render(
        request,
        "evidencija/form.html",
        {"title": f"Uredi događaj – {gradiliste.naziv}", "form": form},
    )


def dopis_create_for_event(request, gradiliste_id, dogadjaj_id):
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    dogadjaj = get_object_or_404(Dogadjaj, pk=dogadjaj_id, gradiliste=gradiliste)

    if request.method == "POST":
        form = DopisForm(request.POST)
        if form.is_valid():
            dopis = form.save(commit=False)
            dopis.dogadjaj = (
                dogadjaj  # vežemo na odabrani događaj, ignorira se što god je u formi
            )
            dopis.save()
            return redirect(
                "dogadjaj_detail", gradiliste_id=gradiliste.id, pk=dogadjaj.id
            )
    else:
        # ako tvoj DopisForm ima polje 'dogadjaj', bolje ga maknuti iz forme (exclude) ili ga ostaviti readonly
        form = DopisForm(initial={"dogadjaj": dogadjaj})


    return render(
        request,
        "evidencija/form.html",
        {
            "title": f"Novi dopis – {dogadjaj.naziv}",
            "form": form,
            "gradiliste": dogadjaj.gradiliste,
            "is_dopis_form": True,
        },
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
    return render(
        request,
        "evidencija/form.html",
        {"title": f"Uredi dopis – {gradiliste.naziv}", "form": form},
    )


def dopisi_po_kategoriji(request, gradiliste_id: int):
    """
    Izvlači dopise iz svih događaja za JEDNO gradilište (po ID-u),
    i filtrira po vrsti dopisa (npr. ZZI) preko ?kategorija=ZZI.
    """
    gradiliste = get_object_or_404(Gradiliste, id=gradiliste_id)

    kategorija = (request.GET.get("kategorija") or "").strip()

    dopisi = Dopis.objects.select_related("dogadjaj", "dogadjaj__gradiliste").filter(
        dogadjaj__gradiliste=gradiliste
    )

    if kategorija:
        dopisi = dopisi.filter(kategorija=kategorija)

    # sortiranje
    sort = request.GET.get("sort", "poslano_asc")
    ordering_map = {
        "poslano_desc": "-poslano",
        "poslano_asc": "poslano",
        "rok_asc": "razuman_rok",
        "rok_desc": "-razuman_rok",
        "broj_asc": "broj",
        "broj_desc": "-broj",
        "dogadjaj_asc": "dogadjaj__broj",
        "dogadjaj_desc": "-dogadjaj__broj",
    }
    ordering = ordering_map.get(sort, "poslano")
    dopisi = dopisi.order_by(ordering, "-created_at")

    # dropdown za vrste (uzima choices iz modela)
    kategorija_field = Dopis._meta.get_field("kategorija")
    kategorija_choices = [(k, v) for (k, v) in kategorija_field.choices if k]

    return render(
        request,
        "evidencija/dopisi_po_kategoriji.html",
        {
            "gradiliste": gradiliste,
            "dopisi": dopisi,
            "kategorija": kategorija,
            "kategorija_choices": kategorija_choices,
            "sort": sort,
        },
    )


@require_GET
@login_required
def next_broj_for_kategorija(request, gradiliste_id):
    kategorija = (request.GET.get("kategorija") or "").strip()
    if not kategorija:
        return JsonResponse({"next": ""})

    # svi dopisi za to gradilište i kategoriju
    qs = Dopis.objects.filter(
        dogadjaj__gradiliste_id=gradiliste_id, kategorija=kategorija
    ).values_list("broj", flat=True)

    # izvuci najveći broj na kraju stringa (npr. "ZZI 14" -> 14)
    max_n = 0
    for b in qs:
        if not b:
            continue
        m = re.search(r"(\d+)\s*$", str(b))
        if m:
            n = int(m.group(1))
            if n > max_n:
                max_n = n

    next_n = max_n + 1
    return JsonResponse({"next": f"{kategorija.upper()} {next_n}"})
