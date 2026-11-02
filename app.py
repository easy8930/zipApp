"""ZIP App: Windows desktop interface using Python's standard library."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from archive_core import compress, extract


class App:
    def __init__(self, root):
        self.root = root
        self.paths = []
        self.events = queue.Queue()
        root.title('ZIP App — 圧縮・解凍')
        root.geometry('680x510')
        root.minsize(560, 440)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='ZIP App', font=('Yu Gothic UI', 24, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='ファイルを端末内で圧縮・解凍します。外部への送信はありません。').pack(anchor='w', pady=(4, 18))
        self.buttons = []
        bar = ttk.Frame(frame)
        bar.pack(fill='x')
        self.button(bar, 'ファイルを追加', self.add_files)
        self.button(bar, 'フォルダーを追加', self.add_folder)
        self.button(bar, '選択をクリア', self.clear)
        self.listbox = tk.Listbox(frame, height=10, selectmode='extended')
        self.listbox.pack(fill='both', expand=True, pady=12)
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        self.button(actions, '選択した項目を ZIP に圧縮', self.zip)
        self.button(actions, 'ZIP を選んで解凍', self.unzip)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=(18, 8))
        self.status = tk.StringVar(value='ファイルやフォルダーを追加するか、ZIP を選んで解凍してください。')
        ttk.Label(frame, textvariable=self.status, wraplength=590).pack(anchor='w')
        self.busy = False
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)

    def button(self, parent, label, action):
        button = ttk.Button(parent, text=label, command=action)
        button.pack(side='left', padx=(0, 8))
        self.buttons.append(button)

    def add(self, paths):
        for path in paths:
            if path not in self.paths:
                self.paths.append(path)
                self.listbox.insert('end', path)

    def add_files(self):
        self.add(filedialog.askopenfilenames(title='圧縮するファイルを選択'))

    def add_folder(self):
        folder = filedialog.askdirectory(title='圧縮するフォルダーを選択')
        if folder:
            self.add([folder])

    def clear(self):
        self.paths.clear()
        self.listbox.delete(0, 'end')

    def zip(self):
        if not self.paths:
            messagebox.showinfo('項目を選択', 'ファイルまたはフォルダーを追加してください。')
            return
        target = filedialog.asksaveasfilename(title='ZIP の保存先', defaultextension='.zip', filetypes=[('ZIP', '*.zip')])
        if target:
            self.run(lambda: compress(list(self.paths), target), '圧縮', target)

    def unzip(self):
        source = filedialog.askopenfilename(title='解凍する ZIP を選択', filetypes=[('ZIP', '*.zip')])
        if not source:
            return
        parent = filedialog.askdirectory(title='解凍先の親フォルダーを選択')
        if parent:
            target = Path(parent) / Path(source).stem
            self.run(lambda: extract(source, target), '解凍', str(target))

    def run(self, action, label, target):
        self.busy = True
        for button in self.buttons:
            button.state(['disabled'])
        self.progress.start()
        self.status.set(label + '中です…')
        def worker():
            try:
                action()
                self.events.put((True, label + 'が完了しました。\n' + target))
            except Exception as error:
                self.events.put((False, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            ok, text = self.events.get_nowait()
            self.busy = False
            self.progress.stop()
            for button in self.buttons:
                button.state(['!disabled'])
            self.status.set(text if ok else '処理できませんでした。保存先や ZIP を確認してください。')
            (messagebox.showinfo if ok else messagebox.showerror)('完了' if ok else 'エラー', text)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('処理中', '処理が完了してから閉じてください。')
        else:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
