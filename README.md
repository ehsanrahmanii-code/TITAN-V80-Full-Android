# TITAN PRO V80.1.2 — Full Android APK

موتور تحلیل کریپتو (فقط تحلیل، بدون اجرای سفارش) داخل APK با **Chaquopy**.

## نسخه
- **80.1.2-nervous** — Central Nervous Seal، سطوح LONG/SHORT درست، ماتریس TF ساختاریافته

## ساخت APK
1. Actions → **Build TITAN V80 Android APK** → Run workflow
2. بعد از اتمام، Artifact: `TITAN-V80-Android-APK` را دانلود کنید
3. روی گوشی نصب کنید (Unknown sources)

یا محلی:
```bash
./gradlew assembleDebug
# خروجی: app/build/outputs/apk/debug/app-debug.apk
```

## داخل برنامه
- Flask + waitress روی `127.0.0.1:8080`
- WebView به همان آدرس
- داده در `filesDir/MMM/`
- وابستگی‌های Python داخل APK (numpy, pandas, flask, waitress, requests)

## محدودیت صادقانه
- قیمت زنده نیاز به اینترنت دارد (صرافی)
- این محیط (Grok) نمی‌تواند APK را روی گوشی واقعی نصب و تست کند؛ ساخت از GitHub Actions است

## ریپو
https://github.com/ehsanrahmanii-code/TITAN-V80-Full-Android
