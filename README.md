# GridLoss AI

**Elektrik paylayıcı şəbəkəsində itkinin lokallaşdırılması və qeyri-texniki itki riskinin aşkarlanması**

GridLoss AI universitet innovasiya müsabiqəsi üçün hazırlanmış işlək prototipdir. Sistem bir transformatoru, üç fideri və 30 smart sayğacı 30 gün ərzində 15 dəqiqəlik intervallarla simulyasiya edir. Məqsəd şəbəkədəki normal texniki itkini izah olunmayan enerjidən ayırmaq, problemin hansı fiderdə olduğunu göstərmək və yoxlanmalı sayğacları prioritetləşdirməkdir.

Tətbiq hər hansı müştərini pozuntu törətməkdə ittiham etmir. Nəticələr yalnız **Normal**, **Aşağı risk**, **Orta risk**, **Yüksək risk** və **Yoxlama tələb olunur** kimi təqdim edilir.

## Sistem nə edir?

1. T1 transformatoru, F1–F3 fiderləri və M01–M30 sayğacları üçün realistik istehlak yaradır.
2. Xətt cərəyanına və müqavimətinə əsaslanan gözlənilən texniki itkini hesablayır.
3. Fiderə daxil olan enerjidən sayğac enerjisini, çatışmayan məlumat üçün qiyməti və texniki itkini çıxır.
4. Qalan fərqi **izah olunmayan enerji** kimi göstərir.
5. Isolation Forest modeli ilə sayğacların öz normal istehlakından yayınmasını tapır.
6. Fiziki balansı, ML nəticəsini və açıq qaydaları birləşdirərək yoxlama prioriteti yaradır.

Əsas enerji balansı:

```text
İzah olunmayan enerji
= Fiderə daxil olan enerji
− Sayğaclarda qeydə alınan enerji
− Çatışmayan məlumat üçün qiymətləndirilən enerji
− Gözlənilən texniki itki
```

## Modelin məntiqi

### Fiziki qat

Fider xəttinin texniki itkisi sadələşdirilmiş balanslı üçfazalı model ilə hesablanır:

```text
I = P / (√3 × V × güc əmsalı)
Texniki itki = 3 × I² × R × Δt
```

Bu qat elektrik mühəndisinin yoxlaya biləcəyi enerji balansını yaradır. Rabitəsi kəsilmiş sayğac üçün ilk 10 günlük baza dövründə eyni saatın median göstəricisi istifadə edilir və məlumat keyfiyyəti ayrıca işarələnir.

### ML qatı

Isolation Forest hər sayğac üçün üç gündəlik əlaməti yoxlayır:

- istehlakın öz baza səviyyəsinə nisbəti;
- sıfır göstəricilərin payı;
- çatışmayan göstəricilərin payı.

Həftəsonu və iş günləri ayrıca müqayisə edilir. ML balı pozuntu ehtimalı deyil; normal istehlak nümunəsindən yayınmanın ölçüsüdür.

### Risk və lokallaşdırma qatı

Fider risk balı iki hissədən ibarətdir:

- 55% — izah olunmayan enerjinin baza dövründən statistik yayınması;
- 45% — izah olunmayan enerjinin gözlənilən texniki itkiyə nisbəti.

Sayğac yoxlama balı isə belə formalaşır:

- 62% — istehlakın öz baza səviyyəsindən azalması;
- 18% — ML anomaliya balı;
- 20% — aid olduğu fiderin risk balı.

Fider sensorları problemi fider səviyyəsində lokallaşdıra bilər. Sayğacdan kənar əlavə yükü bu ölçmələrlə konkret müştəriyə aid etmək mümkün deyil. Buna görə sistem nəticəni yalnız sahə yoxlaması üçün prioritet kimi təqdim edir.

## Demo ssenariləri

- **F2 / M17:** 18-ci gündən sayğacın az qeyd etməsi.
- **F2:** 21-ci gündən sayğacdan kənar əlavə yük. Bu hadisə fiderdə görünür, lakin konkret müştəriyə aid edilmir.
- **F1 / M05:** 24–27-ci günlərdə sayğac nasazlığı və sıfır göstəricilər.
- **F3 / M27:** 26–28-ci günlərdə rabitə kəsilməsi. Sistem bunu enerji pozuntusu kimi deyil, məlumat keyfiyyəti problemi kimi ayırır.

## Lokal işə salmaq

Python 3.10 və ya daha yeni versiya tələb olunur.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Streamlit-in terminalda göstərdiyi lokal ünvanı brauzerdə açın. Tətbiq bütün məlumatları özü yaradır; əlavə verilənlər bazası və ya API açarı lazım deyil.

CSV fayllarını yaratmaq və testləri işə salmaq üçün:

```bash
python -m src.utils.export_data
python -m pytest -q
```

## Streamlit Community Cloud-da yerləşdirmək

1. [share.streamlit.io](https://share.streamlit.io/) səhifəsində GitHub hesabı ilə daxil olun.
2. **Create app** seçin.
3. Repository: `Hakim581/gridloss-ai`
4. Branch: `main`
5. Main file path: `app.py`
6. **Deploy** düyməsini basın.

`main` branch-də edilən sonrakı dəyişikliklər yayımlanmış tətbiqə avtomatik ötürüləcək.

## Layihə quruluşu

- `app.py` — Azərbaycanca Streamlit interfeysi;
- `config/config.yaml` — simulyasiya və hadisə parametrləri;
- `src/simulation/` — şəbəkə, istehlak və anomaliya simulyasiyası;
- `src/detection/` — enerji balansı, ML və risk hesabı;
- `src/dashboard/` — qrafiklər və model izahı;
- `src/evaluation/` — sintetik həqiqətə görə qiymətləndirmə;
- `tests/` — simulyasiya, balans, aşkarlama və lokallaşdırma testləri;
- `docs/` — arxitektura, metodologiya və müsabiqə demo ssenarisi.

## Məhdudiyyətlər

Bütün tarixlər, ölçmələr və müştəri identifikatorları sünidir. Real şəbəkədə istifadədən əvvəl xətt parametrləri, faza xəritəsi, mövsümi və hava təsirləri, sayğac səhvləri və sahə yoxlamalarının nəticələri ilə kalibrasiya tələb olunur. Risk balı statistik ehtimal və ya hüquqi nəticə deyil.
