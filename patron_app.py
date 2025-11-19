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
        Patron harici (OFIS) kullanıcılar için:
          - Personeller sekmesinde saatlik ücret sütununu gizle ve giriş alanını kilitle
          - Mesai sekmesinde mesai saatlik ücret ve toplam mesai ücreti sütunlarını gizle
          - Aylık Saat / Maaş sekmesinde tüm para kolonlarını + kasa özetini gizle
          - Performans (PPM) sekmesinde mesai tutarı ve net maaş kolonlarını gizle

        Amaç:
          Ofis personeli devamsızlık, avans ve mesai saatlerini girebilsin,
          fakat personelin ne kadar kazandığını göremesin.
        """

        # Başlıkta rol metnini güncelle
        if self.role_label is not None:
            self.role_label.config(text=self.role_display_text())

        # Patron ise her şeyi görsün – ekstra kısıtlama yok.
        if self.current_role == "PATRON":
            return

        # --------------------------------------------------------------
        # Yardımcı: treeview içindeki "para" kolonlarını gizleyen fonksiyon
        # --------------------------------------------------------------
        def hide_money_columns_in_tree(tree: ttk.Treeview):
            try:
                cols = tree["columns"]
            except Exception:
                return

            for col in cols:
                info = tree.heading(col)
                text = str(info.get("text", "")).strip()
                lower = text.lower()

                # Avans kolonlarını BILEREK bırakıyoruz (ofis avansı görebilmeli)
                # Sadece maaş / ücret / net / mesai tutarı gibi kazanç kolonlarını gizliyoruz.
                is_money = (
                    ("maaş" in lower)
                    or ("ücret" in lower)
                    or ("tutar" in lower)
                    or ("net" in lower)
                    or ("kasadan" in lower)
                    or ("₺" in lower)
                    or ("kazanç" in lower)
                    # "Mesai" ama "saat" geçmiyorsa genelde para kolonu oluyor (Aylık Saat / Maaş'taki 'Mesai')
                    or ("mesai" in lower and "saat" not in lower and "saatlik" not in lower)
                )

                if is_money:
                    tree.column(col, width=0, stretch=False)
                    tree.heading(col, text="")

        def hide_money_in_all_treeviews(root_widget: tk.Widget):
            """Verilen sekme içindeki tüm Treeview'lerde para kolonlarını gizle."""
            def walk(w):
                if isinstance(w, ttk.Treeview):
                    hide_money_columns_in_tree(w)
                for child in w.winfo_children():
                    walk(child)
            walk(root_widget)

        # --------------------------------------------------------------
        # 1) Personeller sekmesinde saatlik ücret sütununu gizle + girişini kilitle
        # --------------------------------------------------------------
        try:
            hide_money_in_all_treeviews(self.tab_employees)

            # Saatlik ücret girişini kilitle:
            # "Saatlik Ücret" yazan label'ı bulup, aynı satırdaki Entry'yi disable yapıyoruz.
            def disable_hourly_rate_entry(widget):
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, ttk.Label):
                            txt = str(child.cget("text")).lower()
                            if "saatlik" in txt and "ücret" in txt:
                                info = child.grid_info()
                                if info:
                                    row = int(info.get("row", 0))
                                    col = int(info.get("column", 0))
                                    parent = child.master
                                    for sib in parent.winfo_children():
                                        if isinstance(sib, ttk.Entry):
                                            sinfo = sib.grid_info()
                                            if (
                                                sinfo
                                                and int(sinfo.get("row", -1)) == row
                                                and int(sinfo.get("column", -1)) == col + 1
                                            ):
                                                sib.configure(state="disabled")
                        # derine in
                        disable_hourly_rate_entry(child)
                    except Exception:
                        disable_hourly_rate_entry(child)

            disable_hourly_rate_entry(self.tab_employees)
        except Exception:
            pass

        # --------------------------------------------------------------
        # 2) Mesai sekmesinde mesai saatlik ücret ve toplam mesai ücreti sütunlarını gizle
        #    (Heading'lerinde 'ücret', '₺', 'tutar' vs. geçen kolonlar gizleniyor)
        # --------------------------------------------------------------
        try:
            hide_money_in_all_treeviews(self.tab_overtime)
        except Exception:
            pass

        # --------------------------------------------------------------
        # 3) Aylık Saat / Maaş sekmesinde tüm para kolonlarını + kasa özetini gizle
        # --------------------------------------------------------------
        try:
            hide_money_in_all_treeviews(self.tab_salary)

            # Kasa özetini gizle / maskele
            for attr in ("total_salary_var", "total_overtime_var", "total_net_var"):
                var = getattr(self.tab_salary, attr, None)
                if isinstance(var, tk.StringVar):
                    var.set("Gizli")
        except Exception:
            pass

        # --------------------------------------------------------------
        # 4) Performans (PPM) sekmesinde mesai tutarı ve net maaş kolonlarını gizle
        #    (Başlıktaki 'Mesai Tutarı', 'Net Maaş', 'Ücret', 'Maaş', '₺' vb.)
        # --------------------------------------------------------------
        try:
            hide_money_in_all_treeviews(self.tab_performance)
        except Exception:
            pass


if __name__ == "__main__":
    init_db()
    app = PatronApp()
    app.mainloop()
