from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone  # koristimo Django-ov timezone
from django.core.exceptions import ValidationError
from django.db.models import Q

# helper za default rok (+7 dana) – ovo se može serijalizirati u migracijama
def default_razuman_rok():
    return timezone.localdate() + timedelta(days=7)

class Gradiliste(models.Model):
    naziv = models.CharField("Naziv gradilišta", max_length=200, unique=True)
    lokacija = models.CharField("Lokacija", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["naziv"]
        verbose_name = "Gradilište"
        verbose_name_plural = "Gradilišta"

    def __str__(self):
        return self.naziv

class Dogadjaj(models.Model):
    RADNJA_CHOICES = [
        ('zzi','Zahtjev za informacijom (ZZI)'),
        ('claim','Potraživanje'),
        ('notice','Obavijest'),
        ('improvement','Poboljšanje'),
        ('suggestion','Prijedlog'),
        ('other','Ostalo'),
    ]

    broj = models.PositiveIntegerField("Broj događaja", blank=True, null=True)
    naziv = models.CharField("Naziv događaja", max_length=255)
    opis = models.TextField("Opis", blank=True)
    datum = models.DateField("Datum događaja", default=timezone.localdate)
    preporucena_radnja = models.CharField("Preporučena radnja", max_length=20, choices=RADNJA_CHOICES)
    gradiliste = models.ForeignKey("Gradiliste", on_delete=models.CASCADE, related_name="dogadjaji", null=True, blank=True)

    class Meta:
        verbose_name = "Događaj"
        verbose_name_plural = "Događaji"
        ordering = ['broj']
        constraints = [
            models.UniqueConstraint(fields=['gradiliste', 'broj'], name='uniq_broj_per_gradiliste')  # ⬅ NOVO
        ]

    def save(self, *args, **kwargs):
        if self.broj is None:  # ako nije ručno zadan
            qs = Dogadjaj.objects.all()
            if self.gradiliste_id:
                qs = qs.filter(gradiliste_id=self.gradiliste_id)
            last = qs.order_by('-broj').first()
            self.broj = 1 if not last or not last.broj else last.broj + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.broj} – {self.naziv} ({self.get_preporucena_radnja_display()})"

class Dopis(models.Model):
    STATUS_CHOICES = [
        ('open','Otvoreno'),
        ('answered','Odgovoreno'),
        ('closed','Zatvoreno'),
    ]
    VRSTA_CHOICES = [
        ('incoming', 'Ulazno'),
        ('outgoing', 'Izlazno'),
    ]
    KATEGORIJA_CHOICES = [
        ('', '—'),  # prazno je dopušteno
        ('zzi', 'ZZI'),
        ('potrazivanje', 'Potraživanje'),
        ('prijedlog', 'Prijedlog'),
        ('uputa_inzenjera', 'Uputa Inženjera'),
        ('poboljsanje', 'Poboljšanje'),
        ('obavijest', 'Obavijest'),
        ('dopis', 'Dopis'),
    ]

    dogadjaj = models.ForeignKey(Dogadjaj, on_delete=models.CASCADE, related_name="dopisi")
    broj_int = models.PositiveIntegerField("Broj dopisa (INT)", null=True, blank=True)
    broj = models.CharField("Broj dopisa (staro)", max_length=50, blank=True)
    vrsta = models.CharField("Vrsta dopisa", max_length=20, choices=VRSTA_CHOICES, default='incoming')
    kategorija = models.CharField("Vrsta dopisa", max_length=30, choices=KATEGORIJA_CHOICES, blank=True, default='')
    rb_po_kategoriji = models.PositiveIntegerField("Redni broj (po vrsti dopisa)", null=True, blank=True)
    poslano = models.DateField("Poslano", default=timezone.localdate)
    razuman_rok = models.DateField("Razuman rok za odgovor", default=default_razuman_rok)
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default='open')
    sadrzaj = models.TextField("Sadržaj", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # sortirajmo po novom integeru (pa tie-break po id)
        ordering = ["kategorija", "rb_po_kategoriji", "id"]
        verbose_name = "Dopis"
        verbose_name_plural = "Dopisi"
       
    def __str__(self):
        kat = dict(self.KATEGORIJA_CHOICES).get(self.kategorija, '—')
        if self.kategorija and self.rb_po_kategoriji:
            return f"{kat} {self.rb_po_kategoriji} – {self.get_vrsta_display()}"
        return f"Dopis – {self.get_vrsta_display()}"
    
    def clean(self):
        super().clean()
        # Ako ima i kategoriju i broj, provjeri jedinstvenost unutar *istog gradilišta* i *iste kategorije*
        if self.kategorija and self.rb_po_kategoriji:
            gradiliste_id = self.dogadjaj.gradiliste_id if self.dogadjaj_id else None
            if gradiliste_id:
                qs = Dopis.objects.filter(
                    dogadjaj__gradiliste_id=gradiliste_id,
                    kategorija=self.kategorija,
                    rb_po_kategoriji=self.rb_po_kategoriji,
                )
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({
                        "rb_po_kategoriji": "Taj broj već postoji za ovu vrstu dopisa na ovom gradilištu."
                    })

    #@property
    #def days_to_due(self):
    #    if self.razuman_rok:
    #        return (self.razuman_rok - timezone.localdate()).days
    #    return None

class Biljeska(models.Model):
    dopis = models.ForeignKey(Dopis, on_delete=models.CASCADE, related_name='biljeske')
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tekst = models.TextField("Bilješka / Odgovor")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bilješka"
        verbose_name_plural = "Bilješke"

    def __str__(self):
        return f"Bilješka za {self.dopis}"


class Prilog(models.Model):
    dopis = models.ForeignKey(Dopis, on_delete=models.CASCADE, related_name='prilozi')
    file = models.FileField(upload_to='prilozi/')
    opis = models.CharField("Opis", max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prilog"
        verbose_name_plural = "Prilozi"

    def __str__(self):
        return f"Prilog za {self.dopis}"
