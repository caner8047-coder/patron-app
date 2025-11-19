import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from datetime import date, datetime, timedelta

from db import get_conn, get_settings
from utils import month_date_range


class DashboardTab(ttk.Frame):
    """
    Dashboard – Seçilen ay için personel bazlı özet:
    - Çalışma günü, teorik saat, devamsızlık saati, toplam saat
    - Net maaş
    Grafik: Toplam saat ve devamsızlık saatleri bar chart olarak
    """

    def __init__(self, master):
        super().__init__(master)
        self.build_ui()

    # -------------------------------------------------
    #   UI
    # -------------------------------------------------
    def build_ui(self):
        filter_frame = ttk.LabelFrame(self, text="Filtre")
        filter_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(filter_frame, text="Yıl:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(filter_frame, textvariable=self.year_var, width=6)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="Ay:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.month_var = tk.StringVar(value=str(date.today().month))
        ttk.Entry(filter_frame, textvariable=self.month_var, width=4)\
            .grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(filter_frame, text="Göster", command=self.load_dashboard)\
            .grid(row=0, column=4, padx=10, pady=5)

        self.info_label = ttk.Label(filter_frame, text="", foreground="gray")
        self.info_label.grid(row=1, column=0, columnspan=5, padx=5, pady=(0, 5), sticky="w")

        # Grafik alanı
        self.chart_frame = ttk.Frame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -------------------------------------------------
    #   Veri & Grafik
    # -------------------------------------------------
    def load_dashboard(self):
        # Önce mevcut grafikleri temizle
        for w in self.chart_frame.winfo_children():
            w.destroy()

        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            if not (1 <= month <= 12):
                raise ValueError
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir yıl ve ay girin (örn. 2025 / 11).")
            return

        month_start, month_end = month_date_range(year, month)
        daily_hours, overtime_coef, include_weekends = get_settings()

        conn = get_conn()
        c = conn.cursor()

        # Çalışan listesi
        c.execute("""
            SELECT id, name, hourly_rate, start_date
            FROM employees
            ORDER BY name
        """)
        employees = c.fetchall()

        names = []
        total_hours_list = []
        missing_hours_list = []

        today = date.today()

        def count_working_days(start_date_str: str) -> int:
            if not start_date_str:
                return 0
            try:
                start_date_val = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except Exception:
                return 0

            last_day = month_end - timedelta(days=1)

            # Gelecekteki günleri sayma
            if year == today.year and month == today.month and today < last_day:
                last_day = today

            period_start = max(month_start, start_date_val)
            if period_start > last_day:
                return 0

            d = period_start
            days = 0
            while d <= last_day:
                if include_weekends or d.weekday() < 5:
                    days += 1
                d += timedelta(days=1)
            return days

        try:
            for emp_id, name, hourly_rate, start_str in employees:
                work_days = count_working_days(start_str)
                theoretical_hours = work_days * daily_hours

                # Devamsızlık saatleri (attendance_logs)
                c.execute("""
                    SELECT COALESCE(SUM(hours), 0)
                    FROM attendance_logs
                    WHERE employee_id = ?
                      AND date >= ? AND date < ?
                """, (emp_id, month_start.isoformat(), month_end.isoformat()))
                row = c.fetchone()
                missing_hours = float(row[0] or 0)

                total_hours = max(theoretical_hours - missing_hours, 0.0)

                # Hiç çalışmamış / teorik sıfırsa grafiğe eklemeyebiliriz
                if theoretical_hours == 0 and missing_hours == 0:
                    continue

                names.append(name)
                total_hours_list.append(total_hours)
                missing_hours_list.append(missing_hours)
        finally:
            conn.close()

        if not names:
            self.info_label.config(
                text=f"{month:02d}/{year} için veri bulunamadı.",
                foreground="red",
            )
            return

        self.info_label.config(
            text=f"Dönem: {month:02d}/{year} · Personel sayısı: {len(names)}",
            foreground="black",
        )

        # Matplotlib Figure
        fig = Figure(figsize=(9, 4), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)

        x = range(len(names))

        # Sol grafik: Toplam saat
        ax1.bar(x, total_hours_list)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(names, rotation=45, ha="right")
        ax1.set_title("Toplam Çalışma Saatleri")
        ax1.set_ylabel("Saat")

        # Sağ grafik: Devamsızlık saatleri
        ax2.bar(x, missing_hours_list)
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(names, rotation=45, ha="right")
        ax2.set_title("Devamsızlık (Eksik Saat)")
        ax2.set_ylabel("Saat")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
