# ... (tu script tal cual)
OUT_DIR = "/app/out"
import os
os.makedirs(OUT_DIR, exist_ok=True)

# cuando guardes:
open(os.path.join(OUT_DIR,"chats.raw.json"), "w", encoding="utf-8").write(json.dumps(chats, ensure_ascii=False, indent=2))
open(os.path.join(OUT_DIR,"messages.raw.json"), "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=2))
grouped.to_csv(os.path.join(OUT_DIR,"summary_by_chat.csv"), index=False, encoding="utf-8")
plt.savefig(os.path.join(OUT_DIR,"hist_sentimiento.png"), dpi=144)
plt.savefig(os.path.join(OUT_DIR,"avg_sentimiento_top_chats.png"), dpi=144)
# ...
