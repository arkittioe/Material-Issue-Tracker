import tkinter as tk
from tkinter import ttk


class HelpWindow(tk.Toplevel):
    def __init__(self, master, console_widget=None):
        super().__init__(master)
        self.title("📘 راهنمای دستورات")
        self.geometry("400x600+1050+100")  # در سمت راست پنجره اصلی باز شود
        self.configure(bg="#1e1e1e")
        self.console_widget = console_widget

        self.commands = [
            "clear",
            "help",
            "exit",
            "register",
            "copy [line_no] from [project1] to [project2]",
            "show last [n] MIV for [project]",
            "show miv for [line_no] in [project]",
            "show all MIV for [project]",
            "show complete MIV for [project]",
            "show incomplete MIV for [project]",
            "show mto for [line_no] in [project]",
            "compare mto and miv for [line_no] in [project]",
            "search [keyword] in [project]",
            "search tag [miv_tag] in [project]",
            "list projects",
            "backup project [project_code]",
            "validate project [project_code]",
            "check duplicates in [project]",
            "set current project [project_code]"
            "log commands",
        ]

        self.create_widgets()

    def create_widgets(self):
        label = tk.Label(self, text="📋 لیست دستورات:", bg="#1e1e1e", fg="white", font=("B Nazanin", 14, "bold"))
        label.pack(pady=10)

        # استفاده از اسکرول برای لیست بلند
        frame = tk.Frame(self, bg="#1e1e1e")
        frame.pack(expand=True, fill="both")

        canvas = tk.Canvas(frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#1e1e1e")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for cmd in self.commands:
            btn = tk.Button(
                scroll_frame,
                text=cmd,
                font=("Consolas", 11),
                fg="white",
                bg="#333333",
                activebackground="#444444",
                activeforeground="lightgreen",
                anchor="w",
                padx=10,
                relief="flat",
                command=lambda c=cmd: self.send_to_console(c)
            )
            btn.pack(fill="x", padx=10, pady=2)

    def send_to_console(self, command):
        if self.console_widget:
            self.console_widget.insert(tk.END, command)
            self.console_widget.focus()
