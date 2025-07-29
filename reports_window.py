import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# Assuming MIVRegistry is correctly defined and available
from miv_registry import MIVRegistry
import matplotlib.patches as mpatches
import numpy as np


class ReportsWindow(tk.Toplevel):
    def __init__(self, master, registry):
        super().__init__(master)
        self.registry = registry
        self.title("Reports and Charts")
        self.geometry("1000x800")
        self.configure(bg="white")
        self.current_chart_type = None
        self.create_widgets()

    def create_widgets(self):
        # --- Main Layout Frames ---
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding=(10, 10))
        controls_frame.pack(padx=5, pady=5, fill="x")
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.columnconfigure(3, weight=1)

        chart_frame = ttk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        chart_frame.pack(padx=5, pady=5, fill="both", expand=True)

        bottom_buttons_frame = ttk.Frame(main_frame, padding=(0, 5))
        bottom_buttons_frame.pack(padx=5, pady=5, fill="x")

        # --- Controls Frame Widgets ---
        ttk.Label(controls_frame, text="Project:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5,
                                                                                    sticky="w")
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(controls_frame, textvariable=self.project_var, state="readonly", width=30)
        self.project_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self._load_projects_into_combo()

        ttk.Label(controls_frame, text="Line No:", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5,
                                                                                    sticky="w")
        self.line_no_var = tk.StringVar()
        self.line_no_entry = ttk.Entry(controls_frame, textvariable=self.line_no_var, width=30)
        self.line_no_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(controls_frame, text="Report Type:", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=(15, 5),
                                                                                        pady=5, sticky="w")
        self.report_type_var = tk.StringVar(value="Project Progress (Pie)")
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
        self.on_report_type_selected()

        ttk.Button(controls_frame, text="Generate Report", command=self.generate_selected_report).grid(row=1, column=2,
                                                                                                       columnspan=2,
                                                                                                       padx=(15, 5),
                                                                                                       pady=5,
                                                                                                       sticky="ew")

        # --- Chart Frame Widgets ---
        self.fig = plt.Figure(figsize=(7, 5), dpi=100, constrained_layout=True)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill="both", expand=True)

        self.display_initial_message("Please select a report type and generate to display.")

        export_button = ttk.Button(bottom_buttons_frame, text="Export Chart to PDF", command=self.export_to_pdf)
        export_button.pack(side=tk.RIGHT, padx=5)

    def _load_projects_into_combo(self):
        try:
            projects = self.registry.list_projects()
            self.project_combo['values'] = projects
            if projects:
                if self.registry.current_project and self.registry.current_project in projects:
                    self.project_var.set(self.registry.current_project)
                else:
                    self.project_var.set(projects[0])
            else:
                self.project_var.set("")
                messagebox.showinfo("Info", "No projects found in the registry. Please create one.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load projects: {e}")
            self.project_combo['values'] = []
            self.project_var.set("Error loading projects")

    def display_initial_message(self, message):
        self.ax.clear()
        self.ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12, color='grey')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def on_report_type_selected(self, event=None):
        selected_type = self.report_type_var.get()
        if "Line" in selected_type:
            self.line_no_entry.config(state="normal")
        else:
            self.line_no_entry.config(state="disabled")
            self.line_no_var.set("")

    def generate_selected_report(self):
        selected_type = self.report_type_var.get()
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()

        if not project_name:
            messagebox.showwarning("Warning", "Please select a project.")
            self.display_initial_message("Please select a project to generate the report.")
            return

        if "Line" in selected_type and not line_no:
            messagebox.showwarning("Warning", "Please enter a line number for line-related reports.")
            self.display_initial_message("Please enter a line number to generate the line report.")
            return

        report_map = {
            "Project Progress (Pie)": self.show_project_progress_pie,
            "Project Progress (Bar)": self.show_project_progress_bar,
            "Line Progress (Horizontal Bar)": self.show_line_progress_horizontal_bar,
            "Line Material progress": self.show_line_material_progress,
            "Line Material Breakdown (Bar)": self.show_line_material_breakdown,
        }

        report_func = report_map.get(selected_type)
        if report_func:
            report_func()
        else:
            messagebox.showerror("Error", "Invalid report type selected.")
            self.display_initial_message("Error: Invalid report type selected.")

    def show_project_progress_pie(self):
        project_name = self.project_var.get().strip()
        self.ax.clear()

        try:
            report_registry = MIVRegistry(project_name)
            progress_data = report_registry.get_project_progress()

            done_weight = progress_data.get("done_weight", 0)
            total_weight = progress_data.get("total_weight", 0)

            if total_weight <= 0:
                self.display_initial_message(f"No MTO data found for project '{project_name}'.")
                return

            remaining = max(0, total_weight - done_weight)
            percentage = (done_weight / total_weight) * 100 if total_weight > 0 else 0

            sizes = [done_weight, remaining]
            labels = [f"Completed ({percentage:.1f}%)", f"Remaining ({(100 - percentage):.1f}%)"]
            colors = ['#4CAF50', '#BDBDBD']

            wedges, texts, autotexts = self.ax.pie(
                sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors,
                wedgeprops={"edgecolor": "white", 'linewidth': 1.5}, pctdistance=0.85
            )

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')

            centre_circle = plt.Circle((0, 0), 0.65, fc='white')
            self.ax.add_artist(centre_circle)

            self.ax.set_title(f"Overall Project Progress: {project_name}", fontsize=14, weight='bold', pad=20)
            self.ax.axis('equal')
            self.current_chart_type = "Project Progress (Pie)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project progress for '{project_name}'.\nError: {e}")
            self.display_initial_message(f"Error showing project progress: {e}")

        self.canvas.draw()

    def show_project_progress_bar(self):
        project_name = self.project_var.get().strip()
        self.ax.clear()
        try:
            # Assuming MIVRegistry is available and works correctly
            report_registry = MIVRegistry(project_name)
            progress_data = report_registry.get_project_progress()

            done_weight = progress_data.get("done_weight", 0)
            total_weight = progress_data.get("total_weight", 0)

            if total_weight <= 0:
                self.display_initial_message(f"No MTO data found for project '{project_name}'.")
                self.canvas.draw()
                return

            remaining_weight = max(0, total_weight - done_weight)
            done_percent = (done_weight / total_weight) * 100 if total_weight > 0 else 0

            # --- NEW STRATEGY: SINGLE STACKED BAR CHART ---
            # This approach is robust, clean, and completely avoids text overlap issues
            # by using a single stacked bar instead of two separate bars.

            bar_width = 0.4  # A single bar can be a bit wider
            # The label for the single bar on the x-axis
            x_label = [f"Project Progress"]

            # 1. Draw the 'Done' part of the bar (the green part)
            self.ax.bar(x_label, done_weight, width=bar_width, label=f'Done ({done_weight:.1f})', color='#4CAF50')

            # 2. Draw the 'Remaining' part on top of the 'Done' part
            self.ax.bar(x_label, remaining_weight, width=bar_width, bottom=done_weight,
                        label=f'Remaining ({remaining_weight:.1f})', color='#BDBDBD')

            # --- NEW, SIMPLIFIED LABELING ---
            # Only add one clear percentage label inside the 'Done' section
            # if there's enough space.
            if done_weight > total_weight * 0.1:  # Only show if progress is more than 10%
                self.ax.text(
                    0,  # The x-position of the single bar
                    done_weight / 2,  # Vertically centered in the green section
                    f'{done_percent:.1f}%',
                    ha='center',
                    va='center',
                    color='white',
                    weight='bold',
                    fontsize=12
                )

            # Add a label for the total weight *above* the entire bar
            self.ax.text(0, total_weight, f' Total: {total_weight:.1f} ', ha='center', va='bottom', fontsize=10)

            # --- AXIS AND TITLE SETUP ---
            self.ax.set_ylim(0, total_weight * 1.2)  # Give 20% headroom for the total label
            self.ax.set_ylabel("Weight")
            self.ax.set_title(f"Project Weight Progress: {project_name}", fontsize=14, weight='bold', pad=15)
            self.ax.legend()

            # Clean up the axes
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['top'].set_visible(False)
            self.current_chart_type = "Project Progress (Bar)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate bar chart for '{project_name}'.\nError: {e}")
            self.display_initial_message(f"Error displaying project progress: {e}")

        # Finally, draw the canvas
        self.canvas.draw()

    def show_line_progress_horizontal_bar(self):
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()
        self.ax.clear()

        try:
            report_registry = MIVRegistry(project_name)
            progress_data = report_registry.get_line_progress(line_no)

            percentage = progress_data.get("percentage", 0)
            total_qty = progress_data.get("total_qty", 0)

            if total_qty <= 0:
                self.display_initial_message(f"No data found for line '{line_no}'.")
                return

            # Ensure percentage is between 0 and 100
            percentage = max(0, min(100, percentage))

            # Draw bars
            self.ax.barh([0], [percentage], color='#28A745', height=0.6, label='Completed')
            self.ax.barh([0], [100 - percentage], left=[percentage], color='#D3D3D3', height=0.6, label='Remaining')

            # <--- FIX: New robust logic for placing the percentage text
            # This logic ensures the text is always visible and readable,
            # regardless of whether the percentage is low, medium, or high.
            if percentage >= 50:
                # If progress is high, place text inside the green bar (more space)
                position = percentage - 2
                alignment = 'right'
                color = 'white'
            else:
                # If progress is low, place text outside the green bar (in the grey area)
                position = percentage + 2
                alignment = 'left'
                color = 'black'

            if percentage > 0:  # Only show text if there is progress
                self.ax.text(position, 0, f"{percentage:.1f}%",
                             ha=alignment, va='center',
                             fontsize=12, color=color, weight='bold')

            self.ax.set_xlim(0, 100)
            self.ax.set_xticks([0, 25, 50, 75, 100])
            self.ax.set_xticklabels([f'{i}%' for i in [0, 25, 50, 75, 100]])
            self.ax.set_yticks([])
            self.ax.set_xlabel("Progress Percentage", fontsize=11)
            self.ax.set_title(f"Line Material Progress - Line {line_no}", fontsize=14, weight='bold', pad=15)

            self.ax.spines['right'].set_visible(False)
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['left'].set_visible(False)
            self.current_chart_type = "Line Progress (Horizontal Bar)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load line progress for '{line_no}'.\nError: {e}")
            self.display_initial_message(f"Error showing line progress: {e}")

        self.canvas.draw()

    def show_line_material_breakdown(self):
        project_name = self.project_var.get().strip()
        line_no = self.line_no_var.get().strip()
        self.ax.clear()

        try:
            report_registry = MIVRegistry(project_name)
            material_data = report_registry.get_line_material_breakdown(line_no)

            if not material_data:
                self.display_initial_message(f"No material data for line '{line_no}'.")
                return

            materials = list(material_data.keys())
            quantities = list(material_data.values())
            total_qty = sum(quantities)

            cmap = plt.get_cmap('viridis')
            colors = [cmap(i) for i in np.linspace(0, 1, len(materials))]

            bars = self.ax.bar(materials, quantities, color=colors)

            self.ax.set_ylabel("Quantity", fontsize=11)
            self.ax.set_title(f"Material Breakdown for Line {line_no}", fontsize=14, weight='bold', pad=20)

            for bar, qty in zip(bars, quantities):
                percent = (qty / total_qty) * 100 if total_qty > 0 else 0
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"{qty:.1f}\n({percent:.1f}%)",
                    ha='center',
                    va='bottom',
                    fontsize=8,
                    bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
                )

            self.fig.autofmt_xdate(rotation=45, ha='right')

            self.ax.spines['right'].set_visible(False)
            self.ax.spines['top'].set_visible(False)
            self.current_chart_type = "Line Material Breakdown (Bar)"

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate breakdown for line '{line_no}'.\nError: {e}")
            self.display_initial_message(f"Error generating breakdown: {e}")

        self.canvas.draw()

    def export_to_pdf(self):
        # A simple check for axes children.
        # This checks if there are any artists (bars, lines, etc.) drawn.
        if not self.ax.get_children():
            messagebox.showwarning("Warning", "No report has been generated to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
            title="Save Chart as PDF"
        )

        if not filepath:
            return

        try:
            self.fig.savefig(filepath, format='pdf', dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Chart successfully saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during PDF export.\nError: {e}")

    def show_line_material_progress(self):
        project = self.project_var.get()
        line_no = self.line_no_var.get()
        self.ax.clear()

        if not project or not line_no:
            self.display_initial_message("Please select a project and enter a line number.")
            return

        try:
            progress_df = self.registry.get_material_progress(project, line_no)

            if progress_df.empty:
                self.display_initial_message("No material progress data available for this line.")
                return

            progress_df.set_index('Item Code')[['Used Qty', 'Remaining Qty']].plot(
                kind='bar',
                stacked=True,
                ax=self.ax,
                color=['#1f77b4', '#aec7e8']
            )

            self.ax.set_ylabel("Quantity")
            self.ax.set_xlabel("Item Code")
            self.ax.set_title(f"Material Progress for Project '{project}', Line {line_no}")
            self.ax.legend(["Used", "Remaining"])

            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        except Exception as e:
            self.display_initial_message(f"Error loading data: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

        self.canvas.draw()