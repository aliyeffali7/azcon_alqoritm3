# from django.shortcuts import render
# from django.http import HttpResponse
# from django.core.files.storage import FileSystemStorage
# import pandas as pd
# import os
# from azcon_match import config, matcher, data_loader

# def upload_file(request):
#     if request.method == 'POST' and request.FILES.get('excel_file'):
#         uploaded_file = request.FILES['excel_file']
#         fs = FileSystemStorage()
#         filename = fs.save(uploaded_file.name, uploaded_file)
#         filepath = fs.path(filename)

#         # query faylını oxu
#         query_df = pd.read_excel(filepath)

#         # master data yüklə
#         master_df = data_loader.load_master()

#         # nəticələri topla
#         results = []
#         for idx, row in query_df.iterrows():
#             q_raw = row.get("Malların (işlərin və xidmətlərin) adı", "")
#             q_flag = row.get("Tip", "")
#             q_unit = row.get("Ölçü vahidi", "")
#             res = matcher.find_matches(q_raw, q_flag, q_unit, master_df)

#             top_hit = res['priced_hits'][0] if res['priced_hits'] else ("", 0, None, "")

#             # Əlavə sütun üçün uyğun gələn sətrləri formatla
#             matched_rows = [
#                 f"{t} – {pr} ₼ / {u} (score {sc})"
#                 for t, sc, pr, u in res['priced_hits']
#             ]
#             matched_text = "\n".join(matched_rows) if matched_rows else "—"

#             results.append({
#                 "Sual": q_raw,
#                 "Qiymət": top_hit[2],
#                 "Ölçü vahidi": top_hit[3],
#                 "Uyğunluq dərəcəsi": top_hit[1],
#                 "Uyğun gələn sətrlər": matched_text  # ✅ YENİ sütun
#             })
#             # sadəcə 1 nəticə alsaq onu yaz
            
        

#         output_df = pd.DataFrame(results)
#         output_path = os.path.join('media', f"analyzed_{filename}")
#         output_df.to_excel(output_path, index=False)

#         with open(output_path, 'rb') as f:
#             response = HttpResponse(f.read(), content_type='application/vnd.ms-excel')
#             response['Content-Disposition'] = f'attachment; filename=analyzed_' + filename
#             return response

#     return render(request, 'analyzer/upload.html')


# analyzer/views.py
# analyzer/views.py
from __future__ import annotations

from django.shortcuts import render
from django.http import FileResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from pathlib import Path
import pandas as pd
import os

from azcon_match import api as match_api
from azcon_match import config  # sütun adları üçün

def _resolve_master_path() -> Path | None:
    """
    Master faylını tapmaq üçün prioritet:
      1) BASE_DIR / data / master_db.xlsx
      2) BASE_DIR / master_db.xlsx
      3) config.MASTER_PATH (əgər mövcuddursa və fayl varsa)
    """
    candidates: list[Path] = [
        Path(settings.BASE_DIR) / "data" / "master_db.xlsx",
        Path(settings.BASE_DIR) / "master_db.xlsx",
    ]
    for p in candidates:
        if p.exists():
            return p

    legacy = getattr(config, "MASTER_PATH", None)
    if legacy and Path(legacy).exists():
        return Path(legacy)

    return None

def upload_file(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        # 1) Faylı saxla
        up = request.FILES['excel_file']
        fs = FileSystemStorage()
        filename = fs.save(up.name, up)
        filepath = Path(fs.path(filename))

        # 2) Master-i tap və yüklə (MEDIA deyil!)
        master_path = _resolve_master_path()
        if not master_path:
            return HttpResponse(
                "Master faylı tapılmadı. Zəhmət olmasa 'data/master_db.xlsx' yerləşdir.",
                status=500
            )
        try:
            master_df = match_api.load_master(path=str(master_path))
        except Exception as e:
            return HttpResponse(f"Master yüklənmədi: {e}", status=500)

        # 3) Query faylını oxu
        try:
            query_df = pd.read_excel(filepath)
        except Exception as e:
            return HttpResponse(f"Query Excel oxunmadı: {e}", status=400)

        # 4) Sətir-sətir matçla
        results: list[dict] = []
        for _, row in query_df.iterrows():
            q_raw  = row.get(config.QUERY_TEXT_COL, "")
            q_flag = row.get(config.QUERY_FLAG_COL, "")
            q_unit = row.get(config.UNIT_COL, "")

            # Mütləq string-ləşdir
            q_raw  = "" if pd.isna(q_raw)  else str(q_raw)
            q_flag = "" if pd.isna(q_flag) else str(q_flag)
            q_unit = "" if pd.isna(q_unit) else str(q_unit)

            # API həmişə dict qaytarmalıdır; ehtiyat üçün guard
            res = match_api.find_matches(q_raw, q_flag, q_unit, master_df) or {}
            hits = res.get("priced_hits") or []

            top = hits[0] if len(hits) > 0 else ("", 0, None, "")
            matched_rows = [f"{t} – {pr} ₼ / {u} (score {sc})" for t, sc, pr, u in hits]

            results.append({
                "Sual": q_raw,
                "Qiymət": top[2],
                "Ölçü vahidi": top[3],
                "Uyğunluq dərəcəsi": top[1],
                "Uyğun gələn sətrlər": "\n".join(matched_rows) if matched_rows else "—",
            })

        # 5) Nəticəni MEDIA_ROOT-a yaz və göndər
        out_name = f"analyzed_{os.path.basename(filename)}"
        out_path = Path(settings.MEDIA_ROOT) / out_name
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        pd.DataFrame(results).to_excel(out_path, index=False)

        return FileResponse(
            open(out_path, "rb"),
            as_attachment=True,
            filename=out_name,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # GET → formu göstər
    return render(request, 'analyzer/upload.html')

