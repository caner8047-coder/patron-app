from datetime import date, datetime, timedelta

from db import get_settings


def month_date_range(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def working_days_for_employee(start_date_str, year, month):
    """Seçilen ay için çalışması gereken gün sayısı.

    - Çalışanın işe giriş tarihinden sonra başlar
    - İçinde bulunulan ayda bugünden sonrasını saymaz
    - Hafta sonu ayarını (include_weekends) dikkate alır
    """
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    month_start, month_end = month_date_range(year, month)

    # Çalışanın işe giriş tarihinden önceki günler sayılmaz
    effective_start = max(start_dt, month_start)

    # Gelecekteki günleri sayma
    today = date.today()
    if today.year == year and today.month == month:
        effective_end = min(month_end, today + timedelta(days=1))
    else:
        effective_end = month_end

    if effective_start >= effective_end:
        return 0

    daily_hours, overtime_coef, include_weekends = get_settings()
    include_weekends_flag = bool(include_weekends)

    d = effective_start
    count = 0
    while d < effective_end:
        if include_weekends_flag:
            count += 1
        else:
            # 0 = Pazartesi, 6 = Pazar
            if d.weekday() < 5:  # Pazartesi–Cuma
                count += 1
        d += timedelta(days=1)
    return count


def calculate_lost_hours(att_rows):
    """Devamsızlıktan düşülecek toplam saat.

    att_rows: (date_str, type_code, hours)
    FULL_ABSENCE ve FREE_LEAVE -> tam gün
    HOUR_LOSS -> girilen saat
    ANNUAL_LEAVE, REPORT -> ücretli izin (saat düşmüyoruz)
    """
    total = 0.0
    daily_hours, overtime_coef, include_weekends = get_settings()

    for d_str, type_code, hours in att_rows:
        if type_code == "FULL_ABSENCE":
            total += daily_hours
        elif type_code == "HOUR_LOSS":
            total += float(hours or 0)
        elif type_code == "FREE_LEAVE":
            total += daily_hours
        else:
            # ANNUAL_LEAVE, REPORT vb. için saat kesme yok
            pass

    return total


def calculate_overtime_total(overtime_rows):
    """Mesai toplamını hesaplar.

    overtime_rows: (date_str, hours, rate, total)
    """
    total = 0.0
    for d_str, hours, rate, total_val in overtime_rows:
        total += float(total_val or 0)
    return total


def calculate_advance_cut(adv_rows):
    """Bu ay avans kesintisini hesaplar.

    adv_rows: (id, date, amount, installments, remaining)
    Her ay için 1 taksit keser.
    Geri dönen:
        (toplam_kesinti, [(adv_id, new_remaining), ...])
    """
    total_cut = 0.0
    updates = []

    for adv_id, d_str, amount, installments, remaining in adv_rows:
        if installments <= 0:
            continue
        per_inst = amount / installments
        if remaining <= 0:
            new_remaining = 0.0
            cut = 0.0
        elif remaining <= per_inst:
            cut = remaining
            new_remaining = 0.0
        else:
            cut = per_inst
            new_remaining = remaining - per_inst

        total_cut += cut
        updates.append((adv_id, new_remaining))

    return total_cut, updates


def tl(value):
    """Sayiyi '1.234,56 ₺' formatına çevirir."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0 ₺"

    s = f"{v:,.2f}"
    # İngilizce format: 1,234.56 -> 1.234,56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " ₺"


def format_float(value):
    """Saat vb. için, 2 haneli ondalık; .00 ise tam sayı gösterir."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0"
    s = f"{v:.2f}"
    if s.endswith(".00"):
        return s[:-3]
    return s
