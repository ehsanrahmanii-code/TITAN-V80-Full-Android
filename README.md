# TITAN V80 Full Android

برنامه اندروید **با موتور کامل ماژولار** TITAN PRO V80 (Flask + numpy + pandas + 80+ لایه).

- بدون داشبورد جعلی
- موتور واقعی روی `http://127.0.0.1:8080`
- داده فقط داخل پوشه خصوصی اپ (`filesDir/MMM`)
- فقط تحلیل (analysis-only)

## ساخت APK (گام‌به‌گام)

1. فایل **TITAN-V80-Full-Android-complete.zip** را که از چت دانلود کردید باز کنید.
2. پوشه `app/src/main/python` را از داخل zip کپی کنید.
3. در این ریپو روی GitHub بروید → **Add file → Upload files**.
4. محتویات `python` (شامل `titan_bootstrap.py` و پوشه `titan/`) را داخل مسیر `app/src/main/python/` آپلود کنید.
5. Commit کنید.
6. بروید به تب **Actions** → workflow اجرا می‌شود.
7. Artifact به نام **TITAN-V80-Android-APK** را دانلود کنید.

## نصب

1. APK را نصب کنید (Unknown sources را فعال کنید).
2. اولین اجرا ممکن است ۱–۳ دقیقه طول بکشد.

## نسخه

**80.0.0** — Modular monolith + advanced platform
