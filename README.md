# F1 sezonas kalendāra plānošana ar simulēto rūdīšanu

Praktiskais darbs optimizācijas kursā. Visi algoritmi (simulētā rūdīšana, hill climbing,
pilnā pārlase) ir implementēti pašrocīgi, izmantojot tikai Python standarta bibliotēku.

## Uzdevums

Doti **k** F1 posmi (trases) un **n = k** nedēļas nogales no marta līdz novembrim. Katram
posmam jāpiekārto tieši viena nedēļas nogale, t.i., risinājums ir posmu permutācija
`cal`, kur `cal[w]` ir posms, kas notiek nedēļas nogalē `w`. Jāmaksimizē peļņa:

```
profit(cal) = Σ_w ien[cal[w]][w]  −  Σ_w izm[cal[w]][cal[w+1]]
```

- `ien[p][w]` — posma `p` ieņēmumi, ja tas notiek nedēļas nogalē `w` (atkarīgi no sezonas);
- `izm[a][b]` — ceļošanas izmaksas starp secīgiem posmiem (loģistika + CO2 emisijas).

Meklēšanas telpā ir k! risinājumu (k = 24 → ~6,2·10²³), tāpēc lieliem k pilnā pārlase nav iespējama.

### Testa piemēru modelis (`src/generator.py`)

- **Izmaksas** (milj. EUR): haversine attālums km × (2000 €/km loģistika + 4 t CO2/km × 150 €/t).
  Pārbraucieniem līdz 1500 km (kravas auto Eiropā) piemēro koeficientu 0,6.
- **Ieņēmumi** (milj. EUR): trases bāzes ieņēmumi × sezonalitātes koeficients pēc klimata tipa
  un mēneša × (1 ± 5% troksnis). Klimata tipi: `desert` (vasarā ļoti zems), `temperate`
  (Eiropas vasara augsta), `mediterranean`, `subtropical`, `tropical`, `southern_hemisphere`
  (labs martā/novembrī).
- **Nedēļas nogales**: k svētdienas, vienmērīgi sadalītas no 2026. g. marta pirmās līdz
  novembra pēdējai svētdienai; nogales mēnesis nosaka sezonalitāti.
- **Izmēri**: k = 6, 8, 10, 16, 24. Mazajiem piemēriem trases izvēlas kā nejaušu
  (bet ar seed reproducējamu) apakškopu no 24 trasēm (`data/tracks.json`).

Bāzes ieņēmumi un izmaksu koeficienti ir ilustratīvi, nevis reāli finanšu dati.

## Algoritmi

**Gājieni** (`src/model.py`): divu posmu samainīšana (*swap*), segmenta apgriešana
(*reverse*), posma pārvietošana (*insert*). Katram gājienam ir delta novērtējums, kas nepārrēķina
visu kalendāru: swap — O(1), reverse un insert — O(segmenta garums) ieņēmumiem un O(1) ceļam
(jo ieņēmumi atkarīgi no nedēļas, nobīdītajiem posmiem tie jāpārrēķina).

**Simulētā rūdīšana** (`src/sa.py`):
- nejaušs sākuma kalendārs; gājiena tips ar varbūtībām 0,4 / 0,3 / 0,3 (swap / reverse / insert);
- uzlabojumu pieņem vienmēr, pasliktinājumu par |Δ| — ar varbūtību exp(−|Δ|/T);
- T0 nosaka automātiski: 200 nejaušiem gājieniem aprēķina vidējo pasliktinājumu |Δ| un izvēlas
  T0 tā, lai exp(−|Δ|/T0) = p0 (noklusējumā p0 = 0,8);
- ģeometriska dzesēšana T ← α·T (α = 0,99), 25·k gājieni katrā temperatūrā, apstājas pie
  T < 10⁻³·T0;
- atgriež labāko atrasto kalendāru, tā peļņu, laiku un konverģences vēsturi.

**Hill climbing ar restartiem** (`src/hill_climbing.py`): no nejauša kalendāra izmanto pirmo
uzlabojošo gājienu pilnā apkārtnē (visi swap/reverse/insert nejaušā secībā); lokālajā optimumā
restartē. Eksperimentos HC saņem tieši tādu pašu gājienu novērtējumu budžetu kā SA.

**Pilnā pārlase** (`src/bruteforce.py`): rekursīvi apskata visas k! permutācijas ar inkrementālu
peļņas skaitīšanu (k = 10: 3 628 800 permutācijas, ~6 s). Rezultāts tiek saglabāts instances
failā (`"optimum"`) un netiek rēķināts atkārtoti. Ar `--bnb` var ieslēgt zaru un robežu
nogriešanu (arī precīza, bet ātrāka).

## Kā palaist

Nepieciešams Python 3.8+. Ārējas bibliotēkas nav vajadzīgas; `matplotlib` ir neobligāts
(tikai konverģences grafikam).

```bash
# (neobligāti) virtuālā vide un matplotlib
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows
pip install matplotlib

python src/generator.py            # 1. ģenerē instances/f1_k{6,8,10,16,24}.json
python src/bruteforce.py           # 2. precīzi optimumi k ≤ 10 (saglabājas instanču failos)
python src/experiments.py          # 3. SA un HC, 20 palaišanas katram piemēram → results/
python src/show_calendar.py 24     # 4. labākā atrastā kalendāra izdruka
```

Windows sistēmā `python` vietā var izmantot `py`. Visas komandas jāpalaiž no projekta saknes.

Noderīgas opcijas:

```bash
python src/generator.py --seed 2026 --sizes 6 8 10 16 24
python src/experiments.py --runs 20 --seed 1 --sizes 16 24 --alpha 0.98 --p0 0.5
python src/sa.py instances/f1_k10.json --seed 3 --move-probs 0.2 0.4 0.4
python src/hill_climbing.py instances/f1_k10.json --seed 3 --max-evals 100000
python src/show_calendar.py instances/f1_k16.json --source sa --seed 7
python -m unittest discover tests  # delta formulu un algoritmu testi
```

Visi rezultāti ir reproducējami: ģenerators izmanto seed `2026·1000 + k`, eksperimentu
palaišanas — seed `1..20` (tos pašus SA un HC).

## Rezultāti

Pilna tabula: [results/results.md](results/results.md), atsevišķas palaišanas:
`results/runs.csv`, konverģence: `results/convergence.png` / `results/convergence.csv`.

- k = 6, 8, 10: SA visās 20 palaišanās atrod precīzo optimumu (pārbaudīts ar pilno pārlasi).
- k = 16, 24: optimums nav zināms; atsauce ir labākais atrastais risinājums. SA vidējā atkāpe
  ~0,1%, sliktākā ≤ ~1,1%.
- Ar vienādu gājienu budžetu HC ar restartiem šiem piemēriem ir stabilāks (20/20). Iemesls —
  apvienotā swap+reverse+insert apkārtne ir ļoti bagāta, un ainavā ir maz dziļu lokālo optimumu,
  tāpēc daudzi īsi kāpieni ātri atrod labāko baseinu. SA apmēram trešdaļu budžeta pavada augstā
  temperatūrā, kur notiek gandrīz nejauša klejošana.
- Gājienu kombinācija ir būtiska: SA tikai ar swap vai tikai ar insert gājieniem parametru
  izpētē deva 2–5× lielāku vidējo atkāpi nekā ar visiem trim gājienu tipiem.

## Projekta struktūra

```
data/tracks.json          24 F1 trases: nosaukums, valsts, koordinātas, klimata tips, bāzes ieņēmumi
instances/f1_k*.json      ģenerētie piemēri (+ saglabātais optimums / labākais zināmais)
src/generator.py          testa piemēru ģenerators
src/model.py              instances ielāde, profit(), gājieni un delta novērtēšana
src/sa.py                 simulētā rūdīšana
src/hill_climbing.py      hill climbing ar restartiem
src/bruteforce.py         pilnā pārlase (k ≤ 10)
src/experiments.py        eksperimenti → results/
src/show_calendar.py      kalendāra izdruka
tests/test_model.py       vienībtesti
results/                  results.csv, results.md, runs.csv, convergence.png/.csv
```
