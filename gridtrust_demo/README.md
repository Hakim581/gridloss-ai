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

## Sistemdən kim istifadə edəcək və haraya qoşulacaq?

**Gələcək inteqrasiya planı (hazır deyil):** Azərişıq SCADA sistemindən yalnız icazəli və oxuma rejimli məlumat ixracı → ayrıca GridTrust AI analitik xidməti → dispetçerin hadisə izahı ekranı.

- **Dispetçer** gündəlik bildiriş və sübutları görür, qərar verir; ssenari yaratmır.
- **Şəbəkə mühəndisi** səbəbləri araşdırır və göstəriciləri təsdiqləyir.
- **İT/OT inzibatçısı** mümkün pilotda bağlantı, icazə və auditin təhlükəsizliyini təmin edir.
- **Demo komandası** sintetik ssenariləri işə salır və sistemin davranışını yoxlayır.

**Hazırkı demo:** sintetik 35/10 kV model → sintetik hadisələr → lokal GridTrust analizi → Streamlit paneli. Heç bir real SCADA inteqrasiyası aparılmayıb.

## İki ayrı düymə niyə nəzərdə tutulur?

1. **Bütün sınaqları yoxla** — mühəndislik keyfiyyətinə nəzarət üçündür, gündəlik dispetçer işi deyil. Mövcud versiyada «Sınaq nəticələri» bölməsinin hesablama düyməsi buna uyğun funksiyanı təmin edir.
2. **Münsiflər üçün nümayiş** — yarışda vacib hadisələri qısa ardıcıllıqla göstərmək üçün gələcək seçimdir, bu versiyada ayrıca avtomatik rejim kimi hazırlanmayıb.

## İnterfeys

- **Baş səhifə:** sistemin nə üçün yaradıldığı, məlumatın mənbəyi, əldə edilən nəticələr, texniki status və sadə sxem.
- **Simulyasiya:** yeddi ssenarini seç və zaman addımlarını izlə.
- **Süni intellekt təhlili:** AI balı, qayda ilə ölçmə yoxlaması, səbəb izahı.
- **Sınaq nəticələri:** yalnız düymə ilə hesablanan sintetik dəqiqlik metrikləri.
- **Layihəni anla:** istifadəçi rolları, inteqrasiya planı, qaydalar və bütün əsas terminlərin Azərbaycan dilində izahı.

Əsas nümayiş: **S03 — Rabitənin kəsilməsi**. Rabitə itdikdə açarın son statusu bağlı olsa da cari status **MƏLUM DEYİL** göstərilir.

## Hesablamalar

Mümkün mühitdə `pandapower` 35/10 kV balanslı yük axını modelləşdirir. Pandapower quraşdırılmayıbsa, proqram 3-fazlı təqribi hesablamaya keçir və bunu mənbə göstəricisində açıq bildirir. Təqribi hesablamanın sənaye yük axını üçün əvəz olduğu iddia edilmir. Rele və qəza hadisələri **sintetik jurnallardır**, real qısaqapanma keçid simulyasiyası deyil.

**Hazırlıq statusu:** İlkin işləklik nümunəsi. Real utility performansı, operator istifadəliliyi, sənaye sertifikasiyası və real hadisələrlə doğrulama aparılmayıb.