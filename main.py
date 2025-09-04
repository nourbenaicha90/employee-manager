# The full code for the EmployeeManagerApp class.
# This code is a complete and runnable Python script.

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from ttkbootstrap import Style
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageTk
import datetime
import re
import os
from calendar import monthrange
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
from tkinter import filedialog
import sys, os



def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # لما يكون exe
    except Exception:
        base_path = os.path.abspath(".")  # لما يكون Python عادي
    return os.path.join(base_path, relative_path)
logo_path = resource_path("Nour kine logo.jpg")
icon_path = resource_path("NourKine.ico")

pdfmetrics.registerFont(TTFont('Amiri', resource_path('Amiri-Regular.ttf')))
pdfmetrics.registerFont(TTFont('Amiri-Bold', resource_path('Amiri-Bold.ttf')))


DB = "employees.db"
MONTH_DAYS = 30  # افتراض: كل شهر 30 يوم حسب طلبك

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # employees table
    c.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        residence TEXT,
        birth_date TEXT,
        national_id TEXT,
        municipality TEXT,
        id_expiry TEXT,
        days_worked INTEGER DEFAULT 0,
        daily_rate REAL DEFAULT 0.0,
        phone TEXT,
        job_title TEXT
    )
    """)
    # attendance: record absences (employee_id, date TEXT 'YYYY-MM-DD')
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        date TEXT,
        status TEXT, -- 'absent' or 'present'
        UNIQUE(employee_id, date)
    )
    """)
    conn.commit()
    conn.close()

# ---------------- Validations ----------------
def is_valid_phone(phone_raw: str) -> bool:
    digits = re.sub(r"\D+", "", phone_raw or "")
    return len(digits) >= 10

def is_valid_date_ddmmyyyy(date_str: str) -> bool:
    try:
        datetime.datetime.strptime(date_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def to_iso(date_ddmmyyyy: str) -> str:
    # converts dd/mm/yyyy -> YYYY-MM-DD (ISO) for attendance
    dt = datetime.datetime.strptime(date_ddmmyyyy, "%d/%m/%Y")
    return dt.date().isoformat()

def iso_to_ddmmyyyy(iso_str: str) -> str:
    d = datetime.date.fromisoformat(iso_str)
    return d.strftime("%d/%m/%Y")

# ---------------- PDF export ----------------
# ---------------- إعداد الخطوط ----------------
    

# قاموس لأسماء الشهور باللغة العربية
MONTH_NAMES = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
    5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
    9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

def ar_text(txt):
    """إرجاع النص بالعربية مع اتجاه صحيح لعرضه في PDF"""
    return get_display(arabic_reshaper.reshape(txt or ""))

def iso_to_ddmmyyyy(date_str):
    """تحويل التاريخ من 2025-09-02 إلى 02/09/2025"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return date_str

def export_employee_pdf(filepath, emp_row, absences_dates, selected_month):
    emp_id = emp_row[0]
    c = canvas.Canvas(filepath, pagesize=A4)
    w, h = A4

    # ---------------- رسم اللوغو ----------------
    
    logo_path = resource_path("Nour kine logo.jpg")

    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 40, h-110, width=100, height=60, preserveAspectRatio=True)
        except Exception:
            pass

    # ---------------- عنوان الشركة ----------------
    c.setFont("Amiri-Bold", 16)
    c.drawRightString(w-40, h-50, ar_text("شركة Nour kine"))

    # ---------------- تاريخ الإنشاء ----------------
    c.setFont("Amiri", 11)
    c.drawRightString(w-40, h-80, ar_text("تاريخ الإنشاء: " + datetime.datetime.today().strftime("%d/%m/%Y")))

    # ---------------- بيانات الموظف ----------------
    y = h-130
    c.setFont("Amiri", 13)

    lines = [
        ("الرقم", str(emp_row[0])),
        ("الاسم", f"{emp_row[1]} {emp_row[2]}"),
        ("مكان الإقامة", emp_row[3] or ""),
        ("تاريخ الميلاد", emp_row[4] or ""),
        ("رقم البطاقة الوطنية", emp_row[5] or ""),
        ("البلدية", emp_row[6] or ""),
        ("تاريخ نهاية صلاحية البطاقة", emp_row[7] or ""),
        # ("عدد أيام العمل (إجمالي مسجل)", str(emp_row[8])),
        ("سعر اليوم", f"{emp_row[9]:.2f}"),
        ("الهاتف", emp_row[10] or ""),
        ("المسمى الوظيفي", emp_row[11] or "")
    ]

    for label, value in lines:
        c.drawRightString(w-40, y, ar_text(f"{label}: {value}"))
        y -= 22

    # ---------------- جدول الغيابات ----------------
    y -= 10
    c.setFont("Amiri-Bold", 14)
    c.drawRightString(w-40, y, ar_text(f"غيابات شهر {MONTH_NAMES.get(selected_month, 'غير معروف')}:"))
    y -= 20
    c.setFont("Amiri", 12)

    if not absences_dates:
        c.drawRightString(w-40, y, ar_text("لم يتم غياب في هذا الشهر."))
        y -= 20
    else:
        for d in sorted(absences_dates):
            c.drawRightString(w-40, y, ar_text(iso_to_ddmmyyyy(d)))
            y -= 18
            if y < 80:
                
                c.showPage()
                y = h - 60

    # ---------------- الملخص ----------------
    absent_count = len(absences_dates)
    worked_days = MONTH_DAYS - absent_count
    deduction = absent_count * emp_row[9]
    total = worked_days * emp_row[9]

    y -= 20
    c.setFont("Amiri", 13)
    c.drawRightString(w-40, y, ar_text(f"عدد الغيابات: {absent_count}"))
    y -= 18
    c.drawRightString(w-40, y, ar_text(f"عدد أيام العمل في هذا الشهر: {worked_days}"))
    y -= 18
    c.drawRightString(w-40, y, ar_text(f"المخصوم عن الغيابات: {deduction:.2f}"))
    y -= 18
    c.drawRightString(w-40, y, ar_text(f"المبلغ المستحق للشهر: {total:.2f}"))

    # ---------------- التوقيعات ----------------
    y -= 150
    c.setFont("Amiri-Bold", 14)
    c.drawRightString(w-60, y, ar_text("إمضاء موظف"))
    c.drawString(60, y, ar_text("إمضاء المحاسب"))

    # ---------------- حفظ الملف ----------------
    c.save()
    messagebox.showinfo("تصدير PDF", f"تم إنشاء الملف: {filepath}")


        
#-----------------------------------------
#-----------------------------------------
#-----------------------------------------

#-----------------------------------------
# ---------------- App UI ----------------
class EmployeeManagerApp:
    def __init__(self, root):
        self.root = root
        root.title("Nour kline - إدارة الموظفين")
        # try set icon (.ico)
        try:
            root.iconbitmap(resource_path("Nourkine.ico"))


        except Exception:
            pass

        # header: logo centered + title
        header = ttk.Frame(root, padding=10)
        header.pack(fill="x")
        try:
            # img = Image.open(resource_path("Nour kine logo.jpg")).resize((70, 70))
            # self.logo_imgtk = ImageTk.PhotoImage(img)
            center = ttk.Frame(header)
            center.pack(anchor="center")
            ttk.Label(center, image=self.logo_imgtk).pack()
            ttk.Label(center, text="Nour kline - نور كلين", font=("Arial", 20, "bold")).pack(pady=(6,0))
        except Exception:
            ttk.Label(header, text="Nour kline - نور كلين", font=("Arial", 20, "bold")).pack(anchor="center")

        # top bar: date/time
        self.time_label = ttk.Label(root, text="")
        self.time_label.pack()
        self.update_clock()

        # Main frames: left (form) + right (list)
        main = ttk.Frame(root, padding=8)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=6, pady=0)

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True, padx=6, pady=0)

        # ----- Form to add new employee -----
        ttk.Label(left, text="إضافة موظف جديد", font=("Arial", 12, "bold")).pack(anchor="n", pady=0)
        fields = [
            ("الاسم", "first"),
            ("اللقب", "last"),
            ("مكان الإقامة", "residence"),
            ("تاريخ الميلاد (dd/mm/yyyy)", "birth"),
            ("رقم البطاقة الوطنية", "nid"),
            ("البلدية", "municipality"),
            ("تاريخ نهاية صلاحية البطاقة (dd/mm/yyyy)", "idexpiry"),
            ("سعر اليوم (رقمي)", "daily_rate"),
            ("رقم الهاتف", "phone"),
            ("المسمى الوظيفي", "job")
        ]
        self.entries = {}
        for label, key in fields:
            ttk.Label(left, text=label).pack(anchor="w", pady=0)
            e = ttk.Entry(left, justify="right")
            e.pack(fill="x", pady=0)
            self.entries[key] = e

        ttk.Button(left, text="إضافة موظف", command=self.add_employee).pack(anchor="n", pady=1, fill="x")
        ttk.Button(left, text="حذف كل التاريخ (حذف كل البيانات)", command=self.delete_all_history).pack(anchor="n", pady=3, fill="x")

        # ----- Employee list on the right -----
        cols = ("id","first","last","phone","daily_rate","days_worked","job")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        headings = ["الرقم","الاسم","اللقب","الهاتف","سعر اليوم","البلدية","الوظيفة"]
        for col, head in zip(cols, headings):
            self.tree.heading(col, text=head, anchor="center")
            self.tree.column(col, width=120 ,anchor="center")
        self.tree.pack(fill="both", expand=True)

        # buttons below, including the new month selection
        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=6)
        ttk.Button(btn_frame, text="تسجيل الغياب", command=self.open_attendance_window).pack(side="left", padx=4)
        
        # إضافة مربع اختيار الشهر
        ttk.Label(btn_frame, text="شهر التقرير:").pack(side="left", padx=(10, 2))
        self.month_var = tk.StringVar(value=str(datetime.date.today().month))
        self.month_combo = ttk.Combobox(btn_frame, textvariable=self.month_var, values=list(range(1, 13)), width=3, state='readonly')
        self.month_combo.pack(side="left", padx=(2, 10))
        self.month_combo.set(datetime.date.today().month)
        
        ttk.Button(btn_frame, text="تحديث بيانات", command=self.update_selected).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="طباعة (PDF)", command=self.print_selected).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="حذف موظف", command=self.delete_selected).pack(side="left", padx=4)

        self.refresh_list()

    def update_clock(self):
        now = datetime.datetime.now()
        self.time_label.configure(text=now.strftime("%d/%m/%Y %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    # ------------- Employee CRUD -------------
    def add_employee(self):
        first = self.entries["first"].get().strip()
        last  = self.entries["last"].get().strip()
        residence = self.entries["residence"].get().strip()
        birth = self.entries["birth"].get().strip()
        nid = self.entries["nid"].get().strip()
        municipality = self.entries["municipality"].get().strip()
        idexpiry = self.entries["idexpiry"].get().strip()
        daily_rate_raw = self.entries["daily_rate"].get().strip()
        phone = self.entries["phone"].get().strip()
        job = self.entries["job"].get().strip()

        # validations
        if not all([first, last, phone, birth, daily_rate_raw]):
            messagebox.showerror("خطأ", "الرجاء ملء الحقول الضرورية (الاسم، اللقب، الهاتف، تاريخ الميلاد، سعر اليوم)")
            return
        if not is_valid_phone(phone):
            messagebox.showerror("خطأ", "رقم الهاتف ليس اقل من عشرة ارقام")
            return
        if not is_valid_date_ddmmyyyy(birth) or (idexpiry and not is_valid_date_ddmmyyyy(idexpiry)):
            messagebox.showerror("خطأ", "التواريخ يجب أن تكون بصيغة dd/mm/yyyy")
            return
        try:
            daily_rate = float(daily_rate_raw)
        except ValueError:
            messagebox.showerror("خطأ", "سعر اليوم يجب أن يكون رقماً")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""INSERT INTO employees
            (first_name,last_name,residence,birth_date,national_id,municipality,id_expiry,days_worked,daily_rate,phone,job_title)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (first,last,residence,birth,nid,municipality,idexpiry,0,daily_rate,phone,job))
        conn.commit()
        conn.close()
        messagebox.showinfo("نجاح", "تمت إضافة الموظف")
        self.clear_form()
        self.refresh_list()

    def clear_form(self):
        for e in self.entries.values():
            e.delete(0, "end")

    def refresh_list(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, first_name, last_name, phone, daily_rate, municipality,job_title FROM employees")
        for row in c.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def delete_selected(self):
        iid = self.tree.focus()
        if not iid:
            messagebox.showerror("خطأ", "اختر موظفاً")
            return
        vals = self.tree.item(iid, "values")
        emp_id = int(vals[0])
        if not messagebox.askyesno("تأكيد", f"هل تريد حذف الموظف {vals[1]} {vals[2]}؟"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM attendance WHERE employee_id=?", (emp_id,))
        c.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("تم", "تم حذف الموظف وسجلاته")
        self.refresh_list()

    def delete_all_history(self):
        if not messagebox.askyesno("تأكيد حذف الكل", "هل تريد حذف كل الموظفين وكل سجلات الحضور؟"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM attendance")
        c.execute("DELETE FROM employees")
        conn.commit()
        conn.close()
        messagebox.showinfo("تم", "تم حذف جميع البيانات")
        self.refresh_list()

    def update_selected(self):
        iid = self.tree.focus()
        if not iid:
            messagebox.showerror("خطأ", "اختر موظفاً")
            return
        vals = self.tree.item(iid, "values")
        emp_id = int(vals[0])

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        emp = c.fetchone()
        conn.close()
        if not emp:
            messagebox.showerror("خطأ", "الموظف غير موجود")
            return

        def save_changes():
            new_first = first_e.get().strip()
            new_last = last_e.get().strip()
            new_residence = residence_e.get().strip()
            new_birth = birth_e.get().strip()
            new_nid = nid_e.get().strip()
            new_municipality = municipality_e.get().strip()
            new_idexpiry = idexpiry_e.get().strip()
            new_phone = phone_e.get().strip()
            new_rate = rate_e.get().strip()
            new_job = job_e.get().strip()

            if not is_valid_phone(new_phone):
                messagebox.showerror("خطأ", "رقم الهاتف غير صالح")
                return
            try:
                new_rate_f = float(new_rate)
            except ValueError:
                messagebox.showerror("خطأ", "سعر اليوم غير صحيح")
                return
            
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("""UPDATE employees 
                        SET first_name=?, last_name=?, residence=?, birth_date=?, national_id=?, municipality=?, 
                            id_expiry=?, daily_rate=?, phone=?, job_title=? 
                        WHERE id=? """, (
                        new_first, new_last, new_residence, new_birth, new_nid, new_municipality,
                        new_idexpiry, new_rate_f, new_phone, new_job, emp_id
                    ))
            conn.commit()
            conn.close()
            messagebox.showinfo("نجاح", "تم التحديث")
            edit_win.destroy()
            self.refresh_list()

        edit_win = tk.Toplevel(self.root)
        edit_win.title("تحديث الموظف")
        
        fields = [
            ("الاسم", "first", emp[1]),
            ("اللقب", "last", emp[2]),
            ("مكان الإقامة", "residence", emp[3]),
            ("تاريخ الميلاد (dd/mm/yyyy)", "birth", emp[4]),
            ("رقم البطاقة الوطنية", "nid", emp[5]),
            ("البلدية", "municipality", emp[6]),
            ("تاريخ نهاية صلاحية البطاقة (dd/mm/yyyy)", "idexpiry", emp[7]),
            ("سعر اليوم (رقمي)", "daily_rate", emp[9]),
            ("رقم الهاتف", "phone", emp[10]),
            ("المسمى الوظيفي", "job", emp[11])
        ]

        entries = {}
        for label_text, key, value in fields:
            ttk.Label(edit_win, text=label_text).pack(anchor="w", padx=10, pady=2)
            entry = ttk.Entry(edit_win)
            entry.pack(fill="x", padx=10, pady=2)
            entry.insert(0, value or "")
            entries[key + '_e'] = entry # Suffix entries with _e

        first_e = entries['first_e']
        last_e = entries['last_e']
        residence_e = entries['residence_e']
        birth_e = entries['birth_e']
        nid_e = entries['nid_e']
        municipality_e = entries['municipality_e']
        idexpiry_e = entries['idexpiry_e']
        phone_e = entries['phone_e']
        rate_e = entries['daily_rate_e']
        job_e = entries['job_e']
        
        ttk.Button(edit_win, text="حفظ", command=save_changes).pack(pady=6)

   
        if not iid:
            messagebox.showerror("خطأ", "اختر موظفاً")
            return
        vals = self.tree.item(iid, "values")
        emp_id = int(vals[0])

        try:
            selected_month = int(self.month_var.get())
            if not 1 <= selected_month <= 12:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("خطأ", "الرجاء اختيار رقم شهر صالح (من 1 إلى 12)")
            return

        now = datetime.date.today()
        selected_year = now.year

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        emp = c.fetchone()
        
        # get absences for the selected month and year
        c.execute("SELECT date FROM attendance WHERE employee_id=? AND status='absent' AND date LIKE ?", (emp_id, f"{selected_year}-{selected_month:02d}-%"))
        rows = c.fetchall()
        conn.close()
        
        abs_dates = [r[0] for r in rows]
        export_employee_pdf(emp, abs_dates, selected_month)
    def print_selected(self):
        iid = self.tree.focus()
        if not iid:
            messagebox.showerror("خطأ", "اختر موظفاً")
            return
        vals = self.tree.item(iid, "values")
        emp_id = int(vals[0])

        try:
            selected_month = int(self.month_var.get())
            if not 1 <= selected_month <= 12:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("خطأ", "الرجاء اختيار رقم شهر صالح (من 1 إلى 12)")
            return

        now = datetime.date.today()
        selected_year = now.year

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        emp = c.fetchone()
        
        c.execute("SELECT date FROM attendance WHERE employee_id=? AND status='absent' AND date LIKE ?", 
                (emp_id, f"{selected_year}-{selected_month:02d}-%"))
        rows = c.fetchall()
        conn.close()

        abs_dates = [r[0] for r in rows]

        # نافذة اختيار مكان حفظ الملف
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"employee_{emp_id}_{selected_month}.pdf"
        )
        if filepath:
            export_employee_pdf(filepath, emp, abs_dates, selected_month)
    # ---------------- Attendance window ----------------
    def open_attendance_window(self):
        AttWindow(self.root, refresh_callback=self.refresh_list)

# ---------------- Attendance window class ----------------
class AttWindow:
    def __init__(self, parent, refresh_callback=None):
        self.parent = parent
        self.refresh_callback = refresh_callback
        self.win = tk.Toplevel(parent)
        self.win.title("تسجيل الغياب")
        self.win.geometry("900x600")

        # controls: choose month/year
        top = ttk.Frame(self.win); top.pack(fill="x", pady=6)
        now = datetime.date.today()
        self.year_var = tk.IntVar(value=now.year)
        self.month_var = tk.IntVar(value=now.month)
        ttk.Label(top, text="السنة").pack(side="left", padx=4)
        ttk.Entry(top, textvariable=self.year_var, width=6).pack(side="left")
        ttk.Label(top, text="الشهر (1-12)").pack(side="left", padx=4)
        ttk.Entry(top, textvariable=self.month_var, width=4).pack(side="left")
        ttk.Button(top, text="فتح الشهر", command=self.build_grid).pack(side="left", padx=6)

        # frame for grid
        self.canvas = tk.Canvas(self.win)
        self.scroll = ttk.Scrollbar(self.win, orient="vertical", command=self.canvas.yview)
        self.frame = ttk.Frame(self.canvas)
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self.build_grid()

    def build_grid(self):
        # clear previous
        for w in self.frame.winfo_children():
            w.destroy()

        year = int(self.year_var.get())
        month = int(self.month_var.get())
        # days_of_month = monthrange(year, month)[1]  # real days in month
        # but per requirement we show 1..30 (30 days)
        days = list(range(1, MONTH_DAYS+1))

        # header row: empty + day numbers
        ttk.Label(self.frame, text="الموظف").grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        for i, d in enumerate(days):
            ttk.Label(self.frame, text=str(d), width=4).grid(row=0, column=1+i, sticky="nsew", padx=2)

        # load employees
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, first_name, last_name FROM employees")
        emps = c.fetchall()
        conn.close()

        self.check_vars = {}  # (emp_id, day) -> tk.IntVar

        for r, emp in enumerate(emps, start=1):
            emp_id = emp[0]
            ttk.Label(self.frame, text=f"{emp[1]} {emp[2]}", width=20).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            for cday_idx, day in enumerate(days):
                var = tk.IntVar()
                # determine date ISO: since input is day+month+year -> construct date
                try:
                    dt = datetime.date(year, month, day)
                except Exception:
                    # in case month has fewer days, still allow with day as number (we'll create iso manually)
                    dt = datetime.date(year, month, min(day, monthrange(year, month)[1]))
                iso = dt.isoformat()
                # check db if absent
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute("SELECT status FROM attendance WHERE employee_id=? AND date=?", (emp_id, iso))
                row = cur.fetchone()
                conn.close()
                if row and row[0] == "absent":
                    var.set(1)
                cb = ttk.Checkbutton(self.frame, variable=var)
                cb.grid(row=r, column=1+cday_idx, padx=2)
                # bind toggling
                cb.configure(command=lambda v=var, eid=emp_id, d_iso=iso: self.on_toggle(v, eid, d_iso))
                self.check_vars[(emp_id, day)] = var

        # add save/close buttons
        btns = ttk.Frame(self.frame)
        btns.grid(row=r+1, column=0, columnspan=len(days)+1, pady=8)
        ttk.Button(btns, text="إغلاق", command=self.win.destroy).pack(side="right", padx=6)

    def on_toggle(self, var, emp_id, iso_date):
        # if checked -> mark absent; if unchecked -> remove absent (present)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        if var.get() == 1:
            # insert or replace
            try:
                c.execute("INSERT OR REPLACE INTO attendance (employee_id, date, status) VALUES (?, ?, ?)", (emp_id, iso_date, "absent"))
            except Exception:
                pass
        else:
            c.execute("DELETE FROM attendance WHERE employee_id=? AND date=?", (emp_id, iso_date))
        conn.commit()
        conn.close()
        # update employee days_worked? We'll compute days_worked as total present per month or keep stored value.
        # For simplicity, update stored days_worked as total present across all records for the employee in DB
        self.update_days_worked(emp_id)

    def update_days_worked(self, emp_id):
        # recompute total present across recorded attendance for that employee across DB months
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        # Count days where status != absent (we only store absences explicitly), but we don't have present records.
        # Instead we will NOT compute days_worked from attendance history; we'll keep days_worked manual or computed elsewhere.
        # For now, do nothing to not overwrite manual field.
        conn.close()
        # After toggling, you may want to refresh main list (if callback provided)
        # (not implemented here to avoid circular imports)
        # If parent passed a refresh callback, call it:
        # (we don't have reference; AttWindow created with refresh_callback in App)
        pass

# ---------------- Run ----------------
def main():
    init_db()
    style = Style("cosmo")
    root = style.master
    root.geometry("1400x900")
 

    app = EmployeeManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
