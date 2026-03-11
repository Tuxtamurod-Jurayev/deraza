# Eshik-Deraza CRM (MVP)

Bu loyiha eshik-deraza savdo bo'limi uchun oddiy CRM:

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
- Ko'p sahifali bo'limlar:
  - `/index` - Dashboard
  - `/sotuv` - Sotuv bo'limi
  - `/chiqim` - Chiqim bo'limi
  - `/mahsulot` - Mahsulot bo'limi
- Dashboard:
  - Kirim
  - Chiqim (faqat `chiqim` bo'limida kiritilgan xarajatlar yig'indisi)
  - Sof foyda
  - Jami xarid
  - Ombordagi qolgan tovarlar

## Ishga tushirish

1. Loyihaga kiring:

```powershell
cd c:\Users\Zevs\Desktop\lesssons\04.03
```

2. Serverni ishga tushiring:

```powershell
python app.py
```

3. Brauzerda oching:

`http://localhost:8080`

## Login

- Username: `admin`
- Password: `admin123`

## Texnologiya

- Python `http.server`
- SQLite (`crm.db`)
- Vanilla HTML/CSS/JS
