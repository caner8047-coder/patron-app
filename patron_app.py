import tkinter as tk
from tkinter import ttk, simpledialog

from db import init_db
from ui_dashboard import DashboardTab
from ui_employees import EmployeesTab
from ui_attendance import AttendanceTab
from ui_advance import AdvanceTab
from ui_overtime import OvertimeTab
from ui_salary import SalaryTab
from ui_settings import SettingsTab
from ui_performance import PerformanceTab


class RoleDialog(simpledialog.Dialog):
    """Uygulama açılırken basit rol seçimi penceresi."""

    def body(self, master):
        ttk.Label(master, text="Kullanıcı rolü seçin:").grid(
            row=0, column=0, columnspan=2, pady=(5, 10), padx=10, sticky="w"
        )

        self.role_var = tk.StringVar(value="OFIS")

        ttk.Radiobutton(
            master, text="Patron", value="PATRON", variable=self.role_var
        ).grid(row=1, column=0, padx=10, pady=2, sticky="w")

        ttk.Radiobutton(
            master, text="Ofis", value="OFIS", variable=self.role_var
        ).grid(row=2, column=0, padx=10, pady=2, sticky="w")

        return None

    def apply(self):
        self.result = self.role_var.get()


class PatronApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.current_role = "OFIS"  # varsayılan
        self.notebook = None
        self.role_label = None

        self.title("Personel Takip - Devamsızlık, Avans, Mesai ve Maaş Hesaplama")
        self.geometry("1150x680")

        # Rol seçimi
        self.ask_for_role()

        # Arayüzü kur
        self.build_ui()

        # Rol yetkilerini uygula (maaş saklama vb.)
        self.apply_role_permissions()

    # ------------------------------------------------------------------ #
    # Rol yönetimi
    # ------------------------------------------------------------------ #
    def ask_for_role(self):
        """Uygulama başlarken kullanıcıdan rolü seçmesini ister."""
        dlg = RoleDialog(self, title="Giriş")
        if dlg.result in ("PATRON", "OFIS"):
            self.current_role = dlg.result
        else:
            # Her ihtimale karşı varsayılan ofis
            self.current_role = "OFIS"

    def role_display_text(self) -> str:
        """Başlıkta gösterilecek metin."""
        if self.current_role == "PATRON":
            return "Giriş yapan: patron (PATRON)"
        return "Giriş yapan: ofis (OFIS)"

    # ------------------------------------------------------------------ #
    # Arayüz
    # ------------------------------------------------------------------ #
    def build_ui(self):
        # Üst başlık alanı
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(5, 0))

        title_label = ttk.Label(
            header, text="Personel Takip", font=("Segoe UI", 16, "bold")
        )
        title_label.pack(side="left")

        self.role_label = ttk.Label(
            header,
            text=self.role_display_text(),
            font=("Segoe UI", 9),
        )
        self.role_label.pack(side="right")

        # Sekmeler
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Sekme nesneleri
        self.tab_dashboard = DashboardTab(self.notebook)
        self.tab_employees = EmployeesTab(self.notebook)
        self.tab_attendance = AttendanceTab(self.notebook)
        self.tab_advance = AdvanceTab(self.notebook)
        self.tab_overtime = OvertimeTab(self.notebook)
        self.tab_salary = SalaryTab(self.notebook)
        self.tab_settings = SettingsTab(self.notebook)
        self.tab_performance = PerformanceTab(self.notebook)

        # Dashboard en başta olacak şekilde ekle
        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.notebook.add(self.tab_employees, text="Personeller")
        self.notebook.add(self.tab_attendance, text="Devamsızlık")
        self.notebook.add(self.tab_advance, text="Avans")
        self.notebook.add(self.tab_overtime, text="Mesai")
        self.notebook.add(self.tab_salary, text="Aylık Saat / Maaş")
        self.notebook.add(self.tab_performance, text="Performans (PPM)")
        self.notebook.add(self.tab_settings, text="Ayarlar")

    # ------------------------------------------------------------------ #
    # Rol bazlı yetkiler
    # ------------------------------------------------------------------ #
    def apply_role_permissions(self):
        """
        Patron harici roller için:
          - Çalışan listesinde saatlik ücreti gizle
          - Aylık Saat / Maaş sekmesinde tüm para kolonlarını gizle
          - Performans (PPM) sekmesinde para kolonlarını gizle
        """

        # Başlıkta rol metnini güncelle
        if self.role_label is not None:
            self.role_label.config(text=self.role_display_text())

        # Patron ise her şeyi görsün – ekstra kısıtlama yok.
        if self.current_role == "PATRON":
            return

        # --- yardımcı: para kolonlarını gizleyen fonksiyon ---
        def hide_money_columns(tree: ttk.Treeview):
            try:
                cols = tree["columns"]
            except Exception:
                return

            for col in cols:
                info = tree.heading(col)
                text = str(info.get("text", "")).strip()

                # Maaş / ücret / tutar / avans / kesinti / net maaş gibi alanlar
                if (
                    "Maaş" in text
                    or "Ücret" in text
                    or "Tutar" in text
                    or "Kesinti" in text
                    or "Avans" in text
                    or "₺" in text
                    or text == "Mesai"  # Aylık Saat/Maaş tablosundaki para sütunu
                ):
                    tree.column(col, width=0, stretch=False)
                    tree.heading(col, text="")  # başlığı da boşalt

        # 1) Personel listesinde saatlik ücret sütununu gizle
        try:
            emp_tree = getattr(self.tab_employees, "tree", None)
            if emp_tree is not None:
                for col in emp_tree["columns"]:
                    info = emp_tree.heading(col)
                    text = str(info.get("text", "")).strip()
                    if "Saatlik Ücret" in text or "Ücret" in text or "₺" in text:
                        emp_tree.column(col, width=0, stretch=False)
                        emp_tree.heading(col, text="")
        except Exception:
            pass

        # 2) Aylık Saat / Maaş tablosunda para alanlarını gizle
        try:
            sal_tree = getattr(self.tab_salary, "tree", None)
            if sal_tree is not None:
                hide_money_columns(sal_tree)
        except Exception:
            pass

        # 3) Performans (PPM) tablosunda para alanlarını gizle
        try:
            perf_tree = getattr(self.tab_performance, "tree", None)
            if perf_tree is not None:
                hide_money_columns(perf_tree)
        except Exception:
            pass


if __name__ == "__main__":
    init_db()
    app = PatronApp()
    app.mainloop()
