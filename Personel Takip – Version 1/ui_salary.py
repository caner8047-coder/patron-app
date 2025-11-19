import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta

from db import get_conn, get_settings
from utils import month_date_range, tl


class SalaryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        # Dışa aktarım için son hesaplanan satırları tutuyoruz
        self.last_rows = []

        self.build_ui()

    # -------------------------------------------------
    #   UI
    # -------------------------------------------------
    def build_ui(self):
        # Ay seçimi
        top_frame = ttk.LabelFrame(self, text="Ay Seçimi")
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ttk.Label(top_frame, text="Yıl:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(top_frame, textvariable=self.year_var, width=6)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(top_frame, text="Ay:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.month_var = tk.StringVar(value=str(date.today().month))
        ttk.Entry(top_frame, textvariable=self.month_var, width=4)\
            .grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(top_frame, text="Hesapla", command=self.calculate_salaries)\
            .grid(row=0, column=4, padx=10, pady=5)

        # Liste
        list_frame = ttk.LabelFrame(self, text="Aylık Maaş, Avans ve Mesai Özeti")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "employee",
            "days",
            "theoretical_hours",
            "missing_hours",
            "total_hours",
            "salary",
            "overtime",
            "advance",
            "net_salary",
        )
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.tree.heading("employee", text="Personel")
        self.tree.heading("days", text="Gün")
        self.tree.heading("theoretical_hours", text="Teorik Saat")
        self.tree.heading("missing_hours", text="Eksik Saat")
        self.tree.heading("total_hours", text="Toplam Saat")
        self.tree.heading("salary", text="Maaş")
        self.tree.heading("overtime", text="Mesai")
        self.tree.heading("advance", text="Avans Kesinti")
        self.tree.heading("net_salary", text="Net Maaş")

        self.tree.column("employee", width=150)
        self.tree.column("days", width=60, anchor="center")
        self.tree.column("theoretical_hours", width=90, anchor="center")
        self.tree.column("missing_hours", width=80, anchor="center")
        self.tree.column("total_hours", width=80, anchor="center")
        self.tree.column("salary", width=110, anchor="e")
        self.tree.column("overtime", width=110, anchor="e")
        self.tree.column("advance", width=110, anchor="e")
        self.tree.column("net_salary", width=110, anchor="e")

        self.tree.pack(fill="both", expand=True)

        # Kasa özeti
        summary_frame = ttk.LabelFrame(self, text="Kasa Özeti (Seçilen Ay)")
        summary_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.total_salary_var = tk.StringVar(value="0,00 ₺")
        self.total_overtime_var = tk.StringVar(value="0,00 ₺")
        self.total_advance_var = tk.StringVar(value="0,00 ₺")
        self.total_net_var = tk.StringVar(value="0,00 ₺")

        ttk.Label(summary_frame, text="Toplam Maaş:")\
            .grid(row=0, column=0, padx=5, pady=3, sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_salary_var)\
            .grid(row=0, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(summary_frame, text="Toplam Mesai:")\
            .grid(row=0, column=2, padx=5, pady=3, sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_overtime_var)\
            .grid(row=0, column=3, padx=5, pady=3, sticky="w")

        ttk.Label(summary_frame, text="Toplam Avans Kesinti:")\
            .grid(row=1, column=0, padx=5, pady=3, sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_advance_var)\
            .grid(row=1, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(summary_frame, text="Toplam Net Maaş (Kasadan Çıkacak):")\
            .grid(row=1, column=2, padx=5, pady=3, sticky="w")
        ttk.Label(summary_frame, textvariable=self.total_net_var)\
            .grid(row=1, column=3, padx=5, pady=3, sticky="w")

        # Dışa aktarım butonları
        export_frame = ttk.Frame(self)
        export_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(export_frame, text="CSV Olarak Dışa Aktar", command=self.export_csv)\
            .pack(side="left", padx=5)
        ttk.Button(export_frame, text="Bordro (Excel)", command=self.export_excel)\
            .pack(side="left", padx=5)
        ttk.Button(export_frame, text="Bordro (PDF)", command=self.export_pdf)\
            .pack(side="left", padx=5)

    # -------------------------------------------------
    #   Hesaplama
    # -------------------------------------------------
    def calculate_salaries(self):
        # Listeyi temizle
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.last_rows = []

        # Yıl / ay oku
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            if not (1 <= month <= 12):
                raise ValueError
        except ValueError:
            messagebox.showerror("Hata", "Yıl / Ay değerleri geçersiz.")
            return

        month_start, month_end = month_date_range(year, month)
        daily_hours, overtime_coef, include_weekends = get_settings()

        conn = get_conn()
        c = conn.cursor()

        # Gerekli tablolar yoksa oluştur (varsa dokunmaz)
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                hours REAL NOT NULL,
                note TEXT,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS advances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                installments INTEGER DEFAULT 1,
                remaining REAL DEFAULT 0,
                description TEXT,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS overtimes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                hours REAL NOT NULL,
                hourly_rate REAL NOT NULL,
                total REAL NOT NULL,
                note TEXT,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """)

        # Aktif personel listesi (active kolonu yok, hepsini alıyoruz)
        c.execute("""
            SELECT id, name, hourly_rate, start_date
            FROM employees
            ORDER BY name
        """)
        employees = c.fetchall()

        total_salary_sum = 0.0
        total_overtime_sum = 0.0
        total_advance_sum = 0.0
        total_net_sum = 0.0

        today = date.today()

        def count_working_days(start_date_str: str) -> int:
            """Personelin işe giriş + ay sonuna göre çalışma günü."""
            if not start_date_str:
                return 0
            try:
                start_date_val = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except Exception:
                return 0

            # Ayın son günü (gelecek ay ilk gününden 1 gün geri)
            last_day = month_end - timedelta(days=1)

            # Seçilen ay bu aysa, bugünden sonrasını sayma
            if year == today.year and month == today.month and today < last_day:
                last_day = today

            period_start = max(month_start, start_date_val)
            if period_start > last_day:
                return 0

            d = period_start
            days = 0
            while d <= last_day:
                if include_weekends or d.weekday() < 5:  # 0: Pazartesi, 6: Pazar
                    days += 1
                d += timedelta(days=1)
            return days

        # Her personel için hesapla
        for emp_id, name, hourly_rate, start_str in employees:
            # x = ay içindeki çalışma günü
            work_days = count_working_days(start_str)

            # Teorik saat = x * günlük saat
            theoretical_hours = work_days * daily_hours

            # Eksik saat (devamsızlık kayıtlarındaki hours toplamı)
            c.execute("""
                SELECT COALESCE(SUM(hours), 0)
                FROM attendance_logs
                WHERE employee_id = ?
                  AND date >= ? AND date < ?
            """, (emp_id, month_start.isoformat(), month_end.isoformat()))
            row = c.fetchone()
            missing_hours = float(row[0] or 0)

            # Toplam çalışma saati = x * 10 - devamsızlık
            total_hours = max(theoretical_hours - missing_hours, 0)

            # Maaş = toplam saat * saatlik ücret
            salary = total_hours * float(hourly_rate)

            # Mesai (overtimes.total)
            c.execute("""
                SELECT COALESCE(SUM(total), 0)
                FROM overtimes
                WHERE employee_id = ?
                  AND date >= ? AND date < ?
            """, (emp_id, month_start.isoformat(), month_end.isoformat()))
            row = c.fetchone()
            overtime_total = float(row[0] or 0)

            # Avans – seçilen ay içindeki tüm avanslar
            c.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM advances
                WHERE employee_id = ?
                  AND date >= ? AND date < ?
            """, (emp_id, month_start.isoformat(), month_end.isoformat()))
            row = c.fetchone()
            advance_total = float(row[0] or 0)

            net_salary = salary + overtime_total - advance_total

            # Treeview satırı
            self.tree.insert(
                "",
                "end",
                values=(
                    name,
                    work_days,
                    theoretical_hours,
                    missing_hours,
                    total_hours,
                    tl(salary),
                    tl(overtime_total),
                    tl(advance_total),
                    tl(net_salary),
                ),
            )

            # Dışa aktarım için kaydet
            self.last_rows.append({
                "name": name,
                "days": work_days,
                "theoretical_hours": theoretical_hours,
                "missing_hours": missing_hours,
                "total_hours": total_hours,
                "salary": salary,
                "overtime": overtime_total,
                "advance": advance_total,
                "net_salary": net_salary,
            })

            total_salary_sum += salary
            total_overtime_sum += overtime_total
            total_advance_sum += advance_total
            total_net_sum += net_salary


        # Toplam satırı
        if self.last_rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    "TOPLAM",
                    "",
                    "",
                    "",
                    "",
                    tl(total_salary_sum),
                    tl(total_overtime_sum),
                    tl(total_advance_sum),
                    tl(total_net_sum),
                ),
            )

        # Kasa özetini güncelle
        self.total_salary_var.set(tl(total_salary_sum))
        self.total_overtime_var.set(tl(total_overtime_sum))
        self.total_advance_var.set(tl(total_advance_sum))
        self.total_net_var.set(tl(total_net_sum))

    # -------------------------------------------------
    #   Dışa aktarım – CSV
    # -------------------------------------------------
    def export_csv(self):
        if not self.last_rows:
            messagebox.showwarning("Uyarı", "Önce 'Hesapla' tuşuna basın.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Dosyası", "*.csv")],
            initialfile="maas_ozet.csv",
            title="CSV Olarak Dışa Aktar",
        )
        if not file_path:
            return

        import csv

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "Personel", "Gün", "Teorik Saat", "Eksik Saat", "Toplam Saat",
                    "Maaş", "Mesai", "Avans Kesinti", "Net Maaş",
                ])
                for r in self.last_rows:
                    writer.writerow([
                        r["name"],
                        r["days"],
                        f"{r['theoretical_hours']:.2f}",
                        f"{r['missing_hours']:.2f}",
                        f"{r['total_hours']:.2f}",
                        f"{r['salary']:.2f}",
                        f"{r['overtime']:.2f}",
                        f"{r['advance']:.2f}",
                        f"{r['net_salary']:.2f}",
                    ])
            messagebox.showinfo("Başarılı", f"CSV dışa aktarım tamamlandı:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV kaydedilirken hata oluştu:\n{e}")

    # -------------------------------------------------
    #   Dışa aktarım – Excel
    # -------------------------------------------------
    def export_excel(self):
        if not self.last_rows:
            messagebox.showwarning("Uyarı", "Önce 'Hesapla' tuşuna basın.")
            return

        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror(
                "Hata",
                "Excel dışa aktarım için 'openpyxl' gerekli.\n\npip install openpyxl",
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            initialfile="bordro.xlsx",
            title="Bordro (Excel) Kaydet",
        )
        if not file_path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Bordro"

        headers = [
            "Personel", "Gün", "Teorik Saat", "Eksik Saat", "Toplam Saat",
            "Maaş", "Mesai", "Avans Kesinti", "Net Maaş",
        ]
        ws.append(headers)

        for r in self.last_rows:
            ws.append([
                r["name"],
                r["days"],
                r["theoretical_hours"],
                r["missing_hours"],
                r["total_hours"],
                r["salary"],
                r["overtime"],
                r["advance"],
                r["net_salary"],
            ])

        try:
            wb.save(file_path)
            messagebox.showinfo("Başarılı", f"Excel bordro oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken hata oluştu:\n{e}")

    # -------------------------------------------------
    #   Dışa aktarım – PDF
    # -------------------------------------------------
    def export_pdf(self):
        if not self.last_rows:
            messagebox.showwarning("Uyarı", "Önce 'Hesapla' tuşuna basın.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
        except ImportError:
            messagebox.showerror(
                "Hata",
                "PDF dışa aktarım için 'reportlab' gerekli.\n\npip install reportlab",
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")],
            initialfile="bordro.pdf",
            title="Bordro (PDF) Kaydet",
        )
        if not file_path:
            return

        c_pdf = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        left_margin = 15 * mm
        top_margin = height - 25 * mm
        line_height = 6 * mm

        c_pdf.setFont("Helvetica-Bold", 14)
        c_pdf.drawString(left_margin, top_margin, "Aylık Bordro")

        try:
            y = int(self.year_var.get())
            m = int(self.month_var.get())
            period = f"{m:02d}/{y}"
        except Exception:
            period = ""

        if period:
            c_pdf.setFont("Helvetica", 11)
            c_pdf.drawString(left_margin, top_margin - line_height, f"Dönem: {period}")

        y_pos = top_margin - 3 * line_height

        c_pdf.setFont("Helvetica-Bold", 8)
        header_text = "Personel | Gün | Teorik | Eksik | Saat | Maaş | Mesai | Avans | Net"
        c_pdf.drawString(left_margin, y_pos, header_text)
        y_pos -= line_height
        c_pdf.line(left_margin, y_pos + 2, width - left_margin, y_pos + 2)
        y_pos -= line_height

        c_pdf.setFont("Helvetica", 7)

        for r in self.last_rows:
            row_text = (
                f"{r['name']} | {r['days']} | "
                f"{r['theoretical_hours']:.1f} | {r['missing_hours']:.1f} | {r['total_hours']:.1f} | "
                f"{tl(r['salary'])} | {tl(r['overtime'])} | "
                f"{tl(r['advance'])} | {tl(r['net_salary'])}"
            )

            if y_pos < 20 * mm:
                c_pdf.showPage()
                y_pos = top_margin
                c_pdf.setFont("Helvetica-Bold", 8)
                c_pdf.drawString(left_margin, y_pos, header_text)
                y_pos -= line_height
                c_pdf.line(left_margin, y_pos + 2, width - left_margin, y_pos + 2)
                y_pos -= line_height
                c_pdf.setFont("Helvetica", 7)

            c_pdf.drawString(left_margin, y_pos, row_text)
            y_pos -= line_height

        try:
            c_pdf.save()
            messagebox.showinfo("Başarılı", f"PDF bordro oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"PDF oluşturulurken hata oluştu:\n{e}")
