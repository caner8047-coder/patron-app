import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db import add_employee, update_employee, get_all_employees


class EmployeesTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.selected_employee_id = None

        self.build_ui()
        self.load_employees()

    def build_ui(self):
        # Sol taraf: form
        form_frame = ttk.LabelFrame(self, text="Personel Bilgileri")
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        ttk.Label(form_frame, text="Ad Soyad:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.emp_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.emp_name_var, width=25).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Saatlik Ücret (₺):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.emp_rate_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.emp_rate_var, width=15).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Başlangıç Tarihi (YYYY-AA-GG):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.emp_start_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.emp_start_var, width=15).grid(row=2, column=1, padx=5, pady=5)

        self.emp_active_var = tk.IntVar(value=1)
        ttk.Checkbutton(form_frame, text="Aktif", variable=self.emp_active_var).grid(
            row=3, column=1, sticky="w", padx=5, pady=5
        )

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Yeni", command=self.clear_form).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Kaydet", command=self.save_employee).grid(row=0, column=1, padx=5)

        # Sağ taraf: liste
        list_frame = ttk.LabelFrame(self, text="Personel Listesi")
        list_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        columns = ("name", "rate", "start", "active")
        self.emp_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.emp_tree.heading("name", text="Ad Soyad")
        self.emp_tree.heading("rate", text="Saatlik Ücret (₺)")
        self.emp_tree.heading("start", text="Başlangıç Tarihi")
        self.emp_tree.heading("active", text="Aktif")

        self.emp_tree.column("name", width=200)
        self.emp_tree.column("rate", width=100)
        self.emp_tree.column("start", width=120)
        self.emp_tree.column("active", width=60)

        self.emp_tree.pack(fill="both", expand=True)
        self.emp_tree.bind("<<TreeviewSelect>>", self.on_select)

    # ---------- Yardımcılar ---------- #

    def clear_form(self):
        self.selected_employee_id = None
        self.emp_name_var.set("")
        self.emp_rate_var.set("")
        self.emp_start_var.set("")
        self.emp_active_var.set(1)

    def load_employees(self):
        for row in self.emp_tree.get_children():
            self.emp_tree.delete(row)

        rows = get_all_employees()

        for emp_id, name, rate, start_date_str, active in rows:
            active_str = "Evet" if active else "Hayır"
            self.emp_tree.insert(
                "",
                "end",
                iid=str(emp_id),
                values=(name, rate, start_date_str, active_str),
            )

    def on_select(self, event):
        item_id = self.emp_tree.focus()
        if not item_id:
            return

        self.selected_employee_id = int(item_id)
        vals = self.emp_tree.item(item_id, "values")
        self.emp_name_var.set(vals[0])
        self.emp_rate_var.set(str(vals[1]))
        self.emp_start_var.set(vals[2])
        self.emp_active_var.set(1 if vals[3] == "Evet" else 0)

    def save_employee(self):
        name = self.emp_name_var.get().strip()
        rate_str = self.emp_rate_var.get().strip()
        start_str = self.emp_start_var.get().strip()
        active = self.emp_active_var.get()

        if not name or not rate_str or not start_str:
            messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
            return

        try:
            rate = float(rate_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Saatlik ücret sayısal olmalıdır.")
            return

        # Tarih kontrolü
        try:
            datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Hata", "Başlangıç tarihi formatı YYYY-AA-GG olmalıdır.")
            return

        if self.selected_employee_id is None:
            add_employee(name, rate, start_str, active)
        else:
            update_employee(self.selected_employee_id, name, rate, start_str, active)

        self.load_employees()
        messagebox.showinfo("Başarılı", "Personel kaydedildi.")
        self.clear_form()
