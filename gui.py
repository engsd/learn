import tkinter as tk
from tkinter import messagebox, simpledialog, Listbox, Scrollbar, Frame, Label, Entry, Button, OptionMenu, StringVar
from datetime import datetime
import sqlite3 # 导入 sqlite3 模块
import os # 用于获取脚本目录

class FinanceTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人理财追踪器 (数据库版)")
        self.root.geometry("600x450") # 可以稍微调整窗口大小以适应

        self.db_conn = None # 初始化数据库连接变量
        self.db_cursor = None # 初始化游标变量
        self.setup_database() # 设置数据库

        # --- 界面元素 ---
        # 输入区域框架
        input_frame = Frame(root, padx=10, pady=10)
        input_frame.pack(fill=tk.X)

        # 类型选择
        Label(input_frame, text="类型:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.type_var = StringVar(root)
        self.type_var.set("支出") # 默认值
        type_options = ["支出", "收入"]
        type_menu = OptionMenu(input_frame, self.type_var, *type_options)
        type_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        type_menu.config(width=8) # 调整下拉菜单宽度

        # 描述输入
        Label(input_frame, text="描述:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.desc_entry = Entry(input_frame) # 宽度自适应
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        # 金额输入
        Label(input_frame, text="金额:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.amount_entry = Entry(input_frame) # 宽度自适应
        self.amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        # 配置输入区域列的权重，让输入框可以扩展
        input_frame.columnconfigure(1, weight=1)

        # 添加按钮
        add_button = Button(input_frame, text="添加记录", command=self.add_transaction)
        add_button.grid(row=3, column=0, columnspan=2, pady=10)

        # 列表区域框架
        list_frame = Frame(root, padx=10, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 列表框和滚动条
        Label(list_frame, text="交易记录:").pack(anchor='w')
        scrollbar_frame = Frame(list_frame) # 用于容纳 Listbox 和 Scrollbar
        scrollbar_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = Scrollbar(scrollbar_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.transaction_listbox = Listbox(scrollbar_frame, yscrollcommand=scrollbar.set, height=15)
        self.transaction_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.transaction_listbox.yview)

        # 状态/汇总区域
        self.status_label = Label(root, text="总余额: 0.00", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 初始化时从数据库加载数据并更新显示
        if self.db_conn: # 确保数据库连接成功
            self.update_transaction_list()
            self.update_status()


    def get_db_path(self):
        """获取数据库文件的路径，确保在脚本同目录下"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, 'finance_tracker.db')

    def setup_database(self):
        """建立数据库连接并创建表"""
        db_path = self.get_db_path()
        try:
            self.db_conn = sqlite3.connect(db_path)
            self.db_cursor = self.db_conn.cursor()
            # 创建 transactions 表 (如果不存在)
            # 使用 INTEGER PRIMARY KEY AUTOINCREMENT 确保 id 唯一且自增
            # 使用 TEXT 存储时间和类型，REAL 存储金额
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('收入', '支出')),
                    description TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount > 0)
                )
            ''')
            self.db_conn.commit() # 提交更改
            print(f"数据库已连接并设置: {db_path}") # 打印数据库路径方便调试
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法连接或初始化数据库: {e}\n数据库路径: {db_path}")
            self.db_conn = None # 标记连接失败
            # 如果数据库无法设置，可能需要禁用相关功能或退出
            # self.root.quit()

    def close_database(self):
         """关闭数据库连接"""
         if self.db_conn:
             self.db_conn.close()
             print("数据库连接已关闭")

    def add_transaction(self):
        """添加一笔交易记录到数据库"""
        if not self.db_conn:
             messagebox.showerror("错误", "数据库未连接，无法添加记录。")
             return

        trans_type = self.type_var.get()
        description = self.desc_entry.get()
        amount_str = self.amount_entry.get()

        if not description or not amount_str:
            messagebox.showwarning("输入错误", "描述和金额不能为空！")
            return

        try:
            # 金额必须是正数
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("金额必须为正数")
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的正数金额！")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 将数据插入数据库，金额始终存为正数
            self.db_cursor.execute('''
                INSERT INTO transactions (timestamp, type, description, amount)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, trans_type, description, amount))
            self.db_conn.commit() # 提交事务

            # 更新界面
            self.update_transaction_list()
            self.update_status()

            # 清空输入框
            self.desc_entry.delete(0, tk.END)
            self.amount_entry.delete(0, tk.END)
            self.type_var.set("支出") # 重置类型为默认

        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法添加记录: {e}")
            try:
                self.db_conn.rollback() # 如果出错则回滚
            except sqlite3.Error as rb_e:
                 messagebox.showerror("数据库错误", f"回滚失败: {rb_e}")

    def update_transaction_list(self):
        """从数据库获取记录并更新列表框显示"""
        if not self.db_conn: return # 如果数据库未连接则不执行

        self.transaction_listbox.delete(0, tk.END) # 清空列表
        try:
            # 从数据库查询所有记录，按时间戳降序排列 (最新的在前面)
            self.db_cursor.execute("SELECT timestamp, type, description, amount FROM transactions ORDER BY timestamp DESC")
            all_transactions = self.db_cursor.fetchall()

            for trans in all_transactions:
                timestamp, trans_type, description, amount = trans
                # 根据类型决定符号
                sign = "+" if trans_type == "收入" else "-"
                display_text = f"{timestamp} | {trans_type}: {description} | {sign}{amount:.2f}"
                # 在列表开头插入，保持最新记录在顶部
                self.transaction_listbox.insert(tk.END, display_text)

        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法加载交易记录: {e}")

    def update_status(self):
        """从数据库计算并更新总余额"""
        if not self.db_conn: return # 如果数据库未连接则不执行

        total_balance = 0.0
        try:
            # 使用 SQL 的 SUM 函数计算总收入
            self.db_cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = '收入'")
            total_income_result = self.db_cursor.fetchone()
            # fetchone 返回元组，取第一个元素；如果无收入记录，SUM 可能返回 None
            total_income = total_income_result[0] if total_income_result and total_income_result[0] is not None else 0.0

            # 使用 SQL 的 SUM 函数计算总支出
            self.db_cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = '支出'")
            total_expense_result = self.db_cursor.fetchone()
            total_expense = total_expense_result[0] if total_expense_result and total_expense_result[0] is not None else 0.0

            total_balance = total_income - total_expense
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法计算余额: {e}")
            total_balance = 0.0 # 出错时显示0

        self.status_label.config(text=f"总余额: {total_balance:.2f}")


# --- 主程序运行部分 ---
if __name__ == "__main__":
    main_window = tk.Tk()
    app = FinanceTrackerApp(main_window)

    # 定义关闭窗口时的回调函数
    def on_closing():
        print("正在关闭应用程序...")
        app.close_database() # 关闭数据库连接
        main_window.destroy() # 销毁窗口

    # 将关闭窗口事件绑定到 on_closing 函数
    main_window.protocol("WM_DELETE_WINDOW", on_closing)

    # 启动 Tkinter 事件循环
    main_window.mainloop()