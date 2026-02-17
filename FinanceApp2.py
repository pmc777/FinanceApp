import customtkinter as ctk
import json
import os
from datetime import datetime
import tkinter.messagebox as msg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ExpenseTracker(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Peta's Expense Tracker")
        self.geometry("900x750")
        self.resizable(True, True)

        self.transactions = []
        self.categories = ["Food", "Entertainment", "Transport", "Bills", "Income", "Other"]
        self.load_transactions()

        self.create_header()
        self.create_input_area()
        self.create_transaction_list()
        self.create_summary_area()
        self.create_chart_area()

        self.refresh_transactions()
        self.update_summary()

    # ---------------- HEADER ----------------
    def create_header(self):
        header = ctk.CTkLabel(self, text="Expense Tracker", font=("Segoe UI", 28, "bold"))
        header.pack(pady=(20, 10))

    # ---------------- INPUT AREA ----------------
    def create_input_area(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=10)

        today = datetime.now().strftime("%Y-%m-%d")

        self.date_entry = ctk.CTkEntry(frame, width=120)
        self.date_entry.insert(0, today)
        self.date_entry.pack(side="left", padx=5)

        self.amount_entry = ctk.CTkEntry(frame, placeholder_text="Amount (-50 or 100)", width=150)
        self.amount_entry.pack(side="left", padx=5)

        self.category_combo = ctk.CTkComboBox(frame, values=self.categories, width=150)
        self.category_combo.set("Food")
        self.category_combo.pack(side="left", padx=5)

        self.desc_entry = ctk.CTkEntry(frame, placeholder_text="Description...", width=200)
        self.desc_entry.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(frame, text="Add", width=80, command=self.add_transaction)
        add_btn.pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self.add_transaction())

    # ---------------- TRANSACTION LIST ----------------
    def create_transaction_list(self):
        self.trans_frame = ctk.CTkScrollableFrame(self, height=200)
        self.trans_frame.pack(fill="both", padx=20, pady=10)
        self.trans_widgets = []

    def refresh_transactions(self):
        for w in self.trans_widgets:
            w.destroy()
        self.trans_widgets.clear()

        if not self.transactions:
            lbl = ctk.CTkLabel(self.trans_frame, text="No transactions yet!", text_color="gray")
            lbl.pack(pady=40)
            self.trans_widgets.append(lbl)
            return

        self.transactions.sort(key=lambda t: t["date"], reverse=True)

        for i, trans in enumerate(self.transactions):
            row = ctk.CTkFrame(self.trans_frame)
            row.pack(fill="x", pady=3, padx=5)

            ctk.CTkLabel(row, text=trans["date"], width=100).pack(side="left", padx=5)

            color = "green" if trans["amount"] > 0 else "red"
            ctk.CTkLabel(row, text=f"${trans['amount']:.2f}", text_color=color, width=80).pack(side="left", padx=5)

            ctk.CTkLabel(row, text=trans["category"], width=120).pack(side="left", padx=5)

            ctk.CTkLabel(row, text=trans["desc"], anchor="w").pack(side="left", fill="x", expand=True)

            del_btn = ctk.CTkButton(row, text="×", width=30,
                                    fg_color="transparent",
                                    text_color="red",
                                    command=lambda idx=i: self.delete_transaction(idx))
            del_btn.pack(side="right")

            self.trans_widgets.append(row)

    # ---------------- ADD / DELETE ----------------
    def add_transaction(self):
        try:
            date_str = self.date_entry.get().strip()
            datetime.strptime(date_str, "%Y-%m-%d")
            amount = float(self.amount_entry.get().strip())
            category = self.category_combo.get()
            desc = self.desc_entry.get().strip() or "No description"

            self.transactions.append({
                "date": date_str,
                "amount": amount,
                "category": category,
                "desc": desc
            })

            self.amount_entry.delete(0, "end")
            self.desc_entry.delete(0, "end")

            self.save_transactions()
            self.refresh_transactions()
            self.update_summary()

        except ValueError:
            msg.showerror("Invalid Input", "Check date and amount format.")

    def delete_transaction(self, index):
        if msg.askyesno("Confirm", "Delete this transaction?"):
            del self.transactions[index]
            self.save_transactions()
            self.refresh_transactions()
            self.update_summary()

    # ---------------- SUMMARY ----------------
    def create_summary_area(self):
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.pack(fill="x", padx=20, pady=10)

        self.month_combo = ctk.CTkComboBox(self.summary_frame, width=150)
        self.month_combo.pack(side="left", padx=10)
        self.month_combo.bind("<<ComboboxSelected>>", lambda e: self.update_summary())

        self.summary_label = ctk.CTkLabel(
            self.summary_frame,
            text="",
            justify="left",
            font=("Segoe UI", 14)
        )
        self.summary_label.pack(side="left", fill="x", expand=True, padx=10)

    def update_summary(self):
        if not self.transactions:
            self.summary_label.configure(text="No transactions yet.")
            self.clear_chart()
            return

        df = pd.DataFrame(self.transactions)
        df["date"] = pd.to_datetime(df["date"])

        months = sorted(df["date"].dt.strftime("%Y-%m").unique(), reverse=True)
        self.month_combo.configure(values=months)

        selected_month = self.month_combo.get() or months[0]
        self.month_combo.set(selected_month)

        monthly = df[df["date"].dt.strftime("%Y-%m") == selected_month]

        income = monthly[monthly["amount"] > 0]["amount"].sum()
        expense = abs(monthly[monthly["amount"] < 0]["amount"].sum())
        balance = income - expense

        summary_text = (
            f"Month: {selected_month}\n\n"
            f"Income:   ${income:,.2f}\n"
            f"Expenses: ${expense:,.2f}\n"
            f"Balance:  ${balance:,.2f}"
        )

        self.summary_label.configure(text=summary_text)

        self.update_chart(selected_month)

    # ---------------- CHART ----------------
    def create_chart_area(self):
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.canvas = None

    def clear_chart(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None

    def update_chart(self, month):
        self.clear_chart()

        df = pd.DataFrame(self.transactions)
        df["date"] = pd.to_datetime(df["date"])
        monthly = df[df["date"].dt.strftime("%Y-%m") == month]

        expenses = monthly[monthly["amount"] < 0].copy()
        if expenses.empty:
            return

        grouped = expenses.groupby("category")["amount"].sum().abs()

        fig, ax = plt.subplots(figsize=(6, 5))

        wedges, texts, autotexts = ax.pie(
            grouped,
            autopct="%1.1f%%",
            startangle=90
        )

        # Donut style
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig.gca().add_artist(centre_circle)

        ax.legend(wedges, grouped.index, title="Categories",
                  loc="center left", bbox_to_anchor=(1, 0.5))

        ax.set_title(f"Expenses by Category – {month}")
        plt.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)

    # ---------------- PERSISTENCE ----------------
    def get_data_file(self):
        return "transactions.json"

    def load_transactions(self):
        if os.path.exists(self.get_data_file()):
            with open(self.get_data_file(), "r") as f:
                self.transactions = json.load(f)

    def save_transactions(self):
        with open(self.get_data_file(), "w") as f:
            json.dump(self.transactions, f, indent=2)


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()
