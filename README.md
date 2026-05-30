<div align="center">

# 🛡️ HanogtVPN

**Güvenli, Hızlı ve Modern VPN Çözümü**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Lisans](https://img.shields.io/badge/Lisans-MIT-10B981?style=for-the-badge)](LICENSE)
[![Sürüm](https://img.shields.io/badge/Sürüm-0.0.1-7C3AED?style=for-the-badge)]()
[![Şifreleme](https://img.shields.io/badge/Şifreleme-AES--256--GCM-EF4444?style=for-the-badge)]()

*Uçtan uca şifrelenmiş, profesyonel arayüzlü, açık kaynak VPN uygulaması*

</div>

---

## 📋 İçindekiler

- [🚀 Özellikler](#-özellikler)
- [🏗️ Mimari](#️-mimari)
- [🛠️ Kurulum](#️-kurulum)
- [📖 Kullanım](#-kullanım)
- [🔐 Güvenlik](#-güvenlik)
- [🏛️ Proje Yapısı](#️-proje-yapısı)
- [🧪 Testler](#-testler)
- [🤝 Katkıda Bulunma](#-katkıda-bulunma)
- [📄 Lisans](#-lisans)

---

## 🚀 Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🔒 **AES-256-GCM Şifreleme** | Askeri düzeyde uçtan uca şifreleme |
| 🔑 **ECDH Anahtar Değişimi** | Perfect Forward Secrecy (PFS) desteği |
| 🛡️ **RSA-2048 Kimlik Doğrulama** | Sunucu kimliğinin kriptografik doğrulanması |
| 🎨 **Modern GUI** | CustomTkinter ile premium koyu/açık tema arayüzü |
| 🌐 **Çoklu Sunucu** | İstanbul, Frankfurt, Amsterdam, Londra, New York |
| 📡 **Gerçek Zamanlı Ping** | Sunucu gecikmelerinin anlık ölçümü |
| 🔄 **Otomatik Yeniden Bağlanma** | Bağlantı kesildiğinde otomatik kurtarma |
| 🚫 **Kill Switch** | VPN düştüğünde internet erişimini engelleme |
| 🛡️ **DNS Sızıntı Koruması** | DNS sorgularının tünelden yönlendirilmesi |
| 📊 **Canlı İstatistikler** | Upload/download hızı, süre, veri kullanımı |
| 📋 **Detaylı Loglama** | Renk kodlu, filtrelenebilir gerçek zamanlı loglar |
| 💓 **Heartbeat Sistemi** | Bağlantı canlılık kontrolü |
| ⚙️ **Kapsamlı Ayarlar** | Şifreleme, protokol, güvenlik, genel ayarlar |
| 🌗 **Tema Desteği** | Koyu ve açık tema arasında geçiş |

---

## 🏗️ Mimari

```
┌─────────────────┐         Şifreli Tünel          ┌─────────────────┐
│   HanogtVPN     │◄──────────────────────────────►│   HanogtVPN     │
│   İstemci       │   ECDH + AES-256-GCM + RSA     │   Sunucu        │
│   (GUI)         │                                 │   (Daemon)      │
└─────────────────┘                                 └─────────────────┘
        │                                                   │
   ┌────┴────┐                                        ┌────┴────┐
   │ SOCKS5  │                                        │ Trafik  │
   │ Proxy   │                                        │Yönlend. │
   └─────────┘                                        └─────────┘
```

### Bağlantı Akışı

1. **ECDH Anahtar Değişimi** — İstemci ve sunucu ECDH keypair oluşturur
2. **RSA İmza Doğrulama** — Sunucu, ECDH anahtarını RSA ile imzalar
3. **Oturum Anahtarı Türetme** — HKDF-SHA256 ile ortak sır türetilir
4. **Şifreli Tünel** — Tüm trafik AES-256-GCM ile şifrelenir
5. **Heartbeat** — Periyodik canlılık kontrolü

---

## 🛠️ Kurulum

### Gereksinimler

- **Python 3.9** veya üzeri
- **pip** paket yöneticisi

### Adımlar

```bash
# 1. Projeyi klonlayın
git clone https://github.com/kullanici/HanogtVPN.git
cd HanogtVPN

# 2. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 3. (Opsiyonel) RSA sunucu anahtarlarını oluşturun
python scripts/generate_keys.py
```

### Kurulum Doğrulama

```bash
# Testleri çalıştırarak kurulumu doğrulayın
python -m pytest tests/ -v
```

---

## 📖 Kullanım

### 🖥️ İstemci Başlatma

```bash
python -m hanogtvpn.client.app
```

**GUI Arayüzü:**
- **Ana Ekran** — Bağlantı durumu, istatistikler ve bağlan butonu
- **Sunucular** — Sunucu listesi, ping bilgileri, manuel sunucu ekleme
- **Ayarlar** — Şifreleme, protokol, güvenlik ve genel ayarlar
- **Loglar** — Gerçek zamanlı renk kodlu log görüntüleyici

### 🖧 Sunucu Başlatma

```bash
# Varsayılan ayarlarla
python -m hanogtvpn.server.server

# Özel ayarlarla
python -m hanogtvpn.server.server --host 0.0.0.0 --port 9999 --max-clients 100
```

**Sunucu Parametreleri:**

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `--host` | `0.0.0.0` | Dinlenecek IP adresi |
| `--port` | `9999` | Dinlenecek port |
| `--max-clients` | `50` | Maksimum eş zamanlı bağlantı |

### 🔑 RSA Anahtar Oluşturma

```bash
python scripts/generate_keys.py
```

Bu komut `keys/` dizininde RSA-2048 anahtar çifti oluşturur:
- `server_private.pem` — Özel anahtar (GİZLİ tutun!)
- `server_public.pem` — Genel anahtar

---

## 🔐 Güvenlik

### Şifreleme Katmanları

| Katman | Teknoloji | Amaç |
|--------|-----------|------|
| **Anahtar Değişimi** | ECDH (SECP384R1) | Perfect Forward Secrecy |
| **Veri Şifreleme** | AES-256-GCM | Authenticated Encryption |
| **Sunucu Kimliği** | RSA-2048 PSS | Kimlik Doğrulama |
| **Anahtar Türetme** | HKDF-SHA256 | Güvenli anahtar genişletme |
| **Replay Koruması** | Rastgele Nonce | Tekrar saldırısı engelleme |

### Paket Formatı

```
[4 byte: Uzunluk][1 byte: Tip][12 byte: Nonce][Şifreli Veri][16 byte: GCM Tag]
```

### Güvenlik Özellikleri

- ✅ **Perfect Forward Secrecy (PFS)** — Her oturum benzersiz ECDH anahtarları kullanır
- ✅ **Authenticated Encryption** — AES-GCM hem şifreleme hem bütünlük sağlar
- ✅ **Sunucu Doğrulama** — RSA imzası ile MITM saldırılarına karşı koruma
- ✅ **Replay Koruması** — Her paket benzersiz 12-byte nonce içerir
- ✅ **Atomik Dosya Yazımı** — Ayar dosyası bozulmasına karşı koruma
- ✅ **Girdi Doğrulama** — Tüm kullanıcı girdileri doğrulanır ve temizlenir
- ✅ **Thread-Safe GUI** — `after()` ile güvenli thread iletişimi

> ⚠️ **Uyarı:** `keys/` dizinindeki özel anahtarları asla paylaşmayın ve versiyon kontrolüne eklemeyin!

---

## 🏛️ Proje Yapısı

```
HanogtVPN/
├── 📄 README.md                      Bu dosya
├── 📄 LICENSE                        MIT Lisansı
├── 📄 requirements.txt              Python bağımlılıkları
├── 📄 setup.py                      Paket kurulum dosyası
├── 📄 .gitignore                    Git hariç tutma kuralları
│
├── 📦 hanogtvpn/                     Ana paket
│   ├── 🔧 core/                      Çekirdek modüller
│   │   ├── constants.py              Sabitler ve enumlar
│   │   ├── crypto.py                 Şifreleme motoru (AES, ECDH, RSA)
│   │   ├── protocol.py               İkili protokol
│   │   └── logger.py                 Loglama sistemi
│   │
│   ├── 🖥️ client/                    İstemci uygulaması
│   │   ├── app.py                    Ana uygulama penceresi
│   │   ├── connection.py             Bağlantı yöneticisi
│   │   ├── settings.py               Ayar yönetimi
│   │   └── ui/                       Arayüz bileşenleri
│   │       ├── theme.py              Tema yönetimi
│   │       ├── main_panel.py         Ana dashboard
│   │       ├── settings_panel.py     Ayarlar paneli
│   │       ├── logs_panel.py         Log görüntüleyici
│   │       └── server_list.py        Sunucu listesi
│   │
│   ├── 🖧 server/                    Sunucu uygulaması
│   │   ├── server.py                 Ana sunucu
│   │   └── handler.py                İstemci işleyici
│   │
│   └── 🔧 utils/                     Yardımcı araçlar
│       ├── network.py                Ağ yardımcıları
│       └── validators.py             Girdi doğrulama
│
├── 🧪 tests/                         Test paketi
│   ├── test_crypto.py                Şifreleme testleri
│   ├── test_protocol.py              Protokol testleri
│   └── test_validators.py            Doğrulama testleri
│
└── 📜 scripts/
    └── generate_keys.py              RSA anahtar oluşturucu
```

---

## 🧪 Testler

```bash
# Tüm testleri çalıştır
python -m pytest tests/ -v

# Sadece şifreleme testleri
python -m pytest tests/test_crypto.py -v

# Sadece protokol testleri
python -m pytest tests/test_protocol.py -v

# Sadece doğrulama testleri
python -m pytest tests/test_validators.py -v

# Kapsam raporu ile
python -m pytest tests/ -v --cov=hanogtvpn
```

### Test Kapsamı

| Modül | Test Sayısı | Kapsam |
|-------|------------|--------|
| `core/crypto.py` | 13 | Tam |
| `core/protocol.py` | 9 | Tam |
| `utils/validators.py` | 9 | Tam |

---

## 🤝 Katkıda Bulunma

Katkılarınızı memnuniyetle karşılıyoruz! İşte nasıl katkıda bulunabileceğiniz:

### Adımlar

1. **Fork** yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik: açıklama'`)
4. Branch'ınızı push edin (`git push origin feature/yeni-ozellik`)
5. **Pull Request** açın

### Kurallar

- 📝 Kod yorumlarını İngilizce yazın
- 🧪 Yeni özellikler için test ekleyin
- 🔒 Güvenlikle ilgili değişikliklerde ekstra dikkatli olun
- 📋 Pull request açıklamasında değişiklikleri detaylı anlatın
- 🎨 Mevcut kod stiline uyun

### Güvenlik Açıkları

Güvenlik açığı bulduysanız lütfen public issue açmak yerine doğrudan iletişime geçin.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

```
MIT License — Dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz.
```

---

## 👨‍💻 Geliştirici

**HanogtVPN Team** tarafından ❤️ ile geliştirilmiştir.

---

<div align="center">

**⭐ Bu projeyi beğendiyseniz yıldız vermeyi unutmayın! ⭐**

</div>
