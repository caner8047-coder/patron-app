import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime

from tkcalendar import DateEntry

from db import (
    get_active_employees,
    add_overtime,
    get_conn,
    update_overtime as db_update_overtime,
    delete_overtime as db_delete_overtime,
    get_settings,
)
from utils import tl, month_date_range


class OvertimeTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.employees_cache = []
        self.selected_ov_id = None
        self.show_only_selected_var = tk.IntVar(value=0)

        self.build_ui()
        self.load_employees()
        self.load_current_month_overtimes()

    def build_ui(self):
        # Üst: Mesai formu
        form_frame = ttk.LabelFrame(self, text="Mesai Kaydı")
        form_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Personel
        ttk.Label(form_frame, text="Personel:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ov_emp_var = tk.StringVar()
        self.ov_emp_combo = ttk.Combobox(form_frame, textvariable=self.ov_emp_var, state="readonly", width=30)
        self.ov_emp_combo.grid(row=0, column=1, padx=5, pady=5)
        self.ov_emp_combo.bind("<<ComboboxSelected>>", self.on_employee_changed)

        # Personel Yenile
        ttk.Button(form_frame, text="Yenile", command=self.refresh_employees).grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )

        # Tarih
        ttk.Label(form_frame, text="Tarih:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ov_date_var = tk.StringVar()
        self.ov_date_entry = DateEntry(
            form_frame,
            textvariable=self.ov_date_var,
            date_pattern="yyyy-mm-dd",
            width=12
        )
        self.ov_date_entry.set_date(date.today())
        self.ov_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Mesai saati
        ttk.Label(form_frame, text="Mesai Saati:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.ov_hours_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.ov_hours_var, width=10).grid(
            row=2, column=1, padx=5, pady=5, sticky="w"
        )

        # Açıklama
        ttk.Label(form_frame, text="Açıklama:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.ov_desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.ov_desc_var, width=40).grid(
            row=3, column=1, padx=5, pady=5, sticky="w"
        )

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Yeni", command=self.clear_form).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Kaydet", command=self.save_overtime).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Sil", command=self.delete_selected).grid(row=0, column=2, padx=5)

        # Alt: Mesai listesi
        list_frame = ttk.LabelFrame(self, text="Mesai Kayıtları")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Filtre satırı
        top_filter = ttk.Frame(list_frame)
        top_filter.pack(side="top", anchor="w", padx=5, pady=(5, 0))
        ttk.Checkbutton(
            top_filter,
            text="Sadece seçili personel",
            variable=self.show_only_selected_var,
            command=self.load_current_month_overtimes
        ).pack(side="left")

        # Yıl / Ay filtresi
        period_frame = ttk.Frame(list_frame)
        period_frame.pack(side="top", anchor="w", padx=5, pady=(2, 5))
        ttk.Label(period_frame, text="Yıl:").pack(side="left")
        self.ov_year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(period_frame, textvariable=self.ov_year_var, width=6).pack(side="left", padx=(0, 10))
        ttk.Label(period_frame, text="Ay:").pack(side="left")
        self.ov_month_var = tk.StringVar(value=str(date.today().month))
        ttk.Entry(period_frame, textvariable=self.ov_month_var, width=4).pack(side="left")
        ttk.Button(period_frame, text="Listele", command=self.load_current_month_overtimes).pack(side="left", padx=10)

        columns = ("date", "employee", "hours", "rate", "total", "description")
        self.ov_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.ov_tree.heading("date", text="Tarih")
        self.ov_tree.heading("employee", text="Personel")
        self.ov_tree.heading("hours", text="Saat")
        self.ov_tree.heading("rate", text="Mesai Saatlik Ücret")
        self.ov_tree.heading("total", text="Toplam Mesai Ücreti")
        self.ov_tree.heading("description", text="Açıklama")

        self.ov_tree.column("date", width=100)
        self.ov_tree.column("employee", width=150)
        self.ov_tree.column("hours", width=80)
        self.ov_tree.column("rate", width=140)
        self.ov_tree.column("total", width=150)
        self.ov_tree.column("description", width=200)

        self.ov_tree.pack(fill="both", expand=True)

        self.ov_tree.bind("<<TreeviewSelect>>", self.on_select)

        # Rapor butonları
        export_frame = ttk.Frame(list_frame)
        export_frame.pack(side="bottom", pady=5)
        ttk.Button(export_frame, text="Excel (Aylık Rapor)", command=self.export_excel).pack(side="left", padx=5)
        ttk.Button(export_frame, text="PDF (Aylık Rapor)", command=self.export_pdf).pack(side="left", padx=5)

    # ------------- Form kontrol ------------- #

    def clear_form(self):
        self.selected_ov_id = None
        if self.ov_emp_combo["values"]:
            self.ov_emp_combo.current(0)
        self.ov_date_entry.set_date(date.today())
        self.ov_hours_var.set("")
        self.ov_desc_var.set("")

    def load_employees(self):
        employees = get_active_employees()
        self.employees_cache = employees
        names = [e[1] for e in employees]
        self.ov_emp_combo["values"] = names
        if names:
            self.ov_emp_combo.current(0)
        else:
            self.ov_emp_var.set("")

    def refresh_employees(self):
        self.load_employees()
        messagebox.showinfo("Bilgi", "Personel listesi güncellendi.")
        self.load_current_month_overtimes()

    def on_employee_changed(self, event):
        if self.show_only_selected_var.get() == 1:
            self.load_current_month_overtimes()

    # ------------- Kayıt Kaydet / Sil ------------- #

    def save_overtime(self):
        emp_name = self.ov_emp_var.get()
        if not emp_name:
            messagebox.showerror("Hata", "Lütfen personel seçin.")
            return

        emp_id = None
        hourly_rate = None
        for e in self.employees_cache:
            if e[1] == emp_name:
                emp_id = e[0]
                hourly_rate = float(e[2])
                break

        if emp_id is None:
            messagebox.showerror("Hata", "Personel bulunamadı.")
            return

        date_str = self.ov_date_var.get().strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Hata", "Tarih formatı geçersiz.")
            return

        hours_str = self.ov_hours_var.get().strip()
        if not hours_str:
            messagebox.showerror("Hata", "Mesai saatini girin.")
            return

        try:
            hours_val = float(hours_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Mesai saati sayısal olmalıdır.")
            return

        if hours_val <= 0:
            messagebox.showerror("Hata", "Mesai saati 0'dan büyük olmalıdır.")
            return

        desc = self.ov_desc_var.get().strip()

        daily_hours, overtime_coef, include_weekends = get_settings()
        overtime_rate = hourly_rate * float(overtime_coef)
        total = overtime_rate * hours_val

        if self.selected_ov_id is None:
            add_overtime(emp_id, date_str, hours_val, overtime_rate, total, desc)
        else:
            db_update_overtime(self.selected_ov_id, emp_id, date_str, hours_val, overtime_rate, total, desc)

        messagebox.showinfo("Başarılı", f"Mesai kaydedildi.\nToplam: {tl(total)}")

        self.clear_form()
        self.load_current_month_overtimes()

    def delete_selected(self):
        if self.selected_ov_id is None:
            messagebox.showwarning("Uyarı", "Silmek için listeden bir kayıt seçin.")
            return

        if not messagebox.askyesno("Onay", "Bu mesai kaydını silmek istediğinize emin misiniz?"):
            return

        db_delete_overtime(self.selected_ov_id)
        self.selected_ov_id = None
        self.clear_form()
        self.load_current_month_overtimes()

    # ------------- Listeleme (Yıl / Ay) ------------- #

    def load_current_month_overtimes(self):
        for row in self.ov_tree.get_children():
            self.ov_tree.delete(row)

        try:
            year = int(self.ov_year_var.get())
            month = int(self.ov_month_var.get())
            if not (1 <= month <= 12):
                raise ValueError
        except Exception:
            today = date.today()
            year, month = today.year, today.month
            self.ov_year_var.set(str(year))
            self.ov_month_var.set(str(month))

        month_start, month_end = month_date_range(year, month)

        emp_filter_id = None
        if self.show_only_selected_var.get() == 1 and self.ov_emp_var.get():
            selected_name = self.ov_emp_var.get()
            for e in self.employees_cache:
                if e[1] == selected_name:
                    emp_filter_id = e[0]
                    break

        conn = get_conn()
        c = conn.cursor()
        query = """
            SELECT o.id, o.date, e.name, o.hours, o.rate, o.total, o.description
            FROM overtimes o
            JOIN employees e ON e.id = o.employee_id
            WHERE o.date >= ? AND o.date < ?
        """
        params = [month_start.isoformat(), month_end.isoformat()]

        if emp_filter_id is not None:
            query += " AND o.employee_id = ?"
            params.append(emp_filter_id)

        query += " ORDER BY o.date DESC, e.name"

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        for ot_id, d_str, name, hours, rate, total, desc in rows:
            self.ov_tree.insert(
                "",
                "end",
                iid=str(ot_id),
                values=(d_str, name, hours, tl(rate), tl(total), desc or "")
            )

    # ------------- Satır seçince form doldurma ------------- #

    def on_select(self, event):
        item_id = self.ov_tree.focus()
        if not item_id:
            return

        self.selected_ov_id = int(item_id)
        vals = self.ov_tree.item(item_id, "values")
        d_str, emp_name, hours, rate_str, total_str, desc = vals

        self.ov_emp_var.set(emp_name)
        self.ov_date_var.set(d_str)
        try:
            self.ov_date_entry.set_date(datetime.strptime(d_str, "%Y-%m-%d").date())
        except Exception:
            pass

        self.ov_hours_var.set(str(hours))
        self.ov_desc_var.set(desc or "")

    # ------------- Rapor: Excel / PDF ------------- #

    def _get_period_text(self):
        try:
            y = int(self.ov_year_var.get())
            m = int(self.ov_month_var.get())
            return f"{m:02d}/{y}"
        except Exception:
            return ""

    def export_excel(self):
        if not self.ov_tree.get_children():
            messagebox.showwarning("Uyarı", "Liste boş. Önce yıl/ay seçip 'Listele' deyin.")
            return

        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror(
                "Hata",
                "Excel dışa aktarım için 'openpyxl' kütüphanesi gerekiyor.\n\n"
                "Kurulum örneği:\n\npip install openpyxl"
            )
            return

        period = self._get_period_text()
        default_name = "mesai_rapor.xlsx"
        if period:
            default_name = f"mesai_rapor_{period.replace('/', '-')}.xlsx"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            initialfile=default_name,
            title="Mesai Raporunu Kaydet"
        )
        if not file_path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Mesai Raporu"

        headers = [
            "Tarih",
            "Personel",
            "Saat",
            "Mesai Saatlik Ücret",
            "Toplam Mesai Ücreti",
            "Açıklama",
        ]
        ws.append(headers)

        for row_id in self.ov_tree.get_children():
            vals = self.ov_tree.item(row_id)["values"]
            ws.append(list(vals))

        try:
            wb.save(file_path)
            messagebox.showinfo("Başarılı", f"Mesai Excel raporu oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken hata oluştu:\n{e}")

    def export_pdf(self):
        if not self.ov_tree.get_children():
            messagebox.showwarning("Uyarı", "Liste boş. Önce yıl/ay seçip 'Listele' deyin.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
        except ImportError:
            messagebox.showerror(
                "Hata",
                "PDF dışa aktarım için 'reportlab' kütüphanesi gerekiyor.\n\n"
                "Kurulum örneği:\n\npip install reportlab"
            )
            return

        period = self._get_period_text()
        default_name = "mesai_rapor.pdf"
        if period:
            default_name = f"mesai_rapor_{period.replace('/', '-')}.pdf"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")],
            initialfile=default_name,
            title="Mesai Raporunu PDF Olarak Kaydet"
        )
        if not file_path:
            return

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        left_margin = 15 * mm
        top_margin = height - 25 * mm
        line_height = 6 * mm

        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, top_margin, "Mesai Hareketleri Raporu")

        if period:
            c.setFont("Helvetica", 11)
            c.drawString(left_margin, top_margin - line_height, f"Dönem: {period}")

        y = top_margin - 3 * line_height
        c.setFont("Helvetica-Bold", 8)
        header_text = "Tarih | Personel | Saat | Saatlik Ücret | Toplam | Açıklama"
        c.drawString(left_margin, y, header_text)
        y -= line_height
        c.line(left_margin, y + 2, width - left_margin, y + 2)
        y -= line_height

        c.setFont("Helvetica", 7)

        for row_id in self.ov_tree.get_children():
            vals = self.ov_tree.item(row_id)["values"]
            row_text = " | ".join(str(v) for v in vals)

            if y < 20 * mm:
                c.showPage()
                y = top_margin
                c.setFont("Helvetica-Bold", 8)
                c.drawString(left_margin, y, header_text)
                y -= line_height
                c.line(left_margin, y + 2, width - left_margin, y + 2)
                y -= line_height
                c.setFont("Helvetica", 7)

            c.drawString(left_margin, y, row_text)
            y -= line_height

        try:
            c.save()
            messagebox.showinfo("Başarılı", f"Mesai PDF raporu oluşturuldu:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"PDF oluşturulurken hata oluştu:\n{e}")
