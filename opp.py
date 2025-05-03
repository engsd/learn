import tkinter as tk
from tkinter import messagebox, Listbox, Scrollbar, Frame, Label, Entry, Button, OptionMenu, StringVar
from datetime import datetime
import mysql.connector # 导入 MySQL 连接器
from mysql.connector import Error # 导入错误类
import os
# --- 数据库配置 ---
# !! 重要提示: 不建议将密码硬编码在此处。
# !! 更好的做法是使用环境变量、配置文件或专门的密钥管理服务。
# !! 这里为了演示方便，使用了占位符。请替换为您自己的 MySQL 信息。
DB_CONFIG = {
    'host': 'localhost',        # MySQL 服务器地址 (通常是 'localhost' 或 IP 地址)
    'user': 'finance_app_user', # 您创建的数据库用户名
    'password': '12345', # 您为用户设置的密码
    'database': 'finance_tracker_db' # 您创建的数据库名称
}

class FinanceTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人理财追踪器 (MySQL 版)")
        self.root.geometry("600x450")

        self.db_conn = None
        self.db_cursor = None
        self.setup_database() # 设置数据库连接和表

        # --- 界面元素 (与之前版本基本相同) ---
        input_frame = Frame(root, padx=10, pady=10)
        input_frame.pack(fill=tk.X)

        Label(input_frame, text="类型:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.type_var = StringVar(root)
        self.type_var.set("支出")
        type_options = ["支出", "收入"]
        type_menu = OptionMenu(input_frame, self.type_var, *type_options)
        type_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        type_menu.config(width=8)

        Label(input_frame, text="描述:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.desc_entry = Entry(input_frame)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        Label(input_frame, text="金额:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.amount_entry = Entry(input_frame)
        self.amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        input_frame.columnconfigure(1, weight=1)

        add_button = Button(input_frame, text="添加记录", command=self.add_transaction)
        add_button.grid(row=3, column=0, columnspan=2, pady=10)

        list_frame = Frame(root, padx=10, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True)

        Label(list_frame, text="交易记录:").pack(anchor='w')
        scrollbar_frame = Frame(list_frame)
        scrollbar_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = Scrollbar(scrollbar_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.transaction_listbox = Listbox(scrollbar_frame, yscrollcommand=scrollbar.set, height=15)
        self.transaction_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.transaction_listbox.yview)

        self.status_label = Label(root, text="总余额: 0.00", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 初始化加载数据
        if self.db_conn and self.db_conn.is_connected():
            self.update_transaction_list()
            self.update_status()
        else:
             messagebox.showerror("数据库错误", "未能连接到数据库，请检查配置和MySQL服务器状态。")


    def setup_database(self):
        """建立 MySQL 数据库连接并创建表"""
        try:
            # 尝试连接数据库
            self.db_conn = mysql.connector.connect(**DB_CONFIG)

            if self.db_conn.is_connected():
                self.db_cursor = self.db_conn.cursor()
                print(f"成功连接到 MySQL 数据库 '{DB_CONFIG['database']}'")

                # 创建 transactions 表 (如果不存在)
                # 使用 DECIMAL(10, 2) 存储金额以保证精度
                # 使用 DATETIME 存储时间戳
                self.db_cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        type ENUM('收入', '支出') NOT NULL,
                        description VARCHAR(255) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                self.db_conn.commit() # DDL 语句在某些配置下可能自动提交，但显式提交更安全
                print("表 'transactions' 已检查/创建。")
            else:
                messagebox.showerror("数据库连接失败", "无法连接到 MySQL 数据库。")
                self.db_conn = None # 标记连接失败

        except Error as e:
            messagebox.showerror("数据库设置错误", f"连接或设置数据库时出错: {e}\n请检查配置: {DB_CONFIG}")
            self.db_conn = None # 标记连接失败

    def close_database(self):
         """关闭 MySQL 数据库连接"""
         if self.db_cursor:
             self.db_cursor.close()
             print("数据库游标已关闭")
         if self.db_conn and self.db_conn.is_connected():
             self.db_conn.close()
             print("数据库连接已关闭")

    def add_transaction(self):
        """添加一笔交易记录到 MySQL 数据库"""
        if not self.db_conn or not self.db_conn.is_connected():
             messagebox.showerror("错误", "数据库未连接，无法添加记录。")
             return

        trans_type = self.type_var.get()
        description = self.desc_entry.get()
        amount_str = self.amount_entry.get()

        if not description or not amount_str:
            messagebox.showwarning("输入错误", "描述和金额不能为空！")
            return

        try:
            amount = float(amount_str) # 先转为 float
            if amount <= 0:
                raise ValueError("金额必须为正数")
            # 可以考虑直接转为 Decimal，但 float 对于简单应用也够用
            # from decimal import Decimal, InvalidOperation
            # amount = Decimal(amount_str)
            # if amount <= Decimal(0): raise ValueError(...)
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的正数金额！")
            return

        # MySQL 的 DATETIME 类型可以直接使用 Python 的 datetime 对象或格式化字符串
        timestamp = datetime.now() #.strftime("%Y-%m-%d %H:%M:%S") # 直接用对象通常更好

        try:
            # 使用 %s 作为占位符
            sql = """
                INSERT INTO transactions (timestamp, type, description, amount)
                VALUES (%s, %s, %s, %s)
            """
            val = (timestamp, trans_type, description, amount) # 金额始终存正数

            self.db_cursor.execute(sql, val)
            self.db_conn.commit() # 提交事务

            print(f"记录已添加: {self.db_cursor.rowcount} 行受影响。")

            # 更新界面
            self.update_transaction_list()
            self.update_status()

            # 清空输入框
            self.desc_entry.delete(0, tk.END)
            self.amount_entry.delete(0, tk.END)
            self.type_var.set("支出")

        except Error as e:
            messagebox.showerror("数据库错误", f"无法添加记录: {e}")
            try:
                self.db_conn.rollback() # 如果出错则回滚
                print("事务已回滚")
            except Error as rb_e:
                 messagebox.showerror("数据库错误", f"回滚失败: {rb_e}")

    def update_transaction_list(self):
        """从 MySQL 获取记录并更新列表框显示"""
        if not self.db_conn or not self.db_conn.is_connected(): return

        self.transaction_listbox.delete(0, tk.END)
        try:
            # 查询记录，按时间戳降序
            # 注意：从数据库获取的 timestamp 是 datetime 对象
            self.db_cursor.execute("SELECT timestamp, type, description, amount FROM transactions ORDER BY timestamp DESC")
            all_transactions = self.db_cursor.fetchall()

            for trans in all_transactions:
                timestamp_dt, trans_type, description, amount = trans
                # 格式化时间戳用于显示
                timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
                sign = "+" if trans_type == "收入" else "-"
                # amount 从 DECIMAL 或 DOUBLE 取出时可能是 Decimal 类型或 float，直接格式化
                display_text = f"{timestamp_str} | {trans_type}: {description} | {sign}{amount:.2f}"
                self.transaction_listbox.insert(tk.END, display_text)

        except Error as e:
            messagebox.showerror("数据库错误", f"无法加载交易记录: {e}")

    def update_status(self):
        """从 MySQL 计算并更新总余额"""
        if not self.db_conn or not self.db_conn.is_connected(): return

        total_balance = 0.0
        try:
            # 计算总收入
            self.db_cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = '收入'")
            total_income_result = self.db_cursor.fetchone()
            # SUM 返回的可能是 Decimal 类型，或者在没有记录时为 None
            total_income = total_income_result[0] if total_income_result and total_income_result[0] is not None else 0.0

            # 计算总支出
            self.db_cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = '支出'")
            total_expense_result = self.db_cursor.fetchone()
            total_expense = total_expense_result[0] if total_expense_result and total_expense_result[0] is not None else 0.0

            # 将 Decimal 或 float 转为 float 进行计算和显示
            total_balance = float(total_income) - float(total_expense)

        except Error as e:
            messagebox.showerror("数据库错误", f"无法计算余额: {e}")
            total_balance = 0.0

        self.status_label.config(text=f"总余额: {total_balance:.2f}")


# --- 主程序运行部分 ---
if __name__ == "__main__":
    main_window = tk.Tk()
    app = FinanceTrackerApp(main_window)

    def on_closing():
        print("正在关闭应用程序...")
        app.close_database()
        main_window.destroy()

    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()