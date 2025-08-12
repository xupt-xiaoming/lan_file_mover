import socket
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import zipfile
import time # 用于模拟网络延迟
import shutil # 用于检查磁盘空间
import queue
import json

def get_preferred_local_ip():
    """获取本机局域网IP地址，优先192.168.x.x"""
    try:
        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        
        # 优先192.168.x.x
        for ip in ip_addresses:
            if ip.startswith('192.168.'):
                return ip
        
        # 然后是其他常见的私有IP范围 (10.x.x.x 和 172.16.x.x 到 172.31.x.x)
        for ip in ip_addresses:
            if ip.startswith('10.'):
                return ip
            if ip.startswith('172.'):
                parts = ip.split('.')
                if len(parts) > 1 and 16 <= int(parts[1]) <= 31:
                    return ip
        
        # 最后，返回第一个非回环地址
        for ip in ip_addresses:
            if ip != '127.0.0.1':
                return ip
        
        return '127.0.0.1' # 如果没有找到合适的IP，则返回回环地址
    except socket.gaierror:
        return '127.0.0.1'

class App(tk.Tk):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.title("局域网文件互传")
        self.geometry("550x750")
        self.resizable(True, True)

        # 设置样式
        style = ttk.Style(self)
        style.theme_use('clam') # 使用一个更现代的主题
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
        style.configure('Accent.TButton', foreground='white', background='#0078D7', font=('Helvetica', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#005bb5')])

        # 创建选项卡
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=15, padx=15, fill="both", expand=True)

        self.send_frame = SendFrame(self.notebook)
        self.receive_frame = ReceiveFrame(self.notebook)

        self.notebook.add(self.send_frame, text="  发送文件  ")
        self.notebook.add(self.receive_frame, text="  接收文件  ")

        # 绑定窗口关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _get_progress_file_path(self):
        return os.path.join(os.path.dirname(__file__), "transfer_progress.json")

    def _save_progress(self, file_name, total_size, transferred_size, is_sending):
        progress_data = {
            "file_name": file_name,
            "total_size": total_size,
            "transferred_size": transferred_size,
            "is_sending": is_sending
        }
        try:
            with open(self._get_progress_file_path(), 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"保存传输进度失败: {e}")

    def _load_progress(self):
        progress_file = self._get_progress_file_path()
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载传输进度失败: {e}")
                return None
        return None

    def _clear_progress(self):
        progress_file = self._get_progress_file_path()
        if os.path.exists(progress_file):
            try:
                os.remove(progress_file)
            except Exception as e:
                print(f"清除传输进度失败: {e}")

    def on_closing(self):
        # 保存IP地址到文件
        current_ip = self.send_frame.host_ip.get()
        if current_ip:
            try:
                with open("ip.txt", 'w') as f:
                    f.write(current_ip)
            except Exception as e:
                print(f"保存IP地址到ip.txt失败: {e}")
        self.destroy() # 关闭窗口

class SendFrame(ttk.Frame):
    """发送文件选项卡"""
    def __init__(self, container):
        super().__init__(container)
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.file_path = tk.StringVar()

        # --- 文件选择区域 ---
        file_frame = ttk.LabelFrame(self, text="第一步：选择文件", padding=(10, 10))
        file_frame.pack(fill="x", pady=10)

        ttk.Entry(file_frame, textvariable=self.file_path, state="readonly").pack(side="left", expand=True, fill="x", padx=(0, 10))
        ttk.Button(file_frame, text="浏览...", command=self.browse_file).pack(side="right")

        # --- IP地址输入区域 ---
        ip_frame = ttk.LabelFrame(self, text="第二步：输入接收方IP地址", padding=(10, 10))
        ip_frame.pack(fill="x", pady=10)
        
        self.host_ip = tk.StringVar()
        ip_file_path = "ip.txt"
        if os.path.exists(ip_file_path):
            try:
                with open(ip_file_path, 'r') as f:
                    default_ip = f.read().strip()
                    self.host_ip.set(default_ip)
            except Exception as e:
                print(f"读取ip.txt文件失败: {e}") # 可以在控制台打印错误，不影响GUI
        
        self.host_entry = ttk.Entry(ip_frame, textvariable=self.host_ip)
        self.host_entry.pack(expand=True, fill="x")

        # --- 发送文件按钮 ---
        self.send_file_button = ttk.Button(self, text="发送文件", command=self.start_send_file_thread, style='Accent.TButton')
        self.send_file_button.pack(pady=10, ipady=5)

        # --- 文件夹选择区域 ---
        folder_frame = ttk.LabelFrame(self, text="第三步：选择要发送的文件夹 (将压缩后发送)", padding=(10, 10))
        folder_frame.pack(fill="x", pady=10)

        self.folder_path = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_path, state="readonly").pack(side="left", expand=True, fill="x", padx=(0, 10))
        ttk.Button(folder_frame, text="浏览文件夹...", command=self.browse_folder).pack(side="right")

        # --- 发送文件夹按钮 ---
        self.send_folder_button = ttk.Button(self, text="发送文件夹", command=self.start_send_folder_thread, style='Accent.TButton')
        self.send_folder_button.pack(pady=10, ipady=5)

        # --- 进度显示区域 ---
        progress_container_frame = ttk.LabelFrame(self, text="传输进度", padding=(10, 10))
        progress_container_frame.pack(fill="x", pady=10, side="bottom")

        self.steps = [
            "初始化",
            "连接到接收方",
            "压缩文件夹 (如果适用)",
            "发送数据",
            "清理临时文件 (如果适用)",
            "完成"
        ]
        self.step_labels = []
        for i, step_text in enumerate(self.steps):
            label = ttk.Label(progress_container_frame, text=f"□ {step_text}")
            label.pack(anchor="w", padx=5, pady=2)
            self.step_labels.append(label)
        
        self.main_progress = ttk.Progressbar(progress_container_frame, orient="horizontal", mode="determinate")
        self.main_progress.pack(fill="x", expand=True, pady=5)
        
        self.overall_status_label = ttk.Label(progress_container_frame, text="请选择文件或文件夹并输入IP地址")
        self.overall_status_label.pack(pady=5)

        self.total_size_label = ttk.Label(progress_container_frame, text="总大小: N/A")
        self.total_size_label.pack(pady=2)

        self.speed_label = ttk.Label(progress_container_frame, text="速度: N/A")
        self.speed_label.pack(pady=2)

        self.current_step_index = -1
        self._reset_progress_ui()

    def _reset_progress_ui(self):
        for label in self.step_labels:
            label.config(text=f"□ {label.cget('text')[2:]}", foreground="black")
        self.main_progress["value"] = 0
        self.overall_status_label.config(text="请选择文件或文件夹并输入IP地址")
        self.total_size_label.config(text="总大小: N/A")
        self.speed_label.config(text="速度: N/A")
        self.current_step_index = -1

    def _format_bytes(self, bytes_value):
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024**2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024**3:
            return f"{bytes_value / (1024**2):.2f} MB"
        else:
            return f"{bytes_value / (1024**3):.2f} GB"

    

    def _update_step_status(self, step_index, status, message=""):
        if step_index < 0 or step_index >= len(self.steps):
            return

        # If a new step is becoming active, mark the previous active step as completed
        if status == "active" and self.current_step_index != -1:
            prev_label = self.step_labels[self.current_step_index]
            # Only mark as completed if it was active (not already failed/completed)
            if prev_label.cget('text').startswith("▶"):
                prev_label.config(text=f"✔ {prev_label.cget('text')[2:]}", foreground="green")

        current_label = self.step_labels[step_index]
        step_name = self.steps[step_index]

        if status == "active":
            current_label.config(text=f"▶ {step_name}", foreground="blue")
            self.overall_status_label.config(text=message if message else f"正在执行: {step_name}...")
            self.current_step_index = step_index
        elif status == "completed":
            current_label.config(text=f"✔ {step_name}", foreground="green")
            self.overall_status_label.config(text=message if message else f"{step_name} 完成。")
            self.current_step_index = -1 # No active step after completion
        elif status == "failed":
            current_label.config(text=f"✖ {step_name}", foreground="red")
            self.overall_status_label.config(text=message if message else f"{step_name} 失败！")
            self.current_step_index = -1 # No active step after failure
        
        self.update_idletasks()

    def _execute_with_retries(self, func, max_retries=8, delay=1, *args, **kwargs):
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries:
                    self.overall_status_label.config(text=f"操作失败，第 {attempt}/{max_retries} 次重试... ({e})")
                    self.update_idletasks()
                    time.sleep(delay)
                else:
                    raise # Re-raise the last exception if all retries fail

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path.set(file_path)

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)

    def compress_folder(self, folder_path):
        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", "选择的不是一个有效的文件夹。")
            return None

        zip_file_name = os.path.basename(folder_path) + ".zip"
        temp_zip_path = os.path.join(os.path.dirname(folder_path), zip_file_name) # 临时zip文件放在原文件夹的父目录

        self._update_step_status(2, "active", f"正在计算文件夹大小: {os.path.basename(folder_path)}...") # Step 2: 压缩文件夹
        self.update_idletasks()

        total_size = 0
        file_list = []
        file_count = 0
        self._update_step_status(2, "active", f"正在扫描文件夹并计算大小: {os.path.basename(folder_path)}...")
        self.update_idletasks()
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                        file_list.append(file_path)
                        file_count += 1
                        if file_count % 1000 == 0: # Update every 1000 files
                            self.overall_status_label.config(text=f"已扫描 {file_count} 个文件...")
                            self.update_idletasks()
        except Exception as e:
            self._update_step_status(2, "failed", f"计算文件夹大小时发生错误: {e}")
            messagebox.showerror("错误", f"计算文件夹大小时发生错误: {e}")
            return None
        
        if total_size == 0 and not file_list: # Handle empty folder case
            self._update_step_status(2, "completed", "文件夹为空，无需压缩。")
            return None

        # 检查磁盘空间
        zip_dir = os.path.dirname(temp_zip_path)
        if not os.path.exists(zip_dir):
            try:
                os.makedirs(zip_dir)
            except Exception as e:
                self._update_step_status(2, "failed", f"无法创建目标目录: {zip_dir} - {e}")
                messagebox.showerror("错误", f"无法创建目标目录: {zip_dir}\n{e}")
                return None

        try:
            total, used, free = shutil.disk_usage(zip_dir)
            if free < total_size:
                self._update_step_status(2, "failed", "磁盘空间不足，无法创建压缩文件。")
                messagebox.showerror("错误", f"磁盘空间不足！需要 {total_size / (1024**3):.2f} GB，但只有 {free / (1024**3):.2f} GB 可用。")
                return None
        except Exception as e:
            self._update_step_status(2, "failed", f"检查磁盘空间时发生错误: {e}")
            messagebox.showerror("错误", f"检查磁盘空间时发生错误: {e}")
            return None

        # 检查写入权限
        try:
            # 尝试创建一个临时文件来测试写入权限
            test_file_path = os.path.join(zip_dir, "temp_write_test.tmp")
            with open(test_file_path, "w") as f:
                f.write("test")
            os.remove(test_file_path)
        except Exception as e:
            self._update_step_status(2, "failed", f"没有写入权限: {zip_dir} - {e}")
            messagebox.showerror("错误", f"没有写入权限！请检查目录权限: {zip_dir}\n{e}")
            return None

        self._update_step_status(2, "active", f"正在压缩文件夹: {os.path.basename(folder_path)} (0%)")
        self.main_progress["value"] = 0
        self.update_idletasks()

        messagebox.showinfo("调试信息", f"即将创建临时压缩文件: {temp_zip_path}")
        print(f"DEBUG: Attempting to create zip file at: {temp_zip_path}")

        bytes_compressed = 0
        try:
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for i, file_path in enumerate(file_list):
                    arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                    zipf.write(file_path, arcname)
                    bytes_compressed += os.path.getsize(file_path)
                    if total_size > 0:
                        progress_percentage = (bytes_compressed / total_size) * 100
                        self.main_progress["value"] = progress_percentage
                        self.overall_status_label.config(text=f"压缩中: {os.path.basename(file_path)} ({int(progress_percentage)}%)")
                        self.update_idletasks()
            self._update_step_status(2, "completed", "文件夹压缩完成。")
            return temp_zip_path
        except Exception as e:
            self._update_step_status(2, "failed", f"压缩文件夹时发生错误: {e}")
            messagebox.showerror("压缩错误", f"压缩文件夹时发生错误: {e}")
            return None

    def start_send_file_thread(self):
        file_path = self.file_path.get()
        host = self.host_entry.get()
        if not file_path or not host:
            messagebox.showerror("错误", "请先选择文件，并输入接收方的IP地址。")
            return
        
        app_instance = self.master.master # Get the App instance
        progress = app_instance._load_progress()
        start_offset = 0
        if progress and progress["file_name"] == os.path.basename(file_path) and progress["is_sending"]:
            if messagebox.askyesno("断点续传", f"检测到上次未完成的传输：{progress['file_name']}，已传输 {self._format_bytes(progress['transferred_size'])} / {self._format_bytes(progress['total_size'])}。是否继续传输？"):
                start_offset = progress["transferred_size"]
            else:
                app_instance._clear_progress()

        self.send_file_button.config(state="disabled")
        self.send_folder_button.config(state="disabled")
        self._reset_progress_ui()
        self._update_step_status(0, "active", "正在初始化文件发送...") # Step 0: 初始化
        thread = threading.Thread(target=self.send_file, args=(file_path, host, 9999, start_offset))
        thread.daemon = True
        thread.start()

    def start_send_folder_thread(self):
        folder_path = self.folder_path.get()
        host = self.host_entry.get()
        if not folder_path or not host:
            messagebox.showerror("错误", "请先选择文件夹，并输入接收方的IP地址。")
            return
        
        app_instance = self.master.master # Get the App instance
        progress = app_instance._load_progress()
        start_offset = 0
        zip_file_name = os.path.basename(folder_path) + ".zip"
        temp_zip_path = os.path.join(os.path.dirname(folder_path), zip_file_name)

        if progress and progress["file_name"] == os.path.basename(temp_zip_path) and progress["is_sending"]:
            if messagebox.askyesno("断点续传", f"检测到上次未完成的传输：{progress['file_name']}，已传输 {self._format_bytes(progress['transferred_size'])} / {self._format_bytes(progress['total_size'])}。是否继续传输？"):
                start_offset = progress["transferred_size"]
            else:
                app_instance._clear_progress()

        self.send_file_button.config(state="disabled")
        self.send_folder_button.config(state="disabled")
        self._reset_progress_ui()
        self._update_step_status(0, "active", "正在初始化文件夹发送...") # Step 0: 初始化
        thread = threading.Thread(target=self._send_folder_action, args=(folder_path, host, 9999, start_offset))
        thread.daemon = True
        thread.start()

    def _send_folder_action(self, folder_path, host, port, start_offset=0):
        temp_zip_path = None
        try:
            temp_zip_path = self.compress_folder(folder_path)
            if temp_zip_path:
                self.send_file(temp_zip_path, host, port, start_offset)
                self._update_step_status(4, "active", "正在清理临时压缩文件...") # Step 4: 清理临时文件
        except Exception as e:
            self.overall_status_label.config(text=f"错误: {e}")
            messagebox.showerror("错误", f"发生错误: {e}")
        finally:
            if temp_zip_path and os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
                self._update_step_status(4, "completed", "临时压缩文件已清理。")
            else:
                self._update_step_status(4, "completed", "无需清理临时文件。")
            self._update_step_status(5, "completed", "所有操作完成！") # Step 5: 完成
            self.send_file_button.config(state="normal")
            self.send_folder_button.config(state="normal")
            self.main_progress["value"] = 0

    def send_file(self, file_path, host, port, start_offset=0):
        s = None
        CHUNK_SIZE = 64 * 1024  # 64KB
        SOCKET_BUFFER_SIZE = 64 * 1024 # 64KB
        UI_UPDATE_INTERVAL = 0.5 # seconds
        PROGRESS_SAVE_INTERVAL = 5 # seconds

        app_instance = self.master.master # Get the App instance

        try:
            self._update_step_status(1, "active", f"正在连接到 {host}...")
            self.main_progress["value"] = 0
            
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            self.total_size_label.config(text=f"总大小: {self._format_bytes(file_size)}")

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE) # Set send buffer size
            
            def connect_and_send_metadata():
                s.connect((host, port))
                self._update_step_status(1, "completed", "连接成功！")
                self.update_idletasks()
                
                self._update_step_status(3, "active", "正在发送文件信息...")
                # Send file_name, file_size, and start_offset to receiver
                s.sendall(f"{file_name}:{file_size}:{start_offset}\n".encode('utf-8'))
                s.recv(1024) # Wait for receiver confirmation

            self._execute_with_retries(connect_and_send_metadata, max_retries=8, delay=1)

            data_queue = queue.Queue(maxsize=10) # Queue for data chunks

            def file_reader_thread(q, path, chunk_size, offset):
                try:
                    with open(path, 'rb') as f:
                        f.seek(offset) # Seek to the start_offset
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            q.put(chunk)
                    q.put(None) # Sentinel to signal end of file
                except Exception as e:
                    print(f"File reader thread error: {e}")
                    # Handle error, potentially put an error signal in queue
                    q.put(None) # Ensure consumer doesn't hang

            reader_thread = threading.Thread(target=file_reader_thread, args=(data_queue, file_path, CHUNK_SIZE, start_offset))
            reader_thread.daemon = True
            reader_thread.start()

            sent_size = start_offset # Initialize sent_size with start_offset
            start_time = time.time()
            last_ui_update_time = time.time()
            last_progress_save_time = time.time()

            while True:
                chunk = data_queue.get()
                if chunk is None:
                    break # End of file
                
                s.sendall(chunk)
                sent_size += len(chunk)
                
                current_time = time.time()
                if current_time - last_ui_update_time > UI_UPDATE_INTERVAL:
                    elapsed_time = current_time - start_time
                    if elapsed_time > 0:
                        speed = sent_size / elapsed_time
                        self.speed_label.config(text=f"速度: {self._format_bytes(speed)}/s")

                    progress_percentage = (sent_size / file_size) * 100
                    self.main_progress["value"] = progress_percentage
                    self.overall_status_label.config(text=f"传输中... {int(progress_percentage)}%")
                    self.update_idletasks()
                    last_ui_update_time = current_time

                if current_time - last_progress_save_time > PROGRESS_SAVE_INTERVAL:
                    app_instance._save_progress(file_name, file_size, sent_size, True)
                    last_progress_save_time = current_time
            
            # Final UI update after loop finishes
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                speed = sent_size / elapsed_time
                self.speed_label.config(text=f"速度: {self._format_bytes(speed)}/s")
            self.main_progress["value"] = 100
            self.overall_status_label.config(text="传输中... 100%")
            self.update_idletasks()

            self._update_step_status(3, "completed", "文件发送成功！")
            messagebox.showinfo("成功", "文件已成功发送。")
            app_instance._clear_progress() # Clear progress after successful transfer

        except Exception as e:
            self._update_step_status(self.current_step_index, "failed", f"传输失败: {e}")
            messagebox.showerror("错误", f"发生错误: {e}")
            app_instance._save_progress(file_name, file_size, sent_size, True) # Save progress on error
        finally:
            if s:
                s.close()
            # The finally block here only handles errors within send_file.
            # _send_folder_action (external) handles button states and temporary file cleanup.
            pass

class ReceiveFrame(ttk.Frame):
    """接收文件选项卡"""
    def __init__(self, container):
        super().__init__(container)
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.save_path = tk.StringVar(value=os.getcwd())

        # --- IP地址显示区域 ---
        ip_frame = ttk.LabelFrame(self, text="第一步：将你的IP地址告诉发送方", padding=(10, 10))
        ip_frame.pack(fill="x", pady=10)
        
        ttk.Label(ip_frame, text=f"局域网IP地址: {get_preferred_local_ip()}", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=2)
        
        self.public_ip_label = ttk.Label(ip_frame, text="公网IP地址: 获取中...", font=("Helvetica", 10))
        self.public_ip_label.pack(anchor="w", pady=2)
        # 在单独的线程中获取公网IP，避免阻塞UI
        threading.Thread(target=self.update_public_ip_label, daemon=True).start()

        # --- 保存位置区域 ---
        path_frame = ttk.LabelFrame(self, text="第二步：选择文件保存位置", padding=(10, 10))
        path_frame.pack(fill="x", pady=10)
        
        ttk.Entry(path_frame, textvariable=self.save_path, state="readonly").pack(side="left", expand=True, fill="x", padx=(0, 10))
        ttk.Button(path_frame, text="更改目录...", command=self.change_directory).pack(side="right")

        # --- 接收按钮 ---
        self.receive_button = ttk.Button(self, text="开始接收", command=self.start_receive_thread, style='Accent.TButton')
        self.receive_button.pack(pady=20, ipady=5)

        # --- 进度显示区域 ---
        progress_container_frame = ttk.LabelFrame(self, text="接收进度", padding=(10, 10))
        progress_container_frame.pack(fill="x", pady=10, side="bottom")

        self.steps = [
            "等待连接",
            "接收文件信息",
            "接收数据",
            "解压文件 (如果适用)",
            "清理临时文件 (如果适用)",
            "完成"
        ]
        self.step_labels = []
        for i, step_text in enumerate(self.steps):
            label = ttk.Label(progress_container_frame, text=f"□ {step_text}")
            label.pack(anchor="w", padx=5, pady=2)
            self.step_labels.append(label)
        
        self.main_progress = ttk.Progressbar(progress_container_frame, orient="horizontal", mode="determinate")
        self.main_progress.pack(fill="x", expand=True, pady=5)
        
        self.overall_status_label = ttk.Label(progress_container_frame, text="等待对方连接...")
        self.overall_status_label.pack(pady=5)

        self.total_size_label = ttk.Label(progress_container_frame, text="总大小: N/A")
        self.total_size_label.pack(pady=2)

        self.speed_label = ttk.Label(progress_container_frame, text="速度: N/A")
        self.speed_label.pack(pady=2)

        self.current_step_index = -1
        self._reset_progress_ui()

    def _reset_progress_ui(self):
        for label in self.step_labels:
            label.config(text=f"□ {label.cget('text')[2:]}", foreground="black")
        self.main_progress["value"] = 0
        self.overall_status_label.config(text="等待对方连接...")
        self.total_size_label.config(text="总大小: N/A")
        self.speed_label.config(text="速度: N/A")
        self.current_step_index = -1

    def _format_bytes(self, bytes_value):
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024**2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024**3:
            return f"{bytes_value / (1024**2):.2f} MB"
        else:
            return f"{bytes_value / (1024**3):.2f} GB"

    

    def _update_step_status(self, step_index, status, message=""):
        if step_index < 0 or step_index >= len(self.steps):
            return

        # If a new step is becoming active, mark the previous active step as completed
        if status == "active" and self.current_step_index != -1:
            prev_label = self.step_labels[self.current_step_index]
            # Only mark as completed if it was active (not already failed/completed)
            if prev_label.cget('text').startswith("▶"):
                prev_label.config(text=f"✔ {prev_label.cget('text')[2:]}", foreground="green")

        current_label = self.step_labels[step_index]
        step_name = self.steps[step_index]

        if status == "active":
            current_label.config(text=f"▶ {step_name}", foreground="blue")
            self.overall_status_label.config(text=message if message else f"正在执行: {step_name}...")
            self.current_step_index = step_index
        elif status == "completed":
            current_label.config(text=f"✔ {step_name}", foreground="green")
            self.overall_status_label.config(text=message if message else f"{step_name} 完成。")
            self.current_step_index = -1 # No active step after completion
        elif status == "failed":
            current_label.config(text=f"✖ {step_name}", foreground="red")
            self.overall_status_label.config(text=message if message else f"{step_name} 失败！")
            self.current_step_index = -1 # No active step after failure
        
        self.update_idletasks()

    def update_public_ip_label(self):
        """在后台线程获取公网IP并更新UI"""
        try:
            # 注意：这里需要一个实际的HTTP请求来获取公网IP。
            # 由于本环境限制，无法直接执行HTTP请求，此处仅为示例。
            # 在实际应用中，你可以使用 requests 库或其他方式访问如 'https://icanhazip.com' 等服务。
            # 例如：
            # import requests
            # response = requests.get('https://icanhazip.com', timeout=5)
            # public_ip = response.text.strip()
            
            # 模拟网络请求延迟
            time.sleep(1)
            public_ip = "请连接互联网获取" # 替换为实际获取到的IP
            
            # 尝试通过web_fetch工具获取公网IP，但这仅在代理环境中有效
            # 如果用户在本地运行，需要自行实现HTTP请求
            # 示例：
            # from your_web_fetch_module import web_fetch_function
            # public_ip = web_fetch_function("https://icanhazip.com")

            self.public_ip_label.config(text=f"公网IP地址: {public_ip}")
        except Exception as e:
            self.public_ip_label.config(text=f"公网IP地址: 获取失败 ({e})")

    def change_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path.set(path)

    def start_receive_thread(self):
        app_instance = self.master.master # Get the App instance
        progress = app_instance._load_progress()
        start_offset = 0
        if progress and not progress["is_sending"]:
            if messagebox.askyesno("断点续传", f"检测到上次未完成的接收：{progress['file_name']}，已接收 {self._format_bytes(progress['transferred_size'])} / {self._format_bytes(progress['total_size'])}。是否继续接收？"):
                start_offset = progress["transferred_size"]
            else:
                app_instance._clear_progress()

        self.receive_button.config(state="disabled")
        self._reset_progress_ui()
        self._update_step_status(0, "active", "正在等待连接...") # Step 0: 等待连接
        thread = threading.Thread(target=self.receive_file, args=(9999, start_offset)) 
        thread.daemon = True
        thread.start()

    def receive_file(self, port, start_offset=0):
        file_save_path = None
        s = None
        conn = None
        CHUNK_SIZE = 64 * 1024  # 64KB
        SOCKET_BUFFER_SIZE = 64 * 1024 # 64KB
        UI_UPDATE_INTERVAL = 0.5 # seconds
        PROGRESS_SAVE_INTERVAL = 5 # seconds

        app_instance = self.master.master # Get the App instance

        try:
            host = '0.0.0.0'
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE) # Set receive buffer size
            s.bind((host, port))
            s.listen()
            
            self._update_step_status(0, "active", "正在等待连接...")
            conn, addr = s.accept()
            self._update_step_status(0, "completed", f"已连接: {addr[0]}:{addr[1]}")
            
            with conn:
                self._update_step_status(1, "active", "正在接收文件信息...")
                # Receive file_name, file_size, and start_offset from sender
                received_metadata = conn.recv(1024).decode('utf-8').strip()
                file_name, file_size_str, sender_start_offset_str = received_metadata.split(':', 2)
                file_size = int(file_size_str)
                sender_start_offset = int(sender_start_offset_str)

                # If sender is resuming, ensure our start_offset matches sender's
                if start_offset != sender_start_offset:
                    messagebox.showwarning("断点续传不匹配", f"发送方从 {self._format_bytes(sender_start_offset)} 开始，而本地记录从 {self._format_bytes(start_offset)} 开始。将从发送方指定的位置开始。")
                    start_offset = sender_start_offset

                self.total_size_label.config(text=f"总大小: {self._format_bytes(file_size)}")

                conn.sendall(b'OK')
                self._update_step_status(1, "completed", "文件信息接收成功！")

                file_save_path = os.path.join(self.save_path.get(), file_name)
                
                data_queue = queue.Queue(maxsize=10) # Queue for data chunks
                received_size = start_offset # Initialize received_size with start_offset
                start_time = time.time()
                last_ui_update_time = time.time()
                last_progress_save_time = time.time()

                def socket_receiver_thread(q, connection, total_size, offset):
                    nonlocal received_size
                    try:
                        # No need to seek on socket, just start receiving
                        while received_size < total_size:
                            bytes_read = connection.recv(CHUNK_SIZE)
                            if not bytes_read:
                                break
                            q.put(bytes_read)
                            received_size += len(bytes_read)
                        q.put(None) # Sentinel to signal end of data
                    except Exception as e:
                        print(f"Socket receiver thread error: {e}")
                        q.put(None) # Ensure consumer doesn't hang

                def file_writer_thread(q, path, offset):
                    try:
                        with open(path, 'ab' if offset > 0 else 'wb') as f: # Use 'ab' for append if resuming
                            f.seek(offset) # Seek to the start_offset for writing
                            while True:
                                chunk = q.get()
                                if chunk is None:
                                    break
                                f.write(chunk)
                    except Exception as e:
                        print(f"File writer thread error: {e}")

                receiver_thread = threading.Thread(target=socket_receiver_thread, args=(data_queue, conn, file_size, start_offset))
                receiver_thread.daemon = True
                receiver_thread.start()

                writer_thread = threading.Thread(target=file_writer_thread, args=(data_queue, file_save_path, start_offset))
                writer_thread.daemon = True
                writer_thread.start()

                # Main thread for UI updates
                self._update_step_status(2, "active", f"正在接收数据: {file_name} ({int((received_size / file_size) * 100) if file_size > 0 else 0}%)")
                while receiver_thread.is_alive() or not data_queue.empty():
                    current_time = time.time()
                    if current_time - last_ui_update_time > UI_UPDATE_INTERVAL:
                        elapsed_time = current_time - start_time
                        if elapsed_time > 0:
                            speed = received_size / elapsed_time
                            self.speed_label.config(text=f"速度: {self._format_bytes(speed)}/s")

                        progress_percentage = (received_size / file_size) * 100 if file_size > 0 else 0
                        self.main_progress["value"] = progress_percentage
                        self.overall_status_label.config(text=f"接收中... {int(progress_percentage)}%")
                        self.update_idletasks()
                        last_ui_update_time = current_time

                    if current_time - last_progress_save_time > PROGRESS_SAVE_INTERVAL:
                        app_instance._save_progress(file_name, file_size, received_size, False)
                        last_progress_save_time = current_time

                    time.sleep(0.01) # Small sleep to prevent busy-waiting
                
                writer_thread.join() # Ensure all data is written

            # Final UI update after loop finishes
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                speed = received_size / elapsed_time
                self.speed_label.config(text=f"速度: {self._format_bytes(speed)}/s")
            self.main_progress["value"] = 100
            self.overall_status_label.config(text="接收中... 100%")
            self.update_idletasks()

            self._update_step_status(2, "completed", "文件接收成功！")
            messagebox.showinfo("成功", f"文件已成功接收并保存到:\n{file_save_path}")
            app_instance._clear_progress() # Clear progress after successful transfer

            # 检查是否为zip文件并解压
            if file_name.lower().endswith('.zip'):
                self._update_step_status(3, "active", "正在解压文件...")
                self.update_idletasks()
                try:
                    extract_path = os.path.splitext(file_save_path)[0]
                    os.makedirs(extract_path, exist_ok=True)
                    with zipfile.ZipFile(file_save_path, 'r') as zip_ref:
                        total_extracted_size = sum(file.file_size for file in zip_ref.infolist())
                        extracted_size = 0
                        last_unzip_ui_update_time = time.time()
                        for file_info in zip_ref.infolist():
                            extracted_file_path = os.path.join(extract_path, file_info.filename)
                            if not os.path.exists(os.path.dirname(extracted_file_path)):
                                os.makedirs(os.path.dirname(extracted_file_path), exist_ok=True)
                            with zip_ref.open(file_info.filename) as infile:
                                with open(extracted_file_path, "wb") as outfile:
                                    while True:
                                        chunk = infile.read(CHUNK_SIZE)
                                        if not chunk:
                                            break
                                        outfile.write(chunk)
                                        extracted_size += len(chunk)
                                        current_time = time.time()
                                        if current_time - last_unzip_ui_update_time > UI_UPDATE_INTERVAL:
                                            if total_extracted_size > 0:
                                                progress_percentage = (extracted_size / total_extracted_size) * 100
                                                self.main_progress["value"] = progress_percentage
                                                self.overall_status_label.config(text=f"解压中... {int(progress_percentage)}%")
                                                self.update_idletasks()
                                            last_unzip_ui_update_time = current_time

                    self._update_step_status(3, "completed", "文件解压成功！")
                    messagebox.showinfo("成功", f"文件已成功解压到:\n{extract_path}")
                    
                    self._update_step_status(4, "active", "正在清理临时zip文件...")
                    os.remove(file_save_path)
                    self._update_step_status(4, "completed", "临时zip文件已清理。")
                except Exception as unzip_e:
                    self._update_step_status(3, "failed", f"解压错误: {unzip_e}")
                    messagebox.showerror("解压错误", f"解压文件时发生错误: {unzip_e}")

            self._update_step_status(5, "completed", "所有操作完成！")

        except Exception as e:
            self._update_step_status(self.current_step_index, "failed", f"接收失败: {e}")
            messagebox.showerror("错误", f"发生错误: {e}")
            app_instance._save_progress(file_name, file_size, received_size, False) # Save progress on error
        finally:
            if conn:
                conn.close()
            if s:
                s.close()
            self.receive_button.config(state="normal")
            self.main_progress["value"] = 0
            self.overall_status_label.config(text="等待对方连接...")

if __name__ == "__main__":
    app = App()
    app.mainloop()
