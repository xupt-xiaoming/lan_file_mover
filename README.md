[English](README.md) | [中文](README_zh.md)

---

# LAN-Sender (Local Area Network File Transfer Tool)

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg) ![Status](https://img.shields.io/badge/status-active-brightgreen)

A simple, fast, and reliable local area network file transfer tool with a graphical user interface, built with Python and Tkinter. No external dependencies required.

---

### Screenshot

*Your application's screenshot goes here. It can greatly attract users.*

![App Screenshot](./screenshot.png) 
*(Please replace `screenshot.png` with your own screenshot file name)*

---

### ✨ Features

*   **💻 Cross-Platform GUI:** Built with Python's standard Tkinter library, it runs on Windows, macOS, and Linux without any changes.
*   **📂 File and Folder Support:** Easily send individual files or entire folders. Folders are automatically compressed into a zip file for transfer and unzipped upon reception.
*   **🔄 Resumable Transfers:** If a transfer is interrupted, it can be resumed from where it left off, saving time and bandwidth.
*   **🚀 High Performance:** Utilizes multi-threading for non-blocking UI and efficient socket communication for fast data transfer.
*   **📊 Detailed Progress Tracking:** Real-time display of transfer speed, percentage, total size, and detailed steps (connecting, compressing, sending, etc.).
*   **💡 Zero Dependencies:** Requires only a standard Python 3 installation. No need to `pip install` anything.
*   **🌐 Smart IP Detection:** Automatically detects and suggests the primary local IP address (e.g., `192.168.x.x`).

---

### 🚀 Getting Started

Since this tool has no external dependencies, getting started is extremely simple.

1.  **Ensure Python is installed.** You need Python 3.7 or newer.
2.  **Download the Code.**
    ```bash
    git clone https://github.com/your-username/lan-sender.git 
    cd lan-sender
    ```
    (Or simply download the `.py` file.)
3.  **Run the application.**
    ```bash
    python main.py
    ```
    *(Assuming you have named the script `main.py`)*

---

### 📖 How to Use

The application has two main tabs: "Send" and "Receive".

#### To Send a File or Folder

1.  Go to the **"Send"** tab.
2.  **To send a file:** Click "Browse..." in the "Select File" section.
3.  **To send a folder:** Click "Browse Folder..." in the "Select Folder" section.
4.  Enter the receiver's IP address in the "Receiver's IP Address" field. This IP is displayed on the receiver's application window.
5.  Click the corresponding **"Send File"** or **"Send Folder"** button.
6.  The progress will be displayed at the bottom.

#### To Receive a File

1.  Go to the **"Receive"** tab.
2.  Tell the sender your IP address, which is displayed at the top of the window (e.g., `Local IP: 192.168.1.5`).
3.  (Optional) Choose a different directory to save the incoming file by clicking "Change Directory...". By default, files are saved in the current directory.
4.  Click the **"Start Receiving"** button. The application will now wait for an incoming connection.
5.  Once the transfer is complete, if it was a folder, it will be automatically unzipped.

---

### 🛠️ Technical Details

*   **GUI:** `tkinter` and `tkinter.ttk` for the graphical interface.
*   **Networking:** `socket` module for low-level TCP/IP communication.
*   **Concurrency:** `threading` module to keep the GUI responsive during I/O-bound tasks like file transfer and compression.
*   **File Operations:** `zipfile` for folder compression/decompression, `shutil` for disk space checks, and `os` for path manipulation.
*   **Persistence:** A simple `ip.txt` stores the last used IP, and `transfer_progress.json` enables resumable transfers.

---

### 🤝 Contributing

Contributions are welcome! If you have suggestions for improvements or find a bug, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Commit your changes (`git commit -am 'Add some feature'`).
4.  Push to the branch (`git push origin feature/your-feature-name`).
5.  Create a new Pull Request.

---

### 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
