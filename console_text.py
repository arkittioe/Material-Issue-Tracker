import tkinter as tk
from tkinter import messagebox
import pandas as pd
from miv_registry import MIVRegistry

class ConsoleText(tk.Text):
    def __init__(self, master=None, app=None, **kwargs):
        super().__init__(master, **kwargs)

        # اتصال به برنامه اصلی و Registry
        self.app = app

        # تنظیمات ظاهری کنسول دارک
        self.configure(
            bg="#2b2b2b",      # پس‌زمینه تیره مشابه PyCharm
            fg="#ffffff",      # رنگ متن سفید
            insertbackground="#ffffff",  # رنگ کرسر متن
            font=("Consolas", 11),
            undo=True,
            wrap="word"
        )

        # تعریف رنگ‌ها و تگ‌ها برای پیام‌ها
        self.tag_config("error", foreground="#ff5555")
        self.tag_config("success", foreground="#50fa7b")
        self.tag_config("info", foreground="#8be9fd")
        self.tag_config("command", foreground="#f1fa8c")
        self.tag_config("output", foreground="#f8f8f2")

        self.bind("<Return>", self.on_enter_pressed)
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<Up>", self.on_history_up)
        self.bind("<Down>", self.on_history_down)

        self.bind("<Control-c>", self.copy_selection)
        self.bind("<Button-3>", self.show_context_menu)  # راست کلیک (اختیاری)

        self.insert(tk.END, "> ", "command")
        self.mark_set("insert", tk.END)
        self.input_start_index = self.index(tk.INSERT)

        self.command_history = []
        self.history_index = -1

    def copy_selection(self, event=None):
        try:
            selected_text = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass  # اگر چیزی انتخاب نشده باشه، کاری نکن

    def show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="کپی", command=self.copy_selection)
        menu.tk_popup(event.x_root, event.y_root)

    def on_enter_pressed(self, event):
        command = self.get(self.input_start_index, tk.END).strip()
        if command:
            self.write_output(f"> {command}", "command")
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            self.process_command(command)
        else:
            self.insert(tk.END, "\n> ", "command")

        self.mark_set("insert", tk.END)
        self.input_start_index = self.index(tk.INSERT)
        self.see(tk.END)
        return "break"

    def on_key_press(self, event):
        # جلوگیری از حذف پرامپت یا رفتن به بالای خط ورودی
        if self.compare(self.index(tk.INSERT), "<", self.input_start_index):
            return "break"

    def on_history_up(self, event):
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.replace_current_input(self.command_history[self.history_index])
        return "break"

    def on_history_down(self, event):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.replace_current_input(self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.replace_current_input("")
        return "break"

    def replace_current_input(self, text):
        self.delete(self.input_start_index, tk.END)
        self.insert(tk.END, text)
        self.mark_set("insert", tk.END)

    def write_output(self, message, tag="output"):
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)
        self.update_idletasks()

    def process_command(self, command):
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        try:
            if cmd == "clear":
                self.clear_console()

            elif cmd == "help":
                self.app.show_help_window()

            elif cmd == "exit":
                self.write_output("👋 خروج از برنامه...", "info")
                self.app.destroy()

            elif cmd == "register":
                self.app.register_record()


            elif cmd == "edit":

                if len(parts) >= 4 and parts[2].lower() == "in":

                    line_no = parts[1]

                    project = parts[3].upper()

                    self.app.show_edit_window(line_no, project)

                else:

                    self.write_output("❌ فرمت دستور edit اشتباه است.", "error")



            elif cmd == "delete":

                # delete [line_no] in [project]

                if len(parts) >= 4 and parts[2].lower() == "in":

                    line_no = parts[1]

                    project = parts[3].upper()

                    self.app.show_delete_window(line_no, project)

                else:

                    self.write_output("❌ فرمت دستور delete اشتباه است.", "error")


            elif cmd == "search":
                # search [keyword] in [project]
                if len(parts) >= 4 and parts[-2].lower() == "in":
                    keyword = " ".join(parts[1:-2])
                    project = parts[-1].upper()
                    self.search_keyword_in_project(keyword, project)

                # search tag [miv_tag] in [project]
                elif len(parts) >= 5 and parts[1].lower() == "tag" and parts[-2].lower() == "in":
                    miv_tag = parts[2]
                    project = parts[-1].upper()
                    self.search_tag_in_project(miv_tag, project)

                else:
                    self.write_output("❌ فرمت دستور search اشتباه است.", "error")


            elif cmd == "filter":

                try:

                    # 👇 ساختار: filter miv project P01 by Status Done and Location Unit12

                    data_type = parts[1].lower()  # فقط miv فعلاً

                    if data_type != "miv":
                        self.write_output("❌ فقط فیلتر روی 'miv' پشتیبانی می‌شود.", "error")

                        return

                    project = None

                    filters = {}

                    # پیدا کردن project (اگر هست)

                    if "project" in parts:

                        proj_index = parts.index("project")

                        if proj_index + 1 < len(parts):
                            project = parts[proj_index + 1].upper()

                    # پیدا کردن بخش فیلترها

                    if "by" in parts:

                        by_index = parts.index("by")

                        filter_parts = parts[by_index + 1:]

                        current_key = None

                        current_val = []

                        for part in filter_parts:

                            if part.lower() == "and":

                                if current_key and current_val:
                                    filters[current_key] = " ".join(current_val)

                                current_key = None

                                current_val = []

                            elif current_key is None:

                                current_key = part

                            else:

                                current_val.append(part)

                        if current_key and current_val:
                            filters[current_key] = " ".join(current_val)

                    # ✅ نمایش جدول با فیلتر

                    if project:

                        self.app.show_table_viewer(

                            mode="custom_filter",

                            project=project,

                            filters=filters

                        )

                    else:

                        self.write_output("❌ لطفاً پروژه را مشخص کنید: project <code>", "error")


                except Exception as e:

                    self.write_output(f"❌ خطا در اجرای دستور filter: {e}", "error")


            elif cmd == "show":

                if len(parts) >= 2:

                    subcmd = parts[1].lower()

                    # ⬇️ نمایش آخرین n خط از MIV برای پروژه خاص

                    if subcmd == "last" and len(parts) >= 6 and parts[3].lower() == "miv" and parts[4].lower() == "for":

                        try:

                            n = int(parts[2])

                            project = parts[5].upper()

                            self.app.show_table_viewer(mode="last", project=project, last_n=n)

                        except ValueError:

                            self.write_output("❌ تعداد n باید عدد صحیح باشد.", "error")


                    # ⬇️ نمایش رکوردهای MIV برای یک شماره خط خاص در یک پروژه

                    elif subcmd == "miv" and len(parts) >= 5 and parts[3].lower() == "for":

                        line_no = parts[2]

                        project = parts[4].upper()

                        self.app.show_table_viewer(mode="miv", project=project, line_no=line_no)


                    # ⬇️ نمایش تمام رکوردهای MIV یک پروژه

                    elif subcmd == "all" and len(parts) >= 4 and parts[2].lower() == "miv" and parts[
                        3].lower() == "for":

                        project = parts[4].upper()

                        self.app.show_table_viewer(mode="all", project=project)


                    # ⬇️ نمایش فقط رکوردهای کامل‌شده MIV برای یک پروژه

                    elif subcmd == "complete" and len(parts) >= 4 and parts[2].lower() == "miv" and parts[
                        3].lower() == "for":

                        project = parts[4].upper()

                        self.app.show_table_viewer(mode="complete", project=project)


                    # ⬇️ نمایش رکوردهای ناقص MIV

                    elif subcmd == "incomplete" and len(parts) >= 4 and parts[2].lower() == "miv" and parts[
                        3].lower() == "for":

                        project = parts[4].upper()

                        self.app.show_table_viewer(mode="incomplete", project=project)


                    # ⬇️ نمایش MTO برای یک شماره خط خاص

                    elif subcmd == "mto" and len(parts) >= 5 and parts[2].lower() == "for":

                        line_no = parts[3]

                        project = parts[4].upper()

                        self.app.show_table_viewer(mode="mto", project=project, line_no=line_no)


                    else:

                        self.write_output("❌ دستور show نامعتبر یا ناقص است.", "error")


                else:

                    self.write_output("❌ دستور show ناقص است.", "error")


            elif cmd == "list":
                # list projects
                if len(parts) == 2 and parts[1].lower() == "projects":
                    self.list_projects()
                else:
                    self.write_output("❌ فرمت دستور list اشتباه است.", "error")

            elif cmd == "backup":
                # backup project [project_code]
                if len(parts) == 3 and parts[1].lower() == "project":
                    project_code = parts[2].upper()
                    self.backup_project(project_code)
                else:
                    self.write_output("❌ فرمت دستور backup اشتباه است.", "error")

            elif cmd == "validate":
                # validate project [project_code]
                if len(parts) == 3 and parts[1].lower() == "project":
                    project_code = parts[2].upper()
                    self.validate_project(project_code)
                else:
                    self.write_output("❌ فرمت دستور validate اشتباه است.", "error")

            elif cmd == "check":
                # check duplicates in [project]
                if len(parts) == 4 and parts[1].lower() == "duplicates" and parts[2].lower() == "in":
                    project = parts[3].upper()
                    self.check_duplicates(project)
                else:
                    self.write_output("❌ فرمت دستور check اشتباه است.", "error")

            elif cmd == "set":
                # set current project [project_code]
                if len(parts) == 4 and parts[1].lower() == "current" and parts[2].lower() == "project":
                    project_code = parts[3].upper()
                    self.set_current_project(project_code)
                else:
                    self.write_output("❌ فرمت دستور set اشتباه است.", "error")

            elif cmd == "export":
                # export project [project_code] to excel
                # export miv for [line_no] in [project]
                if len(parts) >= 3:
                    if parts[1].lower() == "project" and parts[-2].lower() == "to" and parts[-1].lower() == "excel":
                        project_code = parts[2].upper()
                        self.export_project_to_excel(project_code)
                    elif parts[1].lower() == "miv" and parts[2].lower() == "for" and len(parts) >= 6 and parts[-2].lower() == "in":
                        line_no = parts[3]
                        project = parts[5].upper()
                        self.export_miv_for_line(line_no, project)
                    else:
                        self.write_output("❌ فرمت دستور export اشتباه است.", "error")
                else:
                    self.write_output("❌ فرمت دستور export ناقص است.", "error")

            elif cmd == "log":
                # log commands
                if len(parts) == 2 and parts[1].lower() == "commands":
                    self.show_command_history()
                else:
                    self.write_output("❌ فرمت دستور log اشتباه است.", "error")

            elif cmd == "show":
                # برخی دستورات show در بالا مدیریت شده‌اند، اگر اینجا هم باشد به خطا می‌خورد،
                # اگر لازم بود می‌توان توسعه داد.
                pass



            else:
                self.write_output(f"❌ دستور نامعتبر: {command}", "error")

        except Exception as e:
            self.write_output(f"❌ خطا در اجرای دستور: {e}", "error")

    def clear_console(self):
        self.delete("1.0", tk.END)
        self.insert(tk.END, "> ", "command")
        self.mark_set("insert", tk.END)
        self.input_start_index = self.index(tk.INSERT)

    # نمونه پیاده‌سازی چند دستور مهم؛ بقیه را بر اساس همین نمونه کامل کن

    def compare_mto_and_miv(self, line_no, project):
        try:
            if not self.app.registry or self.app.registry.current_project != project:
                self.app.registry = MIVRegistry(project)
            mto_items = self.app.registry.get_mto_items(line_no)
            miv_records, _, complete = self.app.registry.search_record(line_no)
            if mto_items.empty and miv_records.empty:
                self.write_output(f"❌ هیچ رکوردی برای خط {line_no} در پروژه {project} یافت نشد.", "error")
                return
            self.write_output(f"🔎 مقایسه MTO و MIV برای خط {line_no} در پروژه {project}:", "info")
            self.write_output("MTO:\n" + (mto_items.to_string(index=False) if not mto_items.empty else "خالی"))
            self.write_output("MIV:\n" + (miv_records.to_string(index=False) if not miv_records.empty else "خالی"))
            self.write_output("✅ خط کامل شده است." if complete else "⚠️ خط ناقص است.")
        except Exception as e:
            self.write_output(f"❌ خطا در مقایسه: {e}", "error")

    def search_keyword_in_project(self, keyword, project):
        try:
            registry = MIVRegistry(project)
            df = registry.read_project_df()
            if df.empty:
                self.write_output(f"📭 پروژه {project} رکوردی ندارد.", "info")
                return
            mask = df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)
            result = df[mask]
            if result.empty:
                self.write_output(f"❌ هیچ رکوردی با کلمه '{keyword}' در پروژه {project} یافت نشد.", "error")
            else:
                self.write_output(f"🔍 نتایج جستجو برای '{keyword}' در پروژه {project}:", "info")
                self.write_output(result.to_string(index=False))
        except Exception as e:
            self.write_output(f"❌ خطا در جستجو: {e}", "error")

    def search_tag_in_project(self, miv_tag, project):
        try:
            registry = MIVRegistry(project)
            df = registry.read_project_df()
            if df.empty:
                self.write_output(f"📭 پروژه {project} رکوردی ندارد.", "info")
                return
            result = df[df["MIV Tag"].astype(str).str.lower() == miv_tag.lower()]
            if result.empty:
                self.write_output(f"❌ هیچ رکوردی با MIV Tag '{miv_tag}' در پروژه {project} یافت نشد.", "error")
            else:
                self.write_output(f"🔍 نتایج جستجو برای MIV Tag '{miv_tag}' در پروژه {project}:", "info")
                self.write_output(result.to_string(index=False))
        except Exception as e:
            self.write_output(f"❌ خطا در جستجو: {e}", "error")

    def list_projects(self):
        try:
            projects = self.app.registry.list_projects()
            if not projects:
                self.write_output("📭 هیچ پروژه‌ای وجود ندارد.", "info")
                return
            self.write_output("📋 لیست پروژه‌ها:", "info")
            for p in projects:
                self.write_output(f"  • {p}", "info")
        except Exception as e:
            self.write_output(f"❌ خطا در دریافت لیست پروژه‌ها: {e}", "error")

    def set_current_project(self, project_code):
        try:
            self.app.registry = MIVRegistry(project_code)
            self.write_output(f"✅ پروژه جاری به {project_code} تغییر یافت.", "success")
        except Exception as e:
            self.write_output(f"❌ خطا در تغییر پروژه جاری: {e}", "error")

    def show_command_history(self):
        self.write_output("📜 تاریخچه دستورات:", "info")
        if not self.command_history:
            self.write_output(" (هیچ دستوری اجرا نشده)", "info")
            return
        for i, cmd in enumerate(self.command_history, 1):
            self.write_output(f" {i}: {cmd}", "info")

    def backup_project(self, project_code):
        try:
            # اگر پروژه جاری نیست یا پروژه جدید خواسته شده، نمونه جدید بساز
            if not self.app.registry or (project_code and self.app.registry.project != project_code.upper()):
                self.app.registry = MIVRegistry(
                    project_code if project_code != "all" else "")  # "" چون برای بک‌آپ همه پروژه‌ها پروژه نمیخواد

            success, msg = self.app.registry.backup_project(project_code)
            tag = "success" if success else "error"
            self.write_output(msg, tag)
        except Exception as e:
            self.write_output(f"❌ خطا در بک‌آپ‌گیری: {e}", "error")
