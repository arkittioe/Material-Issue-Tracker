import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from miv_registry import MIVRegistry

class ReportsWindow(tk.Toplevel):
    def __init__(self, master, registry):
        super().__init__(master)
        self.registry = registry
        self.title("Reports and Charts")
        self.geometry("800x600")
        self.configure(bg="white")
        self.create_widgets()

    def create_widgets(self):
        # --- Controls Frame ---
        controls_frame = ttk.LabelFrame(self, text="Controls")
        controls_frame.pack(padx=10, pady=10, fill="x")

        # Project Selection
        ttk.Label(controls_frame, text="Project:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.project_var = tk.StringVar()
        project_combo = ttk.Combobox(controls_frame, textvariable=self.project_var, state="readonly")
        try:
            project_combo['values'] = self.registry.list_projects()
            project_combo.set(self.registry.current_project)
        except Exception:
            project_combo['values'] = []
        project_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Line No Entry
        ttk.Label(controls_frame, text="Line No:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.line_no_var = tk.StringVar()
        line_no_entry = ttk.Entry(controls_frame, textvariable=self.line_no_var)
        line_no_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Action Buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=5)

        ttk.Button(button_frame, text="Show Project Progress", command=self.show_project_progress).pack(fill='x',
                                                                                                        pady=2)
        ttk.Button(button_frame, text="Show Line Progress", command=self.show_line_progress).pack(fill='x', pady=2)

        # --- NEW: Export Button ---
        ttk.Button(button_frame, text="Export Chart to PDF", command=self.export_to_pdf).pack(fill='x', pady=(8, 2))

        # --- Chart Frame ---
        chart_frame = ttk.Frame(self)
        chart_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.fig = plt.Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill="both", expand=True)
        # Display a welcome message on the chart initially
        self.ax.text(0.5, 0.5, "Please select a report to display.", ha='center', va='center', fontsize=12,
                     color='grey')
        self.canvas.draw()

    def show_project_progress(self):
        project_name = self.project_var.get().strip()
        if not project_name:
            messagebox.showwarning("هشدار", "لطفاً یک پروژه انتخاب کنید.")
            return

        self.ax.clear()
        report_registry = MIVRegistry(project_name)
        progress_data = report_registry.get_project_progress()

        done_weight = progress_data.get("done_weight", 0)
        total_weight = progress_data.get("total_weight", 0)
        percentage = progress_data.get("percentage", 0)

        if total_weight == 0:
            self.ax.text(0.5, 0.5, "اطلاعات MTO برای این پروژه یافت نشد.",
                         ha='center', va='center', fontsize=12)
        else:
            remaining = max(0, total_weight - done_weight)
            sizes = [done_weight, remaining]
            labels = [f"انجام شده ({round(percentage, 2)}%)", f"باقی‌مانده ({round(100 - percentage, 2)}%)"]
            colors = ['#4CAF50', '#BDBDBD']

            self.ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                wedgeprops={"edgecolor": "white", 'linewidth': 1}
            )
            self.ax.set_title(f"پیشرفت کلی پروژه: {project_name}", fontsize=13, weight='bold')
            self.ax.axis('equal')

        self.fig.tight_layout()
        self.canvas.draw()

    def show_line_progress(self):
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()

        if not project_name or not line_no:
            messagebox.showwarning("هشدار", "لطفاً پروژه و شماره خط را وارد کنید.")
            return

        self.ax.clear()
        report_registry = MIVRegistry(project_name)
        progress_data = report_registry.get_line_progress(line_no)
        percentage = progress_data.get("percentage", 0)
        total_qty = progress_data.get("total_qty", 0)

        if total_qty == 0:
            self.ax.text(0.5, 0.5, f"اطلاعاتی برای خط {line_no} یافت نشد.",
                         ha='center', va='center', fontsize=12)
        else:
            # نمایش به صورت نوار پیشرفت افقی
            self.ax.barh([0], [percentage], color='#007BFF', height=0.4, label='انجام‌شده')
            self.ax.barh([0], [100 - percentage], left=[percentage], color='#E0E0E0', height=0.4, label='باقی‌مانده')

            # درصد وسط نوار
            self.ax.text(percentage / 2, 0, f"{percentage}%", ha='center', va='center',
                         fontsize=11, color='white', weight='bold')

            self.ax.set_xlim(0, 100)
            self.ax.set_yticks([])
            self.ax.set_xlabel("درصد پیشرفت", fontsize=10)
            self.ax.set_title(f"پیشرفت متریال برای خط {line_no}", fontsize=13, weight='bold')

        self.fig.tight_layout()
        self.canvas.draw()

    def export_to_pdf(self):
        """Exports the current chart view to a PDF file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
            title="Save Chart as PDF"
        )

        if not filepath:
            # User cancelled the save dialog
            return

        try:
            # Save the figure with high quality and tight bounding box
            self.fig.savefig(filepath, format='pdf', dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Chart successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF file.\nError: {e}")