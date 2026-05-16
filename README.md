# Radmin Voice - Pro Fix

Bu proje, yerel ağlar (LAN, Ethernet veya Radmin VPN) üzerinde internette bulunan harici bir sunucuya ihtiyaç duymadan, doğrudan bilgisayarlar arasında (P2P) çalışan düşük gecikmeli bir sesli sohbet uygulamasıdır. **Tkinter**, **PyAudio** ve **NumPy** kütüphaneleri kullanılarak geliştirilmiş olup, ağdaki paket dalgalanmalarını sönümleyen Jitter Buffer ve akıllı ses tetikleme (VOX) mekanizmalarına sahiptir.

## 🚀 Özellikler
* **Otomatik Cihaz Keşfi (Auto-Peer Discovery):** Arka planda çalışan UDP Broadcast mekanizması sayesinde aynı yerel ağdaki veya Radmin ağındaki diğer aktif kullanıcıları otomatik olarak tespit eder ve listeler.
* **Jitter Buffer (Gecikme/Kelimelerin Kesilmesini Önleme):** Ağdaki paket varisansını (gecikme dalgalanmalarını) absorbe etmek için thread-safe bir `queue.Queue` yapısı kullanır. Bu sayede ses akışı takılmadan, stabil ve pürüzsüz aktarılır.
* **VOX (Akıllı Mikrofon Tetiklemesi):** Ayarlanabilir ses eşiği filtresi ve cümle sonlarının kesilmesini önleyen özel tutma süresi (`HOLD_TIME = 1.5s`) ile ortamda sessizlik olduğunda ağa paket göndermeyi durdurur; hem işlemciyi hem ağı rahatlatır.
* **Anlık VU Metre (Audio Visualizer):** Mikrofondan giden ses şiddetini Tkinter arayüzünde anlık ve canlı bir Progress Bar grafiği olarak gösterir.
* **Donanımsal Ayarlayıcılar:** Kullanıcı arayüzündeki kaydırıcılar (sliders) sayesinde Mikrofon Kazancı (Gain Amplification) ve Gelen Hoparlör Ses Seviyesi anlık olarak optimize edilebilir.

## 🛠️ Ağ ve Ses Mimarisi
Uygulama, arayüzün donmasını engellemek amacıyla tamamen asenkron çoklu iş parçacığı (Multi-threading) mimarisi üzerine kurulmuştur:

* **Keşif İş Parçacığı (Discovery):** Her saniye `55556` portundan ağa `"HELLO"` paketi yayınlar (Broadcast) ve 5 saniye boyunca sinyal alınamayan kullanıcıları listeden otomatik olarak düşürür.
* **Ses Yakalama ve Filtreleme:** `PyAudio` vasıtasıyla mikrofondan 1024'lük bloklar halinde `22050Hz` frekansında ses okunur. `NumPy` ile bu sesin mutlak ortalama genliği hesaplanır. Belirlenen eşiği (Threshold) aşarsa, ses verisi **UDP Soketleri** (`socket.SOCK_DGRAM`) üzerinden listedeki tüm eşlere (peers) anlık gönderilir.
* **Ses Oynatma Hattı (Pipeline):** Gelen paketler `receive_audio_to_queue` ile yakalanır ve hoparlör hacmi çarpımı yapıldıktan sonra kuyruğa iletilir. `play_audio_from_queue` ise bu kuyruktaki ham ses verisini kesintisiz bir biçimde ses çıkış birimine yazar.

## 💻 Kullanılan Teknolojiler
* **Arayüz Frameworkü:** Tkinter & TTK
* **Ses ve Veri İşleme:** `PyAudio`, `NumPy`
* **Ağ Programlama:** Python `socket` modülü (Hız için UDP Protokolü)
* **Eşzamanlılık:** `threading`, `queue`

### 🚀 HIZLI KULLANIM (.EXE)
**Python veya herhangi bir kütüphane kurmakla uğraşmak istemiyor musunuz?**
Uygulamanın tek tıkla çalışan hazır `.exe` sürümünü doğrudan bilgisayarınıza indirip kullanabilirsiniz:

👉 **[Güncel .EXE Sürümünü İndirmek İçin Tıklayın (Releases)](../../releases/latest)**

---

## 🔧 Kurulum ve Çalıştırma

### Sistem Gereksinimleri
Ham ses verilerinin işlenebilmesi için `PyAudio` kütüphanesinden önce sisteminizde **PortAudio** sürücülerinin kurulu olması gerekmektedir. 
* **Windows:** Genellikle kütüphane ile birlikte gömülü kurulur.
* **Linux (Ubuntu/Debian):** `sudo apt-get install portaudio19-dev`

Gerekli Python paketlerini yükleyin:
```bash
pip install pyaudio numpy
