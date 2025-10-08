from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest
from .models import Gradiliste, Dogadjaj, Dopis
from .forms import DogadjajForm, DopisForm, GradilisteForm
from datetime import date, datetime

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
    """Lista događaja filtrirana po odabranom gradilištu."""
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)

    # ----- tvoje postojeće sortiranje (ostavi kako imaš) -----
    sort = request.GET.get("sort", "broj_asc")
    ordering_map = {
        "broj_asc": "broj",
        "broj_desc": "-broj",
        "datum_desc": "-datum",
        "datum_asc": "datum",
    }
    ordering = ordering_map.get(sort, "broj")

    d_sort = request.GET.get("d_sort", "rok_asc")
    d_ordering_map = {
        "broj_asc": "broj",
        "broj_desc": "-broj",
        "poslano_asc": "poslano",
        "poslano_desc": "-poslano",
        "rok_asc": "razuman_rok",
        "rok_desc": "-razuman_rok",
    }
    d_ordering = d_ordering_map.get(d_sort, "razuman_rok")

    # ⬇⬇⬇ NAJVAŽNIJE: filtriramo po gradilištu
    dogadjaji = (
        Dogadjaj.objects
        .filter(gradiliste=gradiliste)
        .prefetch_related("dopisi")
        .order_by(ordering)
    )

    today = timezone.localdate()

    # helper za bedževe u podtablici dopisa (ostavi ako već imaš nešto slično)
    def due_badge(dopis: Dopis, is_ball_on_us: bool):
        if not is_ball_on_us:
            return ("bg-muted", "Loptica kod njih")
        days = dopis.days_to_due
        if days is None:
            return ("", "—")
        if days < 0:
            return ("bg-red", f"Kasni {abs(days)} d")
        if days == 0:
            return ("bg-yellow", "Rok danas")
        if days <= 2:
            return ("bg-yellow", f"Za {days} d")
        return ("bg-green", f"Za {days} d")

    rows = []
    for d in dogadjaji:
        last = d.dopisi.all().order_by("-poslano", "-created_at").first()
        ball_on_us = bool(last and last.vrsta == "incoming")  # Ulazno ⇒ na nama

        # Boja cijelog reda (što smo ranije dogovorili)
        event_cls = ""
        if ball_on_us and last and getattr(last, "razuman_rok", None):
            rok = last.razuman_rok
            if isinstance(rok, datetime):
                rok_date = timezone.localdate(rok)
            else:
                rok_date = rok
            delta_days = (rok_date - today).days
            if delta_days < 0:
                event_cls = "table-danger"
            elif delta_days <= 14:
                event_cls = "table-warning"

        dopisi_rows = []
        for dp in d.dopisi.all().order_by("broj"):
            cls, label = due_badge(dp, ball_on_us)
            dopisi_rows.append((dp, cls, label))

        rows.append((d, dopisi_rows, ball_on_us, last, event_cls))

    return render(
        request,
        "evidencija/dogadjaj_list.html",
        {
            "rows": rows,
            "today": today,
            "sort": sort,
            "d_sort": d_sort,
            "gradiliste": gradiliste,  # ⬅ u templateu sad imaš {{ gradiliste }}
        },
    )


def dogadjaj_detail(request, gradiliste_id, pk: int):
    """Detalj događaja unutar odabranog gradilišta."""
    gradiliste = get_object_or_404(Gradiliste, pk=gradiliste_id)
    d = get_object_or_404(Dogadjaj, pk=pk, gradiliste=gradiliste)

    last = d.dopisi.all().order_by("broj").first()
    ball_on_us = bool(last and last.vrsta == "incoming")

    def due_badge(dopis: Dopis, is_ball_on_us: bool):
        if not is_ball_on_us:
            return ("bg-muted", "Loptica kod njih")
        days = dopis.days_to_due
        if days is None:
            return ("", "—")
        if days < 0:
            return ("bg-red", f"Kasni {abs(days)} d")
        if days == 0:
            return ("bg-yellow", "Rok danas")
        if days <= 2:
            return ("bg-yellow", f"Za {days} d")
        return ("bg-green", f"Za {days} d")

    rows = []
    for dp in d.dopisi.all().order_by("razuman_rok", "-created_at"):
        cls, label = due_badge(dp, ball_on_us)
        rows.append((dp, cls, label))

    return render(
        request,
        "evidencija/dogadjaj_detail.html",
        {
            "dogadjaj": d,
            "rows": rows,
            "today": timezone.localdate(),
            "ball_on_us": ball_on_us,
            "last": last,
            "gradiliste": gradiliste,  # ⬅ da URL-ovi u templateu imaju ID gradilišta
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