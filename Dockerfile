# 1. Python image
FROM python:3.12-slim

# 2. Working directory
WORKDIR /app

# 3. Kodları konteynerə əlavə et
COPY . .

# 4. Gerekli paketləri qur
RUN pip install --upgrade pip && pip install -r requirements.txt

# 5. Static files (əgər istifadə edirsənsə, yoxsa comment-lə)
# RUN python manage.py collectstatic --noinput

# 6. Port
EXPOSE 8000

# 7. Komanda
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
