import tkinter as tk
from tkinter import ttk

from db import init_db
from ui_employees import EmployeesTab
from ui_attendance import AttendanceTab
from ui_advance import AdvanceTab
from ui_overtime import OvertimeTab
from ui_salary import SalaryTab
from ui_settings import SettingsTab


class PatronApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Personel Takip - Devamsızlık, Avans, Mesai ve Maaş Hesaplama")
        self.geometry("1150x680")

        self.build_ui()

    def build_ui(self):
        title_label = ttk.Label(self, text="Personel Takip", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=5)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Sekmeler
        emp_tab = EmployeesTab(notebook)
        att_tab = AttendanceTab(notebook)
        adv_tab = AdvanceTab(notebook)
        ov_tab = OvertimeTab(notebook)
        sal_tab = SalaryTab(notebook)
        set_tab = SettingsTab(notebook)

        notebook.add(emp_tab, text="Personeller")
        notebook.add(att_tab, text="Devamsızlık")
        notebook.add(adv_tab, text="Avans")
        notebook.add(ov_tab, text="Mesai")
        notebook.add(sal_tab, text="Aylık Saat / Maaş")
        notebook.add(set_tab, text="Ayarlar")


if __name__ == "__main__":
    init_db()
    app = PatronApp()
    app.mainloop()
