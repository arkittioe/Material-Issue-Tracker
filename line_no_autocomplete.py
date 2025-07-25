import tkinter as tk
from tkinter import ttk

class LineNoAutocompleteEntry(ttk.Entry):
    def __init__(self, master, registry, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.registry = registry
        self.listbox = None
        self.selected_index = None  # شاخص انتخاب‌شده واقعی

        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<FocusOut>", self.hide_listbox)
        self.bind("<Down>", self.focus_listbox)
        self.bind("<Return>", self.select_if_needed)

    def on_key_release(self, event=None):
        typed = self.get().strip()
        if not self.registry or len(typed) < 2:
            self.hide_listbox()
            return

        suggestions = self.registry.get_all_line_no_suggestions(typed)
        if suggestions:
            self.show_listbox(suggestions)
        else:
            self.hide_listbox()

    def show_listbox(self, suggestions):
        self.hide_listbox()

        self.listbox = tk.Listbox(
            self.winfo_toplevel(),
            height=min(6, len(suggestions)),
            bg="#fffff0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10)
        )

        for line_no, project in suggestions:
            display_text = f"{line_no} ({project})"
            self.listbox.insert(tk.END, display_text)

        for item in suggestions:
            self.listbox.insert(tk.END, item)

        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.listbox.bind("<Return>", self.select_if_needed)
        self.listbox.bind("<ButtonRelease-1>", self.on_mouse_click)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        self.listbox.place(x=x, y=y, width=w)

    def hide_listbox(self, event=None):
        if self.listbox and self.listbox.winfo_exists():
            self.listbox.destroy()
            self.listbox = None

    def on_listbox_select(self, event=None):
        if self.listbox:
            try:
                index = self.listbox.curselection()[0]
                selected_text = self.listbox.get(index)
                # جدا کردن line_no از project
                line_no = selected_text.split(" (")[0]
                self.selected_index = index
                self.delete(0, tk.END)
                self.insert(0, line_no)
                self.hide_listbox()
            except IndexError:
                pass

    def on_mouse_click(self, event):
        self.on_listbox_select()

    def focus_listbox(self, event):
        if self.listbox and self.listbox.size() > 0:
            self.listbox.focus()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def select_if_needed(self, event):
        if self.listbox and self.listbox.curselection():
            self.on_listbox_select()
            return "break"
