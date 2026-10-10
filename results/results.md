# Eksperimentu rezultāti

Katram piemēram 20 palaišanas ar seed 1..20. Peļņa milj. EUR. HC saņem tādu pašu gājienu novērtējumu budžetu kā SA.
SA parametri: alpha = 0.99, gājieni temperatūrā = 25·k, p0 = 0.8, T_min = T0·0.001.

| k | Algoritms | Atsauce | Atsauces tips | Labākais | Vidējais | Sliktākais | Vid. atkāpe % | Maks. atkāpe % | Atrasts atsauces rez. | Gājieni | Vid. laiks, s |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | SA | 152.752 | optimums | 152.752 | 152.752 | 152.752 | 0.000 | 0.000 | 20/20 | 103200 | 0.119 |
| 6 | HC | 152.752 | optimums | 152.752 | 152.752 | 152.752 | 0.000 | 0.000 | 20/20 | 103200 | 0.113 |
| 8 | SA | 256.461 | optimums | 256.461 | 256.461 | 256.461 | 0.000 | 0.000 | 20/20 | 137600 | 0.165 |
| 8 | HC | 256.461 | optimums | 256.461 | 256.461 | 256.461 | 0.000 | 0.000 | 20/20 | 137600 | 0.178 |
| 10 | SA | 330.862 | optimums | 330.862 | 330.862 | 330.862 | 0.000 | 0.000 | 20/20 | 172000 | 0.220 |
| 10 | HC | 330.862 | optimums | 330.862 | 330.862 | 330.862 | 0.000 | 0.000 | 20/20 | 172000 | 0.261 |
| 16 | SA | 537.234 | labākais zināmais | 537.234 | 536.697 | 531.235 | 0.100 | 1.117 | 16/20 | 275200 | 0.390 |
| 16 | HC | 537.234 | labākais zināmais | 537.234 | 537.234 | 537.234 | 0.000 | 0.000 | 20/20 | 275200 | 0.595 |
| 24 | SA | 830.000 | labākais zināmais | 830.000 | 828.984 | 826.696 | 0.122 | 0.398 | 5/20 | 412800 | 0.588 |
| 24 | HC | 830.000 | labākais zināmais | 830.000 | 830.000 | 830.000 | 0.000 | 0.000 | 20/20 | 412800 | 1.305 |

Kopējais eksperimentu laiks: 78.7 s.
