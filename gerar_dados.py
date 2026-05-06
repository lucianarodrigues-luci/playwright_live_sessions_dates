# gerar_dados.py
import pandas as pd

# Lê o arquivo recalculado gerado por calcular_datas.py.
df = pd.read_csv("orig_teste.csv", sep=None, engine="python")

# Verificação das colunas necessárias
need = [
    "trainer_label",
    "section1_date_and_time","session1_url",
    "section2_date_and_time","session2_url",
    "section3_date_and_time","session3_url",
    "section4_date_and_time","session4_url",
]
missing = [c for c in need if c not in df.columns]
if missing:
    raise SystemExit(f"❌ Colunas faltando no orig_teste.csv: {missing}")

linhas = []
for _, row in df.iterrows():
    trainer = str(row["trainer_label"]).strip()
    for i in range(1, 5):
        date_col = f"section{i}_date_and_time"
        url_col  = f"session{i}_url"
        date_txt = str(row[date_col]).strip() if pd.notna(row[date_col]) else ""
        url_txt  = str(row[url_col]).strip()  if pd.notna(row[url_col])  else ""
        if not trainer or not date_txt or not url_txt:
            continue
        linhas.append({
            "trainer_label": trainer,
            "section": i,
            "session_url": url_txt,
            "date_time": date_txt,
            "status": "pronto",   # mude pra "pendente" se quiser filtrar depois
        })

out = pd.DataFrame(linhas)
out.to_csv("dados.csv", index=False)
print(f"✅ Gerado dados.csv com {len(out)} linhas.")
