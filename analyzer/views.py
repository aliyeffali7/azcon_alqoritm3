from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import pandas as pd
import os
from azcon_match import config, matcher, data_loader

def upload_file(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        uploaded_file = request.FILES['excel_file']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        filepath = fs.path(filename)

        # query faylını oxu
        query_df = pd.read_excel(filepath)

        # master data yüklə
        master_df = data_loader.load_master()

        # nəticələri topla
        results = []
        for idx, row in query_df.iterrows():
            q_raw = row.get("Malların (işlərin və xidmətlərin) adı", "")
            q_flag = row.get("Tip", "")
            q_unit = row.get("Ölçü vahidi", "")
            res = matcher.find_matches(q_raw, q_flag, q_unit, master_df)

            top_hit = res['priced_hits'][0] if res['priced_hits'] else ("", 0, None, "")

            # Əlavə sütun üçün uyğun gələn sətrləri formatla
            matched_rows = [
                f"{t} – {pr} ₼ / {u} (score {sc})"
                for t, sc, pr, u in res['priced_hits']
            ]
            matched_text = "\n".join(matched_rows) if matched_rows else "—"

            results.append({
                "Sual": q_raw,
                "Qiymət": top_hit[2],
                "Ölçü vahidi": top_hit[3],
                "Uyğunluq dərəcəsi": top_hit[1],
                "Uyğun gələn sətrlər": matched_text  # ✅ YENİ sütun
            })
            # sadəcə 1 nəticə alsaq onu yaz
            
        

        output_df = pd.DataFrame(results)
        output_path = os.path.join('media', f"analyzed_{filename}")
        output_df.to_excel(output_path, index=False)

        with open(output_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename=analyzed_' + filename
            return response

    return render(request, 'analyzer/upload.html')

df = pd.read_excel(config.MASTER_PATH, engine="openpyxl")
print("🧾 Sütunlar:", df.columns)
