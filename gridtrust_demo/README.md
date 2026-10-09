# GridTrust AI — Sadə Azərbaycan dilli Streamlit demo

> **Sintetik məlumatlar.** Bu proqram real “Azərişıq” SCADA/OT sisteminə qoşulmur, açar idarə etmir, rele parametrlərini dəyişmir.

## Nə edir?

GridTrust AI elektrik şəbəkəsinin **ölçmə, rabitə və hadisə** məlumatlarını bir yerdə göstərir. Proqram rabitə kəsiləndə açarın **son məlum** vəziyyətini **cari təsdiqlənmiş** vəziyyət kimi təqdim etmir. Süni intellekt modulu (`IsolationForest`) qeyri-adi məlumat davranışlarını əlavə olaraq aşkarlayır. Fiziki yoxlama qaydaları ayrıca hesablanır.

## İşə salma

Python 3.11 tövsiyə olunur. GitHub repozitoriyasının kökündə:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r gridtrust_demo/requirements.txt
python -m streamlit run gridtrust_demo/app.py
```

Test:

```powershell
python -m pytest -q gridtrust_demo/tests
```

## İnterfeys

- **Baş səhifə:** vəziyyətin bir baxışda izahı, kiçik elektrik sxemi.
- **Simulyasiya:** yeddi ssenarini seç və zaman addımlarını izlə.
- **Süni intellekt təhlili:** AI balı, qayda ilə ölçmə yoxlaması, səbəb izahı.
- **Sınaq nəticələri:** yalnız düymə ilə hesablanan sintetik dəqiqlik metrikləri.
- **Layihəni anla:** mərhələlər, təhlükəsizlik qaydaları, bütün əsas terminlərin Azərbaycan dilində izahı.

Əsas nümayiş: **S03 — Rabitənin kəsilməsi**. Rabitə itdikdə açarın son statusu bağlı olsa da cari status **MƏLUM DEYİL** göstərilir.

## Hesablamalar

Mümkün mühitdə `pandapower` 35/10 kV balanslı yük axını modelləşdirir. Pandapower quraşdırılmayıbsa, proqram 3-fazlı təqribi hesablamaya keçir və bunu mənbə göstəricisində açıq bildirir. Təqribi hesablamanın sənaye yük axını üçün əvəz olduğu iddia edilmir. Rele və qəza hadisələri **sintetik jurnallardır**, real qısaqapanma keçid simulyasiyası deyil.

**Hazırlıq statusu:** İlkin işləklik nümunəsi. Real utility performansı, operator istifadəliliyi, sənaye sertifikasiyası və real hadisələrlə doğrulama aparılmayıb.