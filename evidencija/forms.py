from django import forms
from .models import Dogadjaj, Dopis, Gradiliste

# HTML5 "date" input (prikazuje kalendar u browseru)
class DateInput(forms.DateInput):
    input_type = "date"

class DogadjajForm(forms.ModelForm):
    class Meta:
        model = Dogadjaj
        # ➜ DODANO: "datum" pa ga možeš mijenjati na formi
        fields = ["broj", "naziv", "opis", "status", "preporucena_radnja", "datum"]
        widgets = {
            # ➜ Date picker za datum događaja
            "datum": DateInput(),
        }

class DopisForm(forms.ModelForm):
    class Meta:
        model = Dopis
        fields = ["broj_int", "vrsta", "kategorija", "oznaka", "poslano", "razuman_rok", "status", "sadrzaj"]
        widgets = {
            # ➜ Date pickeri za datume dopisa
            "poslano": DateInput(),
            "razuman_rok": DateInput(),
        }
        help_texts = {
            "kategorija": "Odaberi vrstu",
            "oznaka": "Ručna oznaka za tu vrstu"
        }

class GradilisteForm(forms.ModelForm):
    class Meta:
        model = Gradiliste
        fields = ["naziv", "lokacija"]