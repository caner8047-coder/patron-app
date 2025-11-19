import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import shutil

from db import get_settings, update_settings, DB_NAME


class SettingsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.daily_hours_var = tk.StringVar()
        self.overtime_coef_var = tk.StringVar()
        self.include_weekends_var = tk.IntVar(value=1)

        self.build_ui()
        self.load_settings()

    def build_ui(self):
        # --- GENEL AYARLAR ---
        frame = ttk.LabelFrame(self, text="Genel Ayarlar")
        frame.pack(fill="x", padx=10, pady=10)

        # Günlük çalışma saati
        ttk.Label(frame, text="Günlük çalışma saati:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame, textvariable=self.daily_hours_var, width=10).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )
        ttk.Label(frame, text="saat").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Mesai katsayısı
        ttk.Label(frame, text="Mesai katsayısı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame, textvariable=self.overtime_coef_var, width=10).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )
        ttk.Label(frame, text="(ör: 1.5)").grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Hafta sonu dahil mi
        ttk.Checkbutton(
            frame,
            text="Hafta sonları çalışma gününe dahil olsun",
            variable=self.include_weekends_var,
        ).grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        info = (
            "Notlar:\n"
            "- Günlük çalışma saati, teorik saat hesabında kullanılır.\n"
            "- Mesai katsayısı = saatlik ücret × katsayı (örn: 1.5).\n"
            "- Hafta sonları dahil ise, cumartesi/pazar da çalışma günü sayılır."
        )
        ttk.Label(frame, text=info, justify="left").grid(
            row=3, column=0, columnspan=3, padx=5, pady=(5, 10), sticky="w"
        )

        btn = ttk.Button(self, text="Ayarları Kaydet", command=self.save_settings)
        btn.pack(pady=(0, 10))

        # --- VERİTABANI YEDEĞİ ---
        backup_frame = ttk.LabelFrame(self, text="Veritabanı Yedeği")
        backup_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(
            backup_frame,
            text=(
                "Mevcut veritabanını bir .db dosyası olarak yedekleyebilirsiniz.\n"
                "Öneri: Yedekleri tarih/saat içeren isimle saklayın."
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(backup_frame, text=f"Aktif veritabanı dosyası: {DB_NAME}").grid(
            row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w"
        )

        ttk.Button(backup_frame, text="Veritabanını Yedekle", command=self.backup_db).grid(
            row=2, column=0, padx=5, pady=8, sticky="w"
        )

    def load_settings(self):
        daily_hours, overtime_coef, include_weekends = get_settings()
        self.daily_hours_var.set(str(daily_hours))
        self.overtime_coef_var.set(str(overtime_coef))
        self.include_weekends_var.set(int(include_weekends))

    def save_settings(self):
        dh_str = self.daily_hours_var.get().strip()
        oc_str = self.overtime_coef_var.get().strip()

        if not dh_str or not oc_str:
            messagebox.showerror("Hata", "Günlük çalışma saati ve mesai katsayısı boş bırakılamaz.")
            return

        try:
            daily_hours = float(dh_str.replace(",", "."))
            overtime_coef = float(oc_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli sayısal değerler girin.")
            return

        if daily_hours <= 0:
            messagebox.showerror("Hata", "Günlük çalışma saati 0'dan büyük olmalıdır.")
            return

        if overtime_coef < 1.0:
            messagebox.showerror("Hata", "Mesai katsayısı en az 1.0 olmalıdır.")
            return

        include_weekends = int(self.include_weekends_var.get())

        update_settings(daily_hours, overtime_coef, include_weekends)
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

    def backup_db(self):
        """DB dosyasını kullanıcıya seçtirdiği konuma kopyalar."""
        # Önerilen dosya adı: personel_takip_yedek_YYYYMMDD_HHMMSS.db
        default_name = f"personel_takip_yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Veritabanı", "*.db"), ("Tüm Dosyalar", "*.*")],
            initialfile=default_name,
            title="Veritabanı Yedeğini Kaydet",
        )

        if not file_path:
            return

        try:
            shutil.copyfile(DB_NAME, file_path)
            messagebox.showinfo("Başarılı", f"Veritabanı yedeği oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Yedek alınırken hata oluştu:\n{e}")
