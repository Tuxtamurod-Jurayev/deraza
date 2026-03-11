# Eshik-Deraza CRM (MVP)

Bu loyiha eshik-deraza savdo bo'limi uchun CRM tizimi.

- Admin login
- Mahsulot qo'shish
  - Turlar: `eshik`, `deraza`, `padagolnik`, `portichka`, `pena`
  - `eshik`/`deraza` tanlanganda rang va o'lcham tanlanadi
  - Saqlashda kelish narxi va soni bilan kirim avtomatik yoziladi
- Mahsulot kirimini kiritish
- Sotuvni kiritish
- Chiqim bo'limi (`nomi`, `summa`, `komment`) bilan xarajat saqlash
- Sotuv/Chiqim/Mahsulot jadvallarida CRUD (`qo'shish`, `tahrirlash`, `o'chirish`)
- Qo'shish formalari alohida markaziy tugma orqali ochiladi
- Light/Dark tema (`sun/night`) tugmasi

## Bo'limlar

- `/index` - Dashboard
- `/sotuv` - Sotuv bo'limi
- `/chiqim` - Chiqim bo'limi
- `/mahsulot` - Mahsulot bo'limi

Dashboard ko'rsatkichlari:
- Kirim
- Chiqim (faqat `chiqim` bo'limida kiritilgan xarajatlar yig'indisi)
- Sof foyda
- Jami xarid
- Ombordagi qolgan tovarlar

## Ishga tushirish

```powershell
cd c:\Users\Zevs\Desktop\lesssons\04.03
python app.py
```

Brauzer:
- `http://localhost:8080`

Login:
- Username: `admin`
- Password: `admin123`

## Texnologiya

- Python `http.server`
- SQLite (`crm.db`)
- Vanilla HTML/CSS/JS
