import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .config import RESOURCES_ROOT_DEFAULT, ROI_RIGHT_FRACTION, SCALES, MATCH_THRESHOLD
from .templates import scan_resources, load_resource_dir
from .screen import Screen
from .worker import Worker
from .debug import debug_snapshot

class App:
    def __init__(self, root):
        root.title("AutoGather — Multi Resource")
        self.monitor = tk.IntVar(value=1)
        self.want_gathering = tk.BooleanVar(value=True)
        self.resources_root = tk.StringVar(value=RESOURCES_ROOT_DEFAULT)
        self.status = tk.StringVar(value="Укажи папку resources и выбери ресурс.")
        self._resources = []         # [(name, path)]
        self._name_to_path = {}
        self._selected_name = tk.StringVar(value="")

        frm = ttk.Frame(root, padding=12); frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1); root.rowconfigure(0, weight=1)

        # Верхняя панель
        ttk.Label(frm, text="Папка resources:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.resources_root).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Обзор…", command=self.pick_root).grid(row=0, column=2, sticky="w")
        ttk.Button(frm, text="Обновить список", command=self.rescan).grid(row=0, column=3, sticky="w", padx=(6,0))

        ttk.Label(frm, text="Ресурс:").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.cmb = ttk.Combobox(frm, textvariable=self._selected_name, values=[], state="readonly", width=32)
        self.cmb.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6,0))

        ttk.Checkbutton(frm, text="Без стамины → жать только Gathering", variable=self.want_gathering) \
            .grid(row=2, column=0, columnspan=4, sticky="w", pady=(6,2))

        ttk.Label(frm, text="Монитор (mss index):").grid(row=3, column=0, sticky="w")
        tk.Spinbox(frm, from_=1, to=6, textvariable=self.monitor, width=6).grid(row=3, column=1, sticky="w", padx=6)

        self.btn_start = ttk.Button(frm, text="▶ Старт", command=self.start)
        self.btn_start.grid(row=4, column=0, sticky="ew", pady=(10,4))
        self.btn_stop  = ttk.Button(frm, text="■ Стоп", command=self.stop, state="disabled")
        self.btn_stop.grid(row=4, column=1, sticky="ew", pady=(10,4))
        ttk.Button(frm, text="Debug-снимок → debug_prompt.png", command=self.debug_snap) \
            .grid(row=4, column=2, columnspan=2, sticky="ew", pady=(10,4))

        ttk.Label(frm, textvariable=self.status, foreground="#666").grid(row=5, column=0, columnspan=4, sticky="w", pady=(8,0))
        for c in range(1,4):
            frm.columnconfigure(c, weight=1)

        self.screen = None; self.worker = None
        self.ts_f = self.ts_g = self.ts_s = None

        self.rescan()
        self._tick(root)

    def pick_root(self):
        d = filedialog.askdirectory(title="Выбери папку resources", initialdir=self.resources_root.get())
        if d:
            self.resources_root.set(d)
            self.rescan()

    def rescan(self):
        root_dir = self.resources_root.get().strip()
        self._resources = scan_resources(root_dir)
        self._name_to_path = {name: path for name, path in self._resources}
        names = [name for name, _ in self._resources]
        self.cmb["values"] = names
        if names:
            if self._selected_name.get() not in names:
                self._selected_name.set(names[0])
            self.status.set(f"Нашёл {len(names)} ресурс(а).")
        else:
            self._selected_name.set("")
            self.status.set("В корне нет валидных ресурсов (нужны focused/gathering/selector).")

    def start(self):
        if self.worker and self.worker.is_alive(): return
        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_path:
            messagebox.showerror("Нет ресурса", "Выбери ресурс из списка.")
            return
        resource_dir = self._name_to_path[name]
        try:
            from .templates import load_resource_dir
            self.ts_f, self.ts_g, self.ts_s = load_resource_dir(resource_dir)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return
        if not (self.ts_f.tmps and self.ts_g.tmps and self.ts_s.tmps):
            messagebox.showerror("Нет шаблонов", "В одной из подпапок нет изображений.")
            return

        self.screen = Screen(monitor_index=self.monitor.get())
        self.worker = Worker(self.screen, self.ts_f, self.ts_g, self.ts_s, self.want_gathering.get())
        self.worker.start()
        self.btn_start.configure(state="disabled"); self.btn_stop.configure(state="normal")
        self.status.set(f"Запущено: {name}. Перейди в игру (Borderless/Windowed).")

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.configure(state="normal"); self.btn_stop.configure(state="disabled")
        self.status.set("Остановлено.")

    def debug_snap(self):
        name = self._selected_name.get().strip()
        if not name or name not in self._name_to_path:
            messagebox.showerror("Нет ресурса", "Выбери ресурс из списка.")
            return
        resource_dir = self._name_to_path[name]
        try:
            ts_f, ts_g, ts_s = load_resource_dir(resource_dir)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e)); return

        sc = self.screen or Screen(monitor_index=self.monitor.get())
        frame = sc.grab_bgr()
        from .debug import debug_snapshot
        result = debug_snapshot(frame, ts_f, ts_g, ts_s, SCALES, MATCH_THRESHOLD, outfile="debug_prompt.png")
        ok_txt = " | ".join([f"{k}:{'ok' if v else '—'}" for k,v in result.items() if k != 'file'])
        messagebox.showinfo("Debug", f"{result['file']} сохранён. {ok_txt}")

    def _tick(self, root):
        if self.worker:
            self.status.set(f"Состояние: {self.worker.state}")
        root.after(150, lambda: self._tick(root))
