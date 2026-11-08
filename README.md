# impriad-data

Katalaogy (`produits.json`) ho an'ny app *Komandy Sekoly Sabata*. **Repo public** (mila izany ny app mba hamaky ny rakitra).

- `produits.json`: lisitra misy `version`, `categories`, `products` (id, name, category, language, price).
- `scripts/update_catalog.py`: maka ny lisitra avy amin'ny https://impriad.mg/produits/. Mijanona raha tsy mifanaraka ny isa na misy vidiny tsy ara-dalàna (tsy misy commit).
- `.github/workflows/update-catalog.yml`: mandeha isan'andro (08:00 Madagasikara) sy amin'ny tanana (*Run workflow*). Rehefa miova ny site dia mandrisika `version + 1`.

Ny app dia mampitaha ny `version`: raha lehibe kokoa ny any amin'ny GitHub, dia soloina ny katalaogy ao amin'ny finday.
Ny kômandy efa natao dia mitazona ny vidiny tamin'izy natao.
