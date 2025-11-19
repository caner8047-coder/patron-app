import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from tkcalendar import DateEntry

from db import (
    get_active_employees,
    add_advance,
    get_conn,
    delete_advance as db_delete_advance,
    get_advance_by_id,
)
from utils import tl, month_date_range


class AdvanceTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.employees_cache = []
        self.selected_adv_id = None

        self.build_ui()
        self.load_employees()
        self.load_advances()

    # -------------------------------------------------
    #   UI
    # -------------------------------------------------
    def build_ui(self):
        # Üst form
        form_frame = ttk.LabelFrame(self, text="Avans Kaydı")
        form_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Personel
        ttk.Label(form_frame, text="Personel:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.adv_emp_var = tk.StringVar()
        self.adv_emp_combo = ttk.Combobox(form_frame, textvariable=self.adv_emp_var,
                                          state="readonly", width=30)
        self.adv_emp_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(form_frame, text="Yenile", command=self.refresh_employees)\
            .grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Tarih
        ttk.Label(form_frame, text="Tarih:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.adv_date_var = tk.StringVar()
        self.adv_date_entry = DateEntry(
            form_frame,
            textvariable=self.adv_date_var,
            date_pattern="yyyy-mm-dd",
            width=12
        )
        self.adv_date_entry.set_date(date.today())
        self.adv_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Tutar
        ttk.Label(form_frame, text="Avans Tutarı (₺):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.adv_amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.adv_amount_var, width=15)\
            .grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Açıklama
        ttk.Label(form_frame, text="Açıklama:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.adv_desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.adv_desc_var, width=40)\
            .grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Butonlar
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Yeni", command=self.clear_form).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Kaydet", command=self.save_advance).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Sil", command=self.delete_selected).grid(row=0, column=2, padx=5)

        # Alt liste
        list_frame = ttk.LabelFrame(self, text="Avans Hareketleri")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(side="top", anchor="w", padx=5, pady=(5, 0))

        ttk.Label(filter_frame, text="Yıl:").pack(side="left")
        self.adv_year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(filter_frame, textvariable=self.adv_year_var, width=6)\
            .pack(side="left", padx=(0, 10))

        ttk.Label(filter_frame, text="Ay:").pack(side="left")
        self.adv_month_var = tk.StringVar(value=str(date.today().month))
        ttk.Entry(filter_frame, textvariable=self.adv_month_var, width=4)\
            .pack(side="left")

        ttk.Button(filter_frame, text="Listele", command=self.load_advances)\
            .pack(side="left", padx=10)

        columns = ("employee", "date", "amount", "description")
        self.adv_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.adv_tree.heading("employee", text="Personel")
        self.adv_tree.heading("date", text="Tarih")
        self.adv_tree.heading("amount", text="Tutar")
        self.adv_tree.heading("description", text="Açıklama")

        self.adv_tree.column("employee", width=150)
        self.adv_tree.column("date", width=100)
        self.adv_tree.column("amount", width=100)
        self.adv_tree.column("description", width=250)

        self.adv_tree.pack(fill="both", expand=True)
        self.adv_tree.bind("<<TreeviewSelect>>", self.on_select)

    # -------------------------------------------------
    #   Yardımcılar
    # -------------------------------------------------
    def clear_form(self):
        self.selected_adv_id = None
        if self.adv_emp_combo["values"]:
            self.adv_emp_combo.current(0)
        self.adv_date_entry.set_date(date.today())
        self.adv_amount_var.set("")
        self.adv_desc_var.set("")

    def load_employees(self):
        employees = get_active_employees()
        self.employees_cache = employees
        names = [e[1] for e in employees]
        self.adv_emp_combo["values"] = names
        if names:
            self.adv_emp_combo.current(0)
        else:
            self.adv_emp_var.set("")

    def refresh_employees(self):
        self.load_employees()
        messagebox.showinfo("Bilgi", "Personel listesi güncellendi.")

    # -------------------------------------------------
    #   Kayıt işlemleri
    # -------------------------------------------------
    def save_advance(self):
        emp_name = self.adv_emp_var.get()
        if not emp_name:
            messagebox.showerror("Hata", "Lütfen personel seçin.")
            return

        emp_id = None
        for e in self.employees_cache:
            if e[1] == emp_name:
                emp_id = e[0]
                break
        if emp_id is None:
            messagebox.showerror("Hata", "Personel bulunamadı.")
            return

        # Tarih
        date_str = self.adv_date_var.get().strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Hata", "Tarih formatı geçersiz.")
            return

        # Tutar
        amount_str = self.adv_amount_var.get().strip()
        if not amount_str:
            messagebox.showerror("Hata", "Avans tutarını girin.")
            return

        try:
            amount = float(amount_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Avans tutarı sayısal olmalıdır.")
            return

        desc = self.adv_desc_var.get().strip()

        # db.add_advance eski şemayı bozmayalım diye taksit=1 ile çağırıyoruz
        add_advance(emp_id, date_str, amount, 1, desc)

        messagebox.showinfo("Başarılı", "Avans kaydedildi.")
        self.clear_form()
        self.load_advances()

    def delete_selected(self):
        if self.selected_adv_id is None:
            messagebox.showwarning("Uyarı", "Silmek için listeden bir kayıt seçin.")
            return

        if not messagebox.askyesno("Onay", "Bu avans kaydını silmek istiyor musunuz?"):
            return

        db_delete_advance(self.selected_adv_id)
        self.selected_adv_id = None
        self.clear_form()
        self.load_advances()

    def load_advances(self):
        for row in self.adv_tree.get_children():
            self.adv_tree.delete(row)

        conn = get_conn()
        c = conn.cursor()

        try:
            year = int(self.adv_year_var.get())
            month = int(self.adv_month_var.get())
            month_start, month_end = month_date_range(year, month)
            c.execute("""
                SELECT a.id, e.name, a.date, a.amount, a.description
                FROM advances a
                JOIN employees e ON e.id = a.employee_id
                WHERE a.date >= ? AND a.date < ?
                ORDER BY a.date DESC, e.name
            """, (month_start.isoformat(), month_end.isoformat()))
        except Exception:
            # Hatalı yıl/ay girilirse tümünü göster
            c.execute("""
                SELECT a.id, e.name, a.date, a.amount, a.description
                FROM advances a
                JOIN employees e ON e.id = a.employee_id
                ORDER BY a.date DESC, e.name
            """)
        rows = c.fetchall()
        conn.close()

        for adv_id, emp_name, d_str, amount, desc in rows:
            self.adv_tree.insert(
                "",
                "end",
                iid=str(adv_id),
                values=(emp_name, d_str, tl(amount), desc or "")
            )

    def on_select(self, event):
        item_id = self.adv_tree.focus()
        if not item_id:
            return

        self.selected_adv_id = int(item_id)
        row = get_advance_by_id(self.selected_adv_id)
        if row is None:
            return

        adv_id, emp_id, d_str, amount, inst, remaining, desc = row

        # Personel adı
        emp_name = next((e[1] for e in self.employees_cache if e[0] == emp_id), "")
        if emp_name:
            self.adv_emp_var.set(emp_name)

        self.adv_date_var.set(d_str)
        try:
            self.adv_date_entry.set_date(datetime.strptime(d_str, "%Y-%m-%d").date())
        except Exception:
            pass

        self.adv_amount_var.set(str(amount))
        self.adv_desc_var.set(desc or "")
