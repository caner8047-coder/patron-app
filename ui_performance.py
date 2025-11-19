import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta

from db import get_conn, get_settings
from utils import month_date_range, tl

MONTH_NAMES_TR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]


class PerformanceTab(ttk.Frame):
    """
    PPM – Personel Performans Menüsü

    Solda personel listesi,
    Sağda seçilen personelin yıl bazında aylık performans özeti:
    - Çalışma gün sayısı
    - Teorik saat (gün x günlük saat)
    - Devamsızlık (eksik saat)
    - Toplam çalışma saati
    - Mesai saat & tutar
    - Avans toplamı
    - Net maaş (maaş + mesai – avans)
    """

    def __init__(self, master):
        super().__init__(master)
        self.selected_employee_id = None
        self.employees = {}  # id -> {"name", "hourly_rate", "start_date"}
        self.rows = []       # Dışa aktarım için satırlar

        self.build_ui()
        self.load_employees()

    # -------------------------------------------------
    #   UI
    # -------------------------------------------------
    def build_ui(self):
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # Sol taraf: personel listesi
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Personel Listesi").pack(anchor="w", pady=(0, 5))

        emp_columns = ("name", "hourly_rate")
        self.emp_tree = ttk.Treeview(left_frame, columns=emp_columns, show="headings", height=18)
        self.emp_tree.heading("name", text="Personel")
        self.emp_tree.heading("hourly_rate", text="Saatlik Ücret")

        self.emp_tree.column("name", width=170)
        self.emp_tree.column("hourly_rate", width=90, anchor="e")

        self.emp_tree.pack(fill="both", expand=True)
        self.emp_tree.bind("<<TreeviewSelect>>", self.on_employee_select)

        # Sağ taraf: filtre + performans tablosu
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        filter_frame = ttk.LabelFrame(right_frame, text="Filtre")
        filter_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(filter_frame, text="Yıl:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(filter_frame, textvariable=self.year_var, width=6)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(filter_frame, text="Yılı Getir", command=self.refresh_performance)\
            .grid(row=0, column=2, padx=5, pady=5)

        self.info_label = ttk.Label(
            filter_frame,
            text="Önce soldan personel seçin.",
            foreground="gray"
        )
        self.info_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0, 5), sticky="w")

        # Performans listesi
        perf_frame = ttk.LabelFrame(right_frame, text="Aylık Performans Özeti")
        perf_frame.pack(fill="both", expand=True)

        perf_columns = (
            "month",
            "work_days",
            "theoretical_hours",
            "missing_hours",
            "total_hours",
            "overtime_hours",
            "overtime_total",
            "advance_total",
            "net_salary",
        )
        self.perf_tree = ttk.Treeview(perf_frame, columns=perf_columns, show="headings")

        self.perf_tree.heading("month", text="Ay")
        self.perf_tree.heading("work_days", text="Gün")
        self.perf_tree.heading("theoretical_hours", text="Teorik Saat")
        self.perf_tree.heading("missing_hours", text="Devamsızlık")
        self.perf_tree.heading("total_hours", text="Toplam Saat")
        self.perf_tree.heading("overtime_hours", text="Mesai Saat")
        self.perf_tree.heading("overtime_total", text="Mesai Tutarı")
        self.perf_tree.heading("advance_total", text="Avans")
        self.perf_tree.heading("net_salary", text="Net Maaş")

        self.perf_tree.column("month", width=110)
        self.perf_tree.column("work_days", width=60, anchor="center")
        self.perf_tree.column("theoretical_hours", width=90, anchor="center")
        self.perf_tree.column("missing_hours", width=90, anchor="center")
        self.perf_tree.column("total_hours", width=90, anchor="center")
        self.perf_tree.column("overtime_hours", width=90, anchor="center")
        self.perf_tree.column("overtime_total", width=100, anchor="e")
        self.perf_tree.column("advance_total", width=100, anchor="e")
        self.perf_tree.column("net_salary", width=110, anchor="e")

        self.perf_tree.pack(fill="both", expand=True)

        # Dışa aktarım butonları
        export_frame = ttk.Frame(right_frame)
        export_frame.pack(fill="x", pady=(5, 0))

        ttk.Button(export_frame, text="Excel'e Aktar", command=self.export_excel)\
            .pack(side="left", padx=5)
        ttk.Button(export_frame, text="PDF'e Aktar", command=self.export_pdf)\
            .pack(side="left", padx=5)

    # -------------------------------------------------
    #   Personel listesi
    # -------------------------------------------------
    def load_employees(self):
        """Sol taraftaki personel listesini doldurur."""
        for row in self.emp_tree.get_children():
            self.emp_tree.delete(row)
        self.employees.clear()

        conn = get_conn()
        c = conn.cursor()
        try:
            # active kolonu olsa da olmasa da çalışsın diye sadece temel alanlar
            c.execute("""
                SELECT id, name, hourly_rate, start_date
                FROM employees
                ORDER BY name
            """)
            for emp_id, name, hourly_rate, start_date in c.fetchall():
                hourly_rate = float(hourly_rate or 0)
                self.employees[emp_id] = {
                    "name": name,
                    "hourly_rate": hourly_rate,
                    "start_date": start_date,
                }
                # iid'yi emp_id yapıyoruz ki selection'dan ID'yi direkt alabilelim
                self.emp_tree.insert(
                    "",
                    "end",
                    iid=str(emp_id),
                    values=(name, tl(hourly_rate)),
                )
        except Exception as e:
            messagebox.showerror("Hata", f"Personel listesi okunurken hata oluştu:\n{e}")
        finally:
            conn.close()

    def on_employee_select(self, event=None):
        selected = self.emp_tree.selection()
        if not selected:
            return
        try:
            emp_id = int(selected[0])
        except ValueError:
            return

        self.selected_employee_id = emp_id
        self.refresh_performance()

    # -------------------------------------------------
    #   Hesaplama
    # -------------------------------------------------
    def refresh_performance(self):
        """Seçilen personel + yıl için aylık performansı yeniler."""
        if self.selected_employee_id is None:
            self.info_label.config(text="Önce soldan personel seçin.", foreground="gray")
            return

        try:
            year = int(self.year_var.get())
            if year < 2000 or year > 2100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir yıl girin (örn. 2025).")
            return

        emp = self.employees.get(self.selected_employee_id)
        if not emp:
            messagebox.showerror("Hata", "Seçili personel bulunamadı.")
            return

        self.load_performance_for_employee(self.selected_employee_id, emp, year)

    def load_performance_for_employee(self, emp_id: int, emp: dict, year: int):
        # Listeyi temizle
        for row in self.perf_tree.get_children():
            self.perf_tree.delete(row)
        self.rows.clear()

        daily_hours, overtime_coef, include_weekends = get_settings()

        start_date_str = emp.get("start_date")
        start_date_val = None
        if start_date_str:
            try:
                start_date_val = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except Exception:
                start_date_val = None

        today = date.today()

        totals = {
            "work_days": 0,
            "theoretical_hours": 0.0,
            "missing_hours": 0.0,
            "total_hours": 0.0,
            "overtime_hours": 0.0,
            "overtime_total": 0.0,
            "advance_total": 0.0,
            "net_salary": 0.0,
        }

        conn = get_conn()
        c = conn.cursor()

        try:
            for month in range(1, 12 + 1):
                month_start, month_end = month_date_range(year, month)
                last_day = month_end - timedelta(days=1)

                # Gelecek ayları gösterme
                if year == today.year and month > today.month:
                    continue

                # Personel bu aydan sonra başladıysa, bu ayı atla
                if start_date_val is not None and start_date_val > last_day:
                    continue

                # Çalışma günlerini say
                period_start = month_start
                if start_date_val:
                    period_start = max(period_start, start_date_val)

                effective_last_day = last_day
                if year == today.year and month == today.month and today < effective_last_day:
                    effective_last_day = today

                if period_start > effective_last_day:
                    continue

                d = period_start
                work_days = 0
                while d <= effective_last_day:
                    if include_weekends or d.weekday() < 5:
                        work_days += 1
                    d += timedelta(days=1)

                theoretical_hours = work_days * daily_hours

                # Devamsızlık (eksik saat) – attendance_logs'tan okunuyor
                c.execute("""
                    SELECT COALESCE(SUM(hours), 0)
                    FROM attendance_logs
                    WHERE employee_id = ?
                      AND date >= ? AND date < ?
                """, (emp_id, month_start.isoformat(), month_end.isoformat()))
                row = c.fetchone()
                missing_hours = float(row[0] or 0)

                total_hours = max(theoretical_hours - missing_hours, 0.0)

                hourly_rate = emp.get("hourly_rate", 0.0)
                base_salary = total_hours * float(hourly_rate)

                # Mesai – saat ve tutar
                c.execute("""
                    SELECT COALESCE(SUM(hours), 0), COALESCE(SUM(total), 0)
                    FROM overtimes
                    WHERE employee_id = ?
                      AND date >= ? AND date < ?
                """, (emp_id, month_start.isoformat(), month_end.isoformat()))
                o_row = c.fetchone()
                overtime_hours = float(o_row[0] or 0)
                overtime_total = float(o_row[1] or 0)

                # Avans toplamı
                c.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM advances
                    WHERE employee_id = ?
                      AND date >= ? AND date < ?
                """, (emp_id, month_start.isoformat(), month_end.isoformat()))
                a_row = c.fetchone()
                advance_total = float(a_row[0] or 0)

                net_salary = base_salary + overtime_total - advance_total

                # Hiç hareket yoksa satır ekleme (çok boş ayı gizle)
                if (
                    theoretical_hours == 0
                    and missing_hours == 0
                    and overtime_total == 0
                    and advance_total == 0
                ):
                    continue

                month_name = MONTH_NAMES_TR[month - 1]

                # Treeview satırı
                self.perf_tree.insert(
                    "",
                    "end",
                    values=(
                        f"{month:02d} - {month_name}",
                        work_days,
                        f"{theoretical_hours:.2f}",
                        f"{missing_hours:.2f}",
                        f"{total_hours:.2f}",
                        f"{overtime_hours:.2f}",
                        tl(overtime_total),
                        tl(advance_total),
                        tl(net_salary),
                    ),
                )

                # Dışa aktarım için sakla
                self.rows.append({
                    "year": year,
                    "month": month,
                    "month_name": month_name,
                    "work_days": work_days,
                    "theoretical_hours": theoretical_hours,
                    "missing_hours": missing_hours,
                    "total_hours": total_hours,
                    "overtime_hours": overtime_hours,
                    "overtime_total": overtime_total,
                    "advance_total": advance_total,
                    "net_salary": net_salary,
                })

                # Toplamlara ekle
                totals["work_days"] += work_days
                totals["theoretical_hours"] += theoretical_hours
                totals["missing_hours"] += missing_hours
                totals["total_hours"] += total_hours
                totals["overtime_hours"] += overtime_hours
                totals["overtime_total"] += overtime_total
                totals["advance_total"] += advance_total
                totals["net_salary"] += net_salary

        finally:
            conn.close()

        # TOPLAM satırı
        if self.rows:
            self.perf_tree.insert(
                "",
                "end",
                values=(
                    "TOPLAM",
                    totals["work_days"],
                    f"{totals['theoretical_hours']:.2f}",
                    f"{totals['missing_hours']:.2f}",
                    f"{totals['total_hours']:.2f}",
                    f"{totals['overtime_hours']:.2f}",
                    tl(totals["overtime_total"]),
                    tl(totals["advance_total"]),
                    tl(totals["net_salary"]),
                ),
            )

        self.info_label.config(
            text=f"Personel: {emp['name']} · Yıl: {year}",
            foreground="black",
        )

    # -------------------------------------------------
    #   Dışa aktarım – Excel
    # -------------------------------------------------
    def export_excel(self):
        if not self.rows:
            messagebox.showwarning("Uyarı", "Önce personel seçip yıl için performans hesaplayın.")
            return

        emp = self.employees.get(self.selected_employee_id)
        emp_name = emp["name"] if emp else "personel"
        year = self.year_var.get()

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
            initialfile=f"performans_{emp_name}_{year}.xlsx",
            title="Performans Raporu (Excel) Kaydet",
        )
        if not file_path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Performans"

        headers = [
            "Yıl", "Ay", "Personel",
            "Çalışma Günü", "Teorik Saat", "Devamsızlık Saat", "Toplam Saat",
            "Mesai Saat", "Mesai Tutarı", "Avans Toplamı", "Net Maaş",
        ]
        ws.append(headers)

        for r in self.rows:
            ws.append([
                r["year"],
                r["month_name"],
                emp_name,
                r["work_days"],
                r["theoretical_hours"],
                r["missing_hours"],
                r["total_hours"],
                r["overtime_hours"],
                r["overtime_total"],
                r["advance_total"],
                r["net_salary"],
            ])

        try:
            wb.save(file_path)
            messagebox.showinfo("Başarılı", f"Excel performans raporu oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken hata oluştu:\n{e}")

    # -------------------------------------------------
    #   Dışa aktarım – PDF
    # -------------------------------------------------
    def export_pdf(self):
        if not self.rows:
            messagebox.showwarning("Uyarı", "Önce personel seçip yıl için performans hesaplayın.")
            return

        emp = self.employees.get(self.selected_employee_id)
        emp_name = emp["name"] if emp else "Personel"
        year = self.year_var.get()

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
            initialfile=f"performans_{emp_name}_{year}.pdf",
            title="Performans Raporu (PDF) Kaydet",
        )
        if not file_path:
            return

        c_pdf = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        left_margin = 15 * mm
        top_margin = height - 25 * mm
        line_height = 6 * mm

        c_pdf.setFont("Helvetica-Bold", 14)
        c_pdf.drawString(left_margin, top_margin, "Personel Performans Raporu")

        c_pdf.setFont("Helvetica", 11)
        c_pdf.drawString(left_margin, top_margin - line_height, f"Personel: {emp_name}")
        c_pdf.drawString(left_margin, top_margin - 2 * line_height, f"Yıl: {year}")

        y_pos = top_margin - 4 * line_height

        c_pdf.setFont("Helvetica-Bold", 8)
        header_text = "Ay | Gun | Teorik | Devamsizlik | Toplam | Mesai Saat | Mesai | Avans | Net"
        c_pdf.drawString(left_margin, y_pos, header_text)
        y_pos -= line_height
        c_pdf.line(left_margin, y_pos + 2, width - left_margin, y_pos + 2)
        y_pos -= line_height

        c_pdf.setFont("Helvetica", 7)

        for r in self.rows:
            row_text = (
                f"{r['month_name']} | {r['work_days']} | "
                f"{r['theoretical_hours']:.1f} | {r['missing_hours']:.1f} | {r['total_hours']:.1f} | "
                f"{r['overtime_hours']:.1f} | {tl(r['overtime_total'])} | "
                f"{tl(r['advance_total'])} | {tl(r['net_salary'])}"
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
            messagebox.showinfo("Başarılı", f"PDF performans raporu oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"PDF oluşturulurken hata oluştu:\n{e}")
