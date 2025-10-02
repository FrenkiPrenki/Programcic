from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpRequest
from .models import Dogadjaj, Dopis
from .forms import DogadjajForm, DopisForm


def dogadjaj_list(request: HttpRequest):
    # --- SORT Događaji ---
    sort = request.GET.get("sort", "broj_asc")
    ordering_map = {
        "broj_asc": "broj",
        "broj_desc": "-broj",
        "datum_desc": "-datum",
        "datum_asc": "datum",
    }
    ordering = ordering_map.get(sort, "broj")

    # --- SORT Dopisi (unutar svakog događaja) ---
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

    dogadjaji = Dogadjaj.objects.prefetch_related("dopisi").order_by(ordering)
    today = timezone.localdate()

    def due_badge(dopis: Dopis, is_ball_on_us: bool):
        """
        Vrati (css_klasa, label) za prikaz roka.
        Rok bojamo SAMO ako je zadnji dopis Ulazni (loptica kod nas).
        Inače vraćamo sivu oznaku.
        """
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
        # zadnji dopis prema 'poslano' (ako isti dan, po created_at)
        last = d.dopisi.all().order_by("-poslano", "-created_at").first()
        ball_on_us = bool(last and last.vrsta == "incoming")  # Ulazno ⇒ na nama loptica

        dopisi_rows = []
        for dp in d.dopisi.all().order_by(d_ordering, "-created_at"):
            cls, label = due_badge(dp, ball_on_us)
            dopisi_rows.append((dp, cls, label))
        rows.append((d, dopisi_rows, ball_on_us, last))

    return render(
        request,
        "evidencija/dogadjaj_list.html",
        {"rows": rows, "today": today, "sort": sort, "d_sort": d_sort},
    )


def dogadjaj_detail(request, pk: int):
    d = get_object_or_404(Dogadjaj, pk=pk)

    last = d.dopisi.all().order_by("-poslano", "-created_at").first()
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
        },
    )


# ---------- FORME (bez admina) ----------
def dogadjaj_create(request):
    if request.method == "POST":
        form = DogadjajForm(request.POST)
        if form.is_valid():
            d = form.save()
            return redirect("dogadjaj_detail", pk=d.pk)
    else:
        form = DogadjajForm()
    return render(request, "evidencija/form.html", {"form": form, "title": "Novi događaj"})


def dogadjaj_update(request, pk: int):
    d = get_object_or_404(Dogadjaj, pk=pk)
    if request.method == "POST":
        form = DogadjajForm(request.POST, instance=d)
        if form.is_valid():
            form.save()
            return redirect("dogadjaj_detail", pk=d.pk)
    else:
        form = DogadjajForm(instance=d)
    return render(
        request,
        "evidencija/form.html",
        {"form": form, "title": f"Uredi događaj #{d.broj if d.broj is not None else d.pk}"},
    )


def dopis_create(request, dogadjaj_id: int | None = None):
    initial = {}
    if dogadjaj_id is not None:
        initial["dogadjaj"] = get_object_or_404(Dogadjaj, pk=dogadjaj_id)

    if request.method == "POST":
        form = DopisForm(request.POST, initial=initial)
        if form.is_valid():
            dp = form.save()
            return redirect("dogadjaj_detail", pk=dp.dogadjaj.pk)
    else:
        form = DopisForm(initial=initial)

    return render(request, "evidencija/form.html", {"form": form, "title": "Novi dopis"})


def dopis_update(request, pk: int):
    dp = get_object_or_404(Dopis, pk=pk)
    if request.method == "POST":
        form = DopisForm(request.POST, instance=dp)
        if form.is_valid():
            form.save()
            return redirect("dogadjaj_detail", pk=dp.dogadjaj.pk)
    else:
        form = DopisForm(instance=dp)
    title_suffix = f" {dp.broj}" if dp.broj else ""
    return render(
        request,
        "evidencija/form.html",
        {"form": form, "title": f"Uredi dopis{title_suffix}"},
    )
