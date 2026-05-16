import socket
import threading
import pyaudio
import tkinter as tk
from tkinter import ttk
import time
import numpy as np
import queue

# --- AYARLAR ---
CHUNK = 1024  # Paket boyutunu biraz artırdık (Daha stabil akış)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 22050
VOICE_PORT = 55555
DISCOVERY_PORT = 55556
BROADCAST_IP = "255.255.255.255"

INITIAL_THRESHOLD = 120
HOLD_TIME = 1.5 # Cümle sonlarının kesilmemesi için süreyi biraz uzattık

def get_radmin_ip():
    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if ip.startswith("26."):
                return ip
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

MY_IP = get_radmin_ip()

class StableVoiceChat:
    def __init__(self, root):
        self.root = root
        self.root.title("Radmin Voice - Pro Fix")
        self.root.geometry("380x620")
        self.root.configure(bg="#000")

        self.peers = {}
        self.is_mic_on = True
        
        # --- SES AYAR DEĞİŞKENLERİ ---
        self.threshold = INITIAL_THRESHOLD
        self.mic_gain = 7.0
        self.speaker_vol = 1.0
        self.mic_open_until = 0 

        # Jitter Buffer için Kuyruk yapısı
        self.audio_queue = queue.Queue(maxsize=30)

        self.p = pyaudio.PyAudio()
        self.stream_in = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                                    input=True, frames_per_buffer=CHUNK)
        self.stream_out = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                                     output=True, frames_per_buffer=CHUNK)

        # Network Sockets
        self.voice_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.voice_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_sock.bind(("0.0.0.0", VOICE_PORT))
        
        self.disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.disc_sock.bind(("0.0.0.0", DISCOVERY_PORT))

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.setup_ui()
        
        # Threads
        threading.Thread(target=self.broadcast_presence, daemon=True).start()
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.receive_audio_to_queue, daemon=True).start() # Değişti
        threading.Thread(target=self.play_audio_from_queue, daemon=True).start()  # Yeni eklendi
        threading.Thread(target=self.send_audio, daemon=True).start()
        threading.Thread(target=self.update_peer_list, daemon=True).start()

    def setup_ui(self):
        tk.Label(self.root, text="SESLİ SOHBET (STABİL)", fg="#00FF7F", bg="black", 
                 font=("Courier", 14, "bold")).pack(pady=10)

        tk.Label(self.root, text=f"Senin IP: {MY_IP}", fg="#444", bg="black").pack()

        self.vu_bar = ttk.Progressbar(self.root, length=250, mode='determinate', maximum=1000)
        self.vu_bar.pack(pady=10)

        tk.Label(self.root, text="Mikrofon Tetikleme Eşiği:", fg="#888", bg="black").pack()
        self.thresh_slider = tk.Scale(self.root, from_=0, to=1000, orient=tk.HORIZONTAL, 
                                     bg="#111", fg="white", highlightthickness=0, 
                                     command=lambda v: setattr(self, 'threshold', int(v)))
        self.thresh_slider.set(self.threshold)
        self.thresh_slider.pack(fill=tk.X, padx=40)

        tk.Label(self.root, text="Mikrofon Kazancı (Gain):", fg="#888", bg="black").pack(pady=(10,0))
        self.gain_slider = tk.Scale(self.root, from_=1.0, to=15.0, resolution=0.5, orient=tk.HORIZONTAL, 
                                     bg="#111", fg="#00BFFF", highlightthickness=0, 
                                     command=lambda v: setattr(self, 'mic_gain', float(v)))
        self.gain_slider.set(self.mic_gain)
        self.gain_slider.pack(fill=tk.X, padx=40)

        tk.Label(self.root, text="Gelen Ses Seviyesi:", fg="#888", bg="black").pack(pady=(10,0))
        self.speaker_slider = tk.Scale(self.root, from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, 
                                     bg="#111", fg="#FFD700", highlightthickness=0, 
                                     command=lambda v: setattr(self, 'speaker_vol', float(v)))
        self.speaker_slider.set(self.speaker_vol)
        self.speaker_slider.pack(fill=tk.X, padx=40)

        self.peer_listbox = tk.Listbox(self.root, bg="#0a0a0a", fg="#00FF7F", borderwidth=0)
        self.peer_listbox.pack(pady=15, fill=tk.BOTH, expand=True, padx=20)

        self.btn_mic = tk.Button(self.root, text="MİKROFON: AÇIK", command=self.toggle_mic, 
                                 bg="#111", fg="#00FF7F", width=20, font=("Arial", 10, "bold"))
        self.btn_mic.pack(pady=10)

    def toggle_mic(self):
        self.is_mic_on = not self.is_mic_on
        self.btn_mic.config(text=f"MİKROFON: {'AÇIK' if self.is_mic_on else 'KAPALI'}", 
                            fg="#00FF7F" if self.is_mic_on else "#FF4500")

    def broadcast_presence(self):
        while True:
            try: 
                self.send_sock.sendto(b"HELLO", (BROADCAST_IP, DISCOVERY_PORT))
            except: pass
            time.sleep(1)

    def listen_for_peers(self):
        while True:
            try:
                data, addr = self.disc_sock.recvfrom(1024)
                if data == b"HELLO" and addr[0] != MY_IP:
                    self.peers[addr[0]] = time.time()
            except: pass

    def update_peer_list(self):
        while True:
            now = time.time()
            self.peer_listbox.delete(0, tk.END)
            for ip, last_seen in list(self.peers.items()):
                if now - last_seen < 5:
                    self.peer_listbox.insert(tk.END, f"● {ip}")
                else: 
                    del self.peers[ip]
            time.sleep(2)

    def send_audio(self):
        while True:
            try:
                if self.is_mic_on:
                    raw_data = self.stream_in.read(CHUNK, exception_on_overflow=False)
                    audio_array = np.frombuffer(raw_data, dtype=np.int16)
                    
                    vol = np.abs(audio_array.astype(np.float32)).mean()
                    
                    try:
                        self.root.after(0, lambda v=vol: self.vu_bar.configure(value=v))
                    except: pass
                    
                    if vol > self.threshold:
                        self.mic_open_until = time.time() + HOLD_TIME
                    
                    if time.time() < self.mic_open_until:
                        # Mikrofon gain uygulama
                        boosted = (audio_array.astype(np.float32) * self.mic_gain).clip(-32768, 32767).astype(np.int16)
                        data = boosted.tobytes()
                        for ip in list(self.peers.keys()):
                            self.voice_sock.sendto(data, (ip, VOICE_PORT))
            except: pass

    def receive_audio_to_queue(self):
        """Gelen ses paketlerini alır ve işlemden geçirip kuyruğa atar."""
        while True:
            try:
                data, addr = self.voice_sock.recvfrom(4096)
                if addr[0] == MY_IP:
                    continue
                
                # Ses işleme (Speaker volume)
                in_array = np.frombuffer(data, dtype=np.int16)
                adjusted = (in_array.astype(np.float32) * self.speaker_vol).clip(-32768, 32767).astype(np.int16)
                
                # Kuyruğa ekle
                if not self.audio_queue.full():
                    self.audio_queue.put(adjusted.tobytes())
            except: pass

    def play_audio_from_queue(self):
        """Kuyruktaki sesleri stabil bir akışla hoparlöre basar."""
        while True:
            try:
                # Kuyruk çok boşalırsa minik bir bekleme yap (jitter önleme)
                if self.audio_queue.qsize() < 2:
                    time.sleep(0.01)
                
                data = self.audio_queue.get(timeout=1)
                self.stream_out.write(data)
            except:
                continue

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TProgressbar", background="#00FF7F", troughcolor="#111")
    app = StableVoiceChat(root)
    root.mainloop()