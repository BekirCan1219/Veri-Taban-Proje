# 📚 Smart Library Management System

Bu proje, **Flask + MSSQL** kullanılarak geliştirilmiş bir **Kütüphane Yönetim Sistemi**dir.  
Sistemde kullanıcılar kitap ödünç alabilir, iadelerini yapabilir ve gecikme durumunda otomatik ceza oluşur.  
Admin paneli üzerinden tüm sistem merkezi olarak yönetilir.

---

## 🚀 Özellikler

### 👤 Kullanıcı
- Kitap listesini görüntüleme
- Kitap ödünç alma
- Aldığı kitapları iade etme
- Gecikme cezalarını görüntüleme
- Ceza ödeme (online simülasyon)

### 🛠️ Admin
- Kitap ekleme / düzenleme / silme
- Aktif ödünçleri ve gecikenleri görüntüleme
- Gecikme cezalarını görüntüleme (kimin, ne kadar)
- Gecikme kontrolünü manuel veya otomatik çalıştırma
- Bildirim ve mail loglarını izleme

---

## ⏱️ Otomatik Gecikme Kontrolü
Sistemde **APScheduler** kullanılarak belirli aralıklarla:
- Geciken ödünçler tespit edilir
- Teslim tarihi yaklaşanlar kontrol edilir
- Kullanıcılara otomatik e-posta gönderilir
- Tüm işlemler `notification_logs` tablosuna kaydedilir

---

## 🧮 Ceza (Penalty) Sistemi
- Gecikme durumunda otomatik ceza oluşturulur
- Günlük ceza ücreti hesaplanır
- Kullanıcı ödeme yaptığında ceza `is_paid = 1` olur
- Admin paneli anlık olarak güncellenir

---

## 🗄️ Kullanılan Teknolojiler

- **Backend:** Flask (Python)
- **ORM:** SQLAlchemy
- **Veritabanı:** Microsoft SQL Server
- **Mail:** Flask-Mail
- **Scheduler:** APScheduler
- **Frontend:** HTML / CSS / Vanilla JavaScript
- **Auth:** Session tabanlı yetkilendirme

---

## 📡 API Endpoint Örnekleri

### Kullanıcı
- `GET /web/api/books`
- `POST /web/api/borrow`
- `POST /web/api/borrow/return/<id>`
- `GET /web/api/penalties/my`
- `POST /web/api/penalties/pay/<id>`

### Admin
- `GET /web/api/admin/stats`
- `GET /web/api/admin/overdue`
- `GET /web/api/admin/penalties`
- `POST /web/api/admin/run-late-check`

---

## 🧠 Mimari Yapı

```text
app/
├── controllers/
│   └── web_api_controller.py
├── models/
│   ├── book.py
│   ├── borrow.py
│   ├── penalty.py
│   └── notification_log.py
├── services/
│   ├── mail_service.py
│   └── scheduler.py
├── templates/
│   ├── admin.html
│   └── penalties.html
└── extensions.py
