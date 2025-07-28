import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# Assuming MIVRegistry is correctly defined and available
from miv_registry import MIVRegistry


class ReportsWindow(tk.Toplevel):
    def __init__(self, master, registry):
        super().__init__(master)
        self.registry = registry
        self.title("Reports and Charts")
        self.geometry("1000x800")
        self.configure(bg="white")
        self.current_chart_type = None  # To track which chart is currently displayed
        self.create_widgets()

    def create_widgets(self):
        # --- Main Layout Frames ---
        # Use a main frame to organize controls and chart area
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Controls Frame (top)
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding=(10, 10))
        controls_frame.pack(padx=5, pady=5, fill="x")
        controls_frame.columnconfigure(1, weight=1)  # Allow project_combo and line_no_entry to expand
        controls_frame.columnconfigure(3, weight=1)  # Allow report_type_combo to expand

        # Chart Frame (middle)
        chart_frame = ttk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        chart_frame.pack(padx=5, pady=5, fill="both", expand=True)

        # Bottom Buttons Frame (bottom)
        bottom_buttons_frame = ttk.Frame(main_frame, padding=(0, 5))
        bottom_buttons_frame.pack(padx=5, pady=5, fill="x")

        # --- Controls Frame Widgets ---
        # Project Selection
        ttk.Label(controls_frame, text="Project:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5,
                                                                                    sticky="w")
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(controls_frame, textvariable=self.project_var, state="readonly", width=30)
        self.project_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self._load_projects_into_combo()  # Load projects when initializing

        # Line No Entry
        ttk.Label(controls_frame, text="Line No:", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5,
                                                                                    sticky="w")
        self.line_no_var = tk.StringVar()
        self.line_no_entry = ttk.Entry(controls_frame, textvariable=self.line_no_var,
                                       width=30)  # Store as self.line_no_entry
        self.line_no_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Report Type Selection
        ttk.Label(controls_frame, text="Report Type:", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=(15, 5),
                                                                                        pady=5, sticky="w")
        self.report_type_var = tk.StringVar(value="Project Progress (Pie)")  # Default selection
        self.report_type_combo = ttk.Combobox(controls_frame, textvariable=self.report_type_var, state="readonly",
                                              width=30)
        self.report_type_combo['values'] = [
            "Project Progress (Pie)",
            "Project Progress (Bar)",
            "Line Progress (Horizontal Bar)",
            "Line Material Breakdown (Bar)",
            "Line Material progress",
        ]
        self.report_type_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.report_type_combo.bind("<<ComboboxSelected>>", self.on_report_type_selected)
        # Initial call to set state based on default selection
        self.on_report_type_selected()

        # Action Buttons within Controls Frame
        ttk.Button(controls_frame, text="Generate Report", command=self.generate_selected_report).grid(row=1, column=2,
                                                                                                       columnspan=2,
                                                                                                       padx=(15, 5),
                                                                                                       pady=5,
                                                                                                       sticky="ew")

        # --- Chart Frame Widgets ---
        self.fig = plt.Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill="both", expand=True)

        self.display_initial_message("Please select a report type and generate to display.")

        # --- Bottom Buttons Frame Widgets ---
        # Centered "Export" button
        export_button = ttk.Button(bottom_buttons_frame, text="Export Chart to PDF", command=self.export_to_pdf)
        export_button.pack(side=tk.RIGHT, padx=5)  # Align to the right

    def _load_projects_into_combo(self):
        """Helper to load project names into the combobox."""
        try:
            projects = self.registry.list_projects()
            self.project_combo['values'] = projects
            if projects:
                # Set current project if available, otherwise default to first
                if self.registry.current_project and self.registry.current_project in projects:
                    self.project_var.set(self.registry.current_project)
                else:
                    self.project_var.set(projects[0])
            else:
                self.project_var.set("")  # Clear if no projects
                messagebox.showinfo("Info", "No projects found in the registry. Please create one.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load projects: {e}")
            self.project_combo['values'] = []
            self.project_var.set("Error loading projects")

    def display_initial_message(self, message):
        """Clears the axis and displays a message."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12, color='grey')
        self.ax.set_xticks([])  # Hide ticks for a cleaner message display
        self.ax.set_yticks([])
        self.canvas.draw()

    def on_report_type_selected(self, event=None):
        """Handle selection change in report type combobox, enabling/disabling line_no_entry."""
        selected_type = self.report_type_var.get()
        if "Line" in selected_type:
            self.line_no_entry.config(state="normal")
        else:
            self.line_no_entry.config(state="disabled")
            self.line_no_var.set("")  # Clear line number if not a line report

    def generate_selected_report(self):
        """Generates the report based on the selected type."""
        selected_type = self.report_type_var.get()
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()

        # Basic validation before calling specific report functions
        if not project_name:
            messagebox.showwarning("Warning", "Please select a project.")
            self.display_initial_message("Please select a project to generate the report.")
            return

        if "Line" in selected_type and not line_no:
            messagebox.showwarning("Warning", "Please enter a line number for line-related reports.")
            self.display_initial_message("Please enter a line number to generate the line report.")
            return

        # Map selected type to appropriate function
        if selected_type == "Project Progress (Pie)":
            self.show_project_progress_pie()
        elif selected_type == "Project Progress (Bar)":
            self.show_project_progress_bar()
        elif selected_type == "Line Progress (Horizontal Bar)":
            self.show_line_progress_horizontal_bar()
        elif selected_type == "Line Material progress":
            self.show_line_material_progress()
        elif selected_type == "Line Material Breakdown (Bar)":
            self.show_line_material_breakdown()
        else:
            messagebox.showerror("Error", "Invalid report type selected.")
            self.display_initial_message("Error: Invalid report type selected.")

    def show_project_progress_pie(self):
        project_name = self.project_var.get().strip()
        self.ax.clear()
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        try:
            report_registry = MIVRegistry(project_name)
            progress_data = report_registry.get_project_progress()

            done_weight = progress_data.get("done_weight", 0)
            total_weight = progress_data.get("total_weight", 0)
            percentage = progress_data.get("percentage", 0)

            if total_weight <= 0:
                self.display_initial_message(
                    f"No MTO data found for project '{project_name}', or total weight is zero.")
            else:
                remaining = max(0, total_weight - done_weight)
                sizes = [done_weight, remaining]
                labels = [f"Completed ({round(percentage, 2)}%)", f"Remaining ({round(100 - percentage, 2)}%)"]
                colors = ['#4CAF50', '#BDBDBD']  # Green and Gray

                wedges, texts, autotexts = self.ax.pie(
                    sizes,
                    labels=labels,
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=colors,
                    wedgeprops={"edgecolor": "white", 'linewidth': 1.5},
                    pctdistance=0.85
                )

                # Style the percentage texts inside the pie
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(10)
                    autotext.set_weight('bold')

                # Draw a white circle at the center to create a donut chart effect
                centre_circle = plt.Circle((0, 0), 0.65, fc='white')
                self.ax.add_artist(centre_circle)

                self.ax.set_title(
                    f"Overall Project Progress: {project_name}",
                    fontsize=14,
                    weight='bold',
                    pad=20
                )
                self.ax.axis('equal')  # Equal aspect ratio ensures the pie is circular
                self.fig.tight_layout()

            self.current_chart_type = "Project Progress (Pie)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project progress for '{project_name}'.\nError: {e}")
            self.display_initial_message(f"Error showing project progress: {e}")

        self.canvas.draw()

    def show_project_progress_bar(self):
        project_name = self.project_var.get().strip()
        self.ax.cla()  # پاکسازی کامل‌تر نمودار
        try:
            report_registry = MIVRegistry(project_name)
            progress_data = report_registry.get_project_progress()

            done_weight = progress_data.get("done_weight", 0)
            total_weight = progress_data.get("total_weight", 0)
            remaining_weight = max(0, total_weight - done_weight)

            if total_weight <= 0:
                self.display_initial_message(
                    f"No MTO data found or total weight is zero for project '{project_name}'."
                )
            else:
                done_percent = (done_weight / total_weight) * 100
                remaining_percent = 100 - done_percent

                # داده‌ها و برچسب‌ها
                labels = ['Done', 'Remaining']
                weights = [done_weight, remaining_weight]
                percents = [done_percent, remaining_percent]

                # رسم نمودار
                bars = self.ax.bar(labels, weights, color=['#4CAF50', '#BDBDBD'], width=0.5)

                # تنظیم محور y با حاشیه بیشتر
                max_val = max(weights)
                self.ax.set_ylim(0, max_val * 1.25)

                # عنوان و برچسب‌ها
                self.ax.set_ylabel("Weight", fontsize=11)
                self.ax.set_title(f"Project Weight Progress: {project_name}",
                                  fontsize=14, weight='bold', pad=15)

                # اضافه کردن برچسب‌های بالا با فاصله مناسب
                for bar, weight, percent in zip(bars, weights, percents):
                    height = bar.get_height()
                    self.ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height + (max_val * 0.05),  # فاصله بیشتر برای جلوگیری از تداخل
                        f"{weight:.1f} ({percent:.1f}%)",
                        ha='center', va='bottom', fontsize=10
                    )

                # حذف حاشیه‌های اضافی
                self.ax.spines['right'].set_visible(False)
                self.ax.spines['top'].set_visible(False)

                self.fig.tight_layout()

            self.current_chart_type = "Project Progress (Bar)"

        except Exception as e:
            messagebox.showerror("Error",
                                 f"Failed to generate project progress report (bar chart) for '{project_name}'.\nError: {e}")
            self.display_initial_message(f"Error displaying project progress: {e}")

        self.canvas.draw()

    def show_line_progress_horizontal_bar(self):
        # گرفتن نام پروژه و شماره خط از ورودی‌های رابط کاربری
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()

        # پاک‌سازی نمودار قبلی
        self.ax.clear()

        try:
            # ساخت شیء رجیستری برای پروژه
            report_registry = MIVRegistry(project_name)
            # گرفتن داده‌های پیشرفت برای خط موردنظر
            progress_data = report_registry.get_line_progress(line_no)

            percentage = progress_data.get("percentage", 0)
            total_qty = progress_data.get("total_qty", 0)

            # بررسی اینکه آیا داده‌ای وجود دارد یا نه
            if total_qty <= 0:
                self.display_initial_message(f"No data found for line '{line_no}' in project '{project_name}'.")
            else:
                # محدود کردن درصد بین 0 و 100
                percentage = max(0, min(100, percentage))

                # رسم نوار انجام‌شده (سبز)
                self.ax.barh([0], [percentage], color='#28A745', height=0.6, label='Completed')

                # رسم نوار باقی‌مانده (خاکستری)، از سمت راست نوار سبز ادامه پیدا می‌کند
                self.ax.barh([0], [100 - percentage], left=[percentage], color='#D3D3D3', height=0.6, label='Remaining')

                # نوشتن مقدار درصد وسط نوار سبز
                self.ax.text(percentage / 2, 0, f"{percentage:.1f}%", ha='center', va='center',
                             fontsize=12, color='white', weight='bold')

                # تنظیمات محور
                self.ax.set_xlim(0, 100)
                self.ax.set_xticks([0, 25, 50, 75, 100])
                self.ax.set_xticklabels([f'{i}%' for i in [0, 25, 50, 75, 100]])
                self.ax.set_yticks([])
                self.ax.set_xlabel("Progress Percentage", fontsize=11)
                self.ax.set_title(f"Line Material Progress - Line {line_no}", fontsize=14, weight='bold', pad=15)

                # حذف قاب‌های اضافی و تنظیمات ظاهری
                self.ax.spines['right'].set_visible(False)
                self.ax.spines['top'].set_visible(False)
                self.ax.spines['left'].set_visible(False)
                self.ax.spines['bottom'].set_linewidth(0.5)
                self.ax.tick_params(axis='x', length=4, width=0.5)

                self.fig.tight_layout()

            # ذخیره نوع نمودار فعلی
            self.current_chart_type = "Line Progress (Horizontal Bar)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load line progress for '{line_no}'.\nError: {e}")
            self.display_initial_message(f"Error showing line progress: {e}")

        # رسم نهایی نمودار
        self.canvas.draw()

    def show_line_material_breakdown(self):
        import matplotlib.patches as mpatches
        import numpy as np

        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()
        self.ax.clear()
        try:
            report_registry = MIVRegistry(project_name)
            material_data = report_registry.get_line_material_breakdown(line_no)

            if not material_data:
                self.display_initial_message(
                    f"No material breakdown data found for line '{line_no}' in project '{project_name}'.")
            else:
                materials = list(material_data.keys())
                quantities = list(material_data.values())
                total_qty = sum(quantities)

                cmap = plt.get_cmap('Set2')
                colors = [cmap(i) for i in np.linspace(0, 1, len(materials))]

                bars = self.ax.bar(range(len(materials)), quantities, color=colors)

                # برچسب‌های محور x به صورت عمودی
                self.ax.set_xticks(range(len(materials)))
                self.ax.set_xticklabels(materials, rotation=90, fontsize=9)
                self.ax.tick_params(axis='x', which='both', length=0)  # حذف خط‌های کوچک محور x

                # عنوان نمودار و برچسب محور y
                self.ax.set_ylabel("Quantity", fontsize=11)
                self.ax.set_title(f"Material Breakdown for Line {line_no}", fontsize=14, weight='bold', pad=20)

                max_qty = max(quantities)
                self.ax.set_ylim(0, max_qty * 1.15)

                # مقدار + درصد بالای ستون‌ها
                for bar, qty in zip(bars, quantities):
                    percent = (qty / total_qty) * 100 if total_qty > 0 else 0
                    self.ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + (max_qty * 0.02),
                        f"{qty:.1f} ({percent:.1f}%)",
                        ha='center',
                        va='bottom',
                        fontsize=8,
                        rotation=90  # 👈 عمودی کردن متن
                    )

                self.ax.spines['right'].set_visible(False)
                self.ax.spines['top'].set_visible(False)

                # لجند سمت راست
                legend_patches = [mpatches.Patch(color=colors[i], label=mat) for i, mat in enumerate(materials)]
                self.ax.legend(handles=legend_patches, bbox_to_anchor=(1.05, 1), loc='upper left',
                               borderaxespad=0., fontsize=9)

                self.fig.tight_layout(rect=[0, 0, 0.85, 1])

            self.current_chart_type = "Line Material Breakdown (Bar)"
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate material breakdown for line '{line_no}'.\nError: {e}")
            self.display_initial_message(f"Error generating material breakdown: {e}")
        self.canvas.draw()

    def export_to_pdf(self):
        """Exports the current chart view to a PDF file."""
        if not self.current_chart_type:
            messagebox.showwarning("هشدار", "هیچ گزارشی برای صادر کردن تولید نشده است.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
            title="ذخیره نمودار به صورت PDF"
        )

        if not filepath:
            messagebox.showinfo("اطلاعات", "صادرات PDF لغو شد.")
            return

        try:
            # More robust check: see if there are any non-text artists (like bars, wedges, lines)
            # or if the only artist is our initial message text.
            has_actual_data = False
            for artist in self.ax.get_children():
                # Check for common matplotlib artists that signify data (e.g., Rectangle for bars, Wedge for pie)
                # This is a heuristic and might need adjustment based on your specific charts.
                if isinstance(artist, (plt.Rectangle, plt.Circle, plt.Line2D, plt.Polygon)) and not isinstance(artist,
                                                                                                               plt.Text):
                    has_actual_data = True
                    break

            # Also check if the current chart is just showing the initial message
            if not has_actual_data and any(isinstance(a, plt.Text) and "Please select a report" in a.get_text() for a in
                                           self.ax.get_children()):
                messagebox.showwarning("هشدار",
                                       "هیچ نمودار فعالی برای صادرات وجود ندارد. لطفاً ابتدا یک گزارش تولید کنید.")
                return

            self.fig.savefig(filepath, format='pdf', dpi=300, bbox_inches='tight')
            messagebox.showinfo("موفقیت", f"نمودار با موفقیت در مسیر زیر ذخیره شد:\n{filepath}")
        except PermissionError:
            messagebox.showerror(
                "اجازه دسترسی رد شد",
                f"نمی‌توان در '{filepath}' ذخیره کرد. لطفاً بررسی کنید که فایل باز نباشد یا مجوز نوشتن در پوشه انتخابی را داشته باشید."
            )
        except IOError as e:
            messagebox.showerror(
                "خطای دیسک",
                f"خطای ورودی/خروجی هنگام ذخیره فایل رخ داد. لطفاً فضای دیسک یا پوشه مقصد را بررسی کنید.\nخطا: {e}"
            )
        except Exception as e:
            messagebox.showerror("خطای صادرات", f"خطای غیرمنتظره‌ای در هنگام صادرات PDF رخ داد.\nخطا: {e}")

    def show_line_material_progress(self):
        project = self.project_var.get()
        line_no = self.line_no_var.get()

        if not project or not line_no:
            self.display_initial_message("Please select a valid project and enter a line number.")
            return

        try:
            # فرض بر این است که تابع get_material_progress را در MIVRegistry ساختیم:
            # خروجی باید به صورت DataFrame یا لیست دیکشنری با این ستون‌ها باشد:
            # Item Code, Description, Total Qty, Used Qty, Remaining Qty
            progress_df = self.registry.get_material_progress(project, line_no)

            if progress_df.empty:
                self.display_initial_message("No material progress data available for this line.")
                return

            self.ax.clear()

            # داده‌ها را آماده کنیم
            labels = progress_df["Item Code"].astype(str).tolist()
            used = progress_df["Used Qty"].astype(float).tolist()
            remaining = progress_df["Remaining Qty"].astype(float).tolist()

            x = range(len(labels))

            # نمودار stacked bar رسم کنیم
            self.ax.bar(x, used, label="Used Qty", color="tab:blue")
            self.ax.bar(x, remaining, bottom=used, label="Remaining Qty", color="tab:gray", alpha=0.5)

            # لیبل آیتم کدها عمودی و مرتب
            self.ax.set_xticks(x)
            self.ax.set_xticklabels(labels, rotation=90, fontsize=8)

            self.ax.set_ylabel("Quantity")
            self.ax.set_title(f"Material Progress for Project '{project}', Line {line_no}")
            self.ax.legend()

            self.fig.tight_layout()
            self.canvas.draw()

        except Exception as e:
            self.display_initial_message(f"Error loading data: {e}")
