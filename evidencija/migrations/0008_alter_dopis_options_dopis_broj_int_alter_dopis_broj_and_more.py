from django.db import migrations

def forward(apps, schema_editor):
    Dopis = apps.get_model('evidencija', 'Dopis')

    def only_digits(s: str) -> int | None:
        if not s:
            return None
        digits = ''.join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else None

    # 1) Najprije popuni broj_int iz postojećeg tekstualnog broja
    for d in Dopis.objects.all().only('id', 'broj', 'broj_int'):
        if d.broj_int is None:
            d.broj_int = only_digits(d.broj)
            d.save(update_fields=['broj_int'])

    # 2) Ako postoji duplikat po (dogadjaj, broj_int), pomakni ga na prvi slobodan broj
    from django.db.models import F
    by_event = {}
    for d in Dopis.objects.select_related('dogadjaj').values('id', 'dogadjaj_id', 'broj_int'):
        by_event.setdefault(d['dogadjaj_id'], set()).add(d['broj_int'])

    DopisModel = apps.get_model('evidencija', 'Dopis')
    for d in DopisModel.objects.select_related('dogadjaj').order_by('dogadjaj_id', 'broj_int', 'id'):
        used = by_event.setdefault(d.dogadjaj_id, set())
        if d.broj_int is None or d.broj_int in [None]:
            # prazno → na kraj
            n = 1
            while n in used:
                n += 1
            d.broj_int = n
            d.save(update_fields=['broj_int'])
            used.add(n)
        else:
            # ako je dupliciran, pomakni na prvi slobodan
            # (set 'used' već sadrži i njegov trenutni broj; idemo na prvi slobodan prema gore
            count_same = DopisModel.objects.filter(dogadjaj_id=d.dogadjaj_id, broj_int=d.broj_int).count()
            if count_same > 1:
                n = d.broj_int
                while n in used:
                    n += 1
                d.broj_int = n
                d.save(update_fields=['broj_int'])
                used.add(n)

def backward(apps, schema_editor):
    # ništa – zadržavamo broj_int
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('evidencija', '0007_alter_dogadjaj_broj_and_more'),  # prilagodi na zadnju migraciju
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
