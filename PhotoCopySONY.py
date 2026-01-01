import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import re
import threading
from PIL import Image, UnidentifiedImageError
import exifread
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import time

class SDCardCopyTool:
    def __init__(self, root):
        self.root = root
        self.root.title("SDカードコピーツール")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 日本語フォントの設定
        self.default_font = ("Meiryo UI", 10)
        self.root.option_add("*Font", self.default_font)
        
        # スタイルの設定
        self.style = ttk.Style()
        self.style.configure("TButton", font=self.default_font, padding=5)
        self.style.configure("TLabel", font=self.default_font, padding=5)
        self.style.configure("TEntry", font=self.default_font, padding=5)
        
        self.create_widgets()
        self.running = False
        
    def create_widgets(self):
        # フレームの作成
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 入力セクション
        input_frame = ttk.LabelFrame(main_frame, text="入力設定", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # コピー元(SDカード)
        ttk.Label(input_frame, text="コピー元 (SDカードのドライブ):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        source_frame = ttk.Frame(input_frame)
        source_frame.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(source_frame, textvariable=self.source_var, width=30)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.source_button = ttk.Button(source_frame, text="参照", command=self.browse_source)
        self.source_button.pack(side=tk.RIGHT, padx=5)
        
        # コピー先
        ttk.Label(input_frame, text="コピー先フォルダ:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        dest_frame = ttk.Frame(input_frame)
        dest_frame.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        self.dest_var = tk.StringVar()
        self.dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, width=30)
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.dest_button = ttk.Button(dest_frame, text="参照", command=self.browse_destination)
        self.dest_button.pack(side=tk.RIGHT, padx=5)
        
        # 実行ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.execute_button = ttk.Button(button_frame, text="実行", command=self.start_copy_thread, width=20)
        self.execute_button.pack(pady=10)
        
        # プログレスバーとログ表示エリア
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        log_frame = ttk.LabelFrame(main_frame, text="処理ログ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
    def browse_source(self):
        folder = filedialog.askdirectory(title="SDカードのドライブを選択")
        if folder:
            self.source_var.set(folder)
            
    def browse_destination(self):
        folder = filedialog.askdirectory(title="コピー先フォルダを選択")
        if folder:
            self.dest_var.set(folder)
    
    def start_copy_thread(self):
        if self.running:
            messagebox.showinfo("処理中", "すでに処理が実行中です。完了までお待ちください。")
            return
            
        source = self.source_var.get().strip()
        destination = self.dest_var.get().strip()
        
        if not source or not destination:
            messagebox.showerror("エラー", "コピー元とコピー先を指定してください。")
            return
            
        if not os.path.exists(source):
            messagebox.showerror("エラー", "指定されたコピー元が存在しません。")
            return
            
        if not os.path.exists(destination):
            try:
                os.makedirs(destination)
            except Exception as e:
                messagebox.showerror("エラー", f"コピー先フォルダを作成できません: {str(e)}")
                return
        
        # 処理を別スレッドで実行
        self.running = True
        self.execute_button.config(state=tk.DISABLED)
        self.log_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        
        copy_thread = threading.Thread(target=self.copy_files, args=(source, destination))
        copy_thread.daemon = True
        copy_thread.start()
        
    def log(self, message):
        """ログメッセージを表示"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def get_file_date(self, file_path):
        """ファイルの作成日時を取得（画像/動画のメタデータを優先）"""
        try:
            # 拡張子を小文字に変換
            ext = os.path.splitext(file_path)[1].lower()
            
            # 画像ファイルの場合
            if ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                try:
                    # PILを使ってEXIF情報を取得
                    with open(file_path, 'rb') as f:
                        tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')
                        if 'EXIF DateTimeOriginal' in tags:
                            date_str = str(tags['EXIF DateTimeOriginal'])
                            # 2022:05:25 12:34:56 形式を解析
                            date_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                            return date_obj
                        elif 'Image DateTime' in tags:
                            date_str = str(tags['Image DateTime'])
                            date_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                            return date_obj
                except (UnidentifiedImageError, ValueError, KeyError, OSError):
                    pass
                    
            # 動画ファイルの場合
            elif ext in ['.mp4', '.mov', '.avi', '.mpg', '.mpeg', '.m4v']:
                try:
                    parser = createParser(file_path)
                    if parser:
                        metadata = extractMetadata(parser)
                        if metadata and metadata.has('creation_date'):
                            return metadata.get('creation_date').replace(microsecond=0)
                except Exception:
                    pass
                    
            # ファイルのメタデータが取得できない場合はファイルの作成日時を使用
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime)
            
        except Exception as e:
            self.log(f"日付情報の取得に失敗: {file_path} - {str(e)}")
            # 現在の日付をデフォルトとして返す
            return datetime.now()
    
    def copy_files(self, source, destination):
        """ファイルのコピー処理を実行"""
        try:
            self.log(f"コピー処理を開始します...")
            self.log(f"コピー元: {source}")
            self.log(f"コピー先: {destination}")
            
            # コピー元にDCIM/CLIPが無いときに、選択ミスや階層違いでも拾えるように検索
            def find_media_folders(base_path):
                candidates = []
                expected = [
                    os.path.join(base_path, "DCIM"),
                    os.path.join(base_path, "PRIVATE", "M4ROOT", "CLIP"),
                ]
                for p in expected:
                    if os.path.isdir(p):
                        candidates.append(p)
                basename = os.path.basename(base_path).upper()
                if basename in ("DCIM", "CLIP") and os.path.isdir(base_path):
                    candidates.append(base_path)
                if not candidates:
                    for root, dirs, _ in os.walk(base_path):
                        depth = root[len(base_path):].count(os.sep)
                        if depth > 2:
                            continue
                        for d in dirs:
                            if d.upper() in ("DCIM", "CLIP"):
                                candidates.append(os.path.join(root, d))
                        if candidates:
                            break
                return list(dict.fromkeys(candidates))
            
            paths_to_check = find_media_folders(source)
                
            if not paths_to_check:
                self.log("コピー元に有効なフォルダ構造が見つかりません。")
                messagebox.showwarning("警告", "コピー元にDCIMまたはCLIPフォルダが見つかりません。")
                self.finish_copy()
                return
                
            # 処理対象ファイルのリストを作成
            all_files = []
            
            for path in paths_to_check:
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # XMLファイルは除外
                        if file.lower().endswith('.xml'):
                            continue
                        all_files.append(file_path)
            
            if not all_files:
                self.log("コピー対象ファイルが見つかりません。")
                messagebox.showinfo("情報", "コピー対象ファイルが見つかりません。")
                self.finish_copy()
                return
                
            self.log(f"コピー対象ファイル数: {len(all_files)}")
            
            # プログレスバーの更新用
            total_files = len(all_files)
            copied_files = 0
            
            # ファイルをコピー
            for file_path in all_files:
                try:
                    # ファイルの日付情報を取得
                    file_date = self.get_file_date(file_path)
                    date_folder = file_date.strftime('%Y-%m-%d')
                    
                    # ファイルの拡張子を取得
                    _, ext = os.path.splitext(file_path)
                    ext = ext.upper().lstrip('.')  # 拡張子を大文字に変換
                    
                    if not ext:  # 拡張子がない場合
                        ext = "OTHER"
                        
                    # 保存先のフォルダ構造を作成
                    date_folder_path = os.path.join(destination, date_folder)
                    ext_folder_path = os.path.join(date_folder_path, ext)
                    
                    os.makedirs(ext_folder_path, exist_ok=True)
                    
                    # コピー先のファイルパス
                    dest_file = os.path.join(ext_folder_path, os.path.basename(file_path))
                    
                    # 同名ファイルがある場合は名前を変更
                    if os.path.exists(dest_file):
                        base_name, extension = os.path.splitext(os.path.basename(file_path))
                        counter = 1
                        while os.path.exists(dest_file):
                            new_name = f"{base_name}_{counter}{extension}"
                            dest_file = os.path.join(ext_folder_path, new_name)
                            counter += 1
                    
                    # ファイルをコピー
                    shutil.copy2(file_path, dest_file)
                    
                    # 進捗状況更新
                    copied_files += 1
                    progress = (copied_files / total_files) * 100
                    self.progress_var.set(progress)
                    
                    # ログ更新（大量のファイルの場合は頻度を下げる）
                    if total_files < 100 or copied_files % 10 == 0:
                        self.log(f"コピー: {os.path.basename(file_path)} -> {date_folder}/{ext}/")
                        
                except Exception as e:
                    self.log(f"エラー: {file_path} のコピーに失敗しました - {str(e)}")
            
            self.log(f"コピー完了！ 合計 {copied_files} ファイルをコピーしました。")
            messagebox.showinfo("完了", f"コピー処理が完了しました。\n合計 {copied_files} ファイルをコピーしました。")
            
        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{str(e)}")
            
        finally:
            self.finish_copy()
    
    def finish_copy(self):
        """コピー処理の終了処理"""
        self.running = False
        self.execute_button.config(state=tk.NORMAL)
        self.root.update_idletasks()

def main():
    root = tk.Tk()
    app = SDCardCopyTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()