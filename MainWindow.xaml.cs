using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using Microsoft.Win32;
using MetadataExtractor;
using MetadataExtractor.Formats.Exif;
using MetadataExtractor.Formats.QuickTime;
using MetadataExtractor.Formats.Avi;
using MetadataExtractor.Formats.Mpeg;

namespace PhotoSDCopy
{
    public partial class MainWindow : Window
    {
        private bool _isRunning = false;

        public MainWindow()
        {
            InitializeComponent();
        }

        private void SourceBrowseButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFolderDialog
            {
                Title = "SDカードのドライブを選択"
            };
            if (dialog.ShowDialog() == true)
            {
                SourceTextBox.Text = dialog.FolderName;
            }
        }

        private void DestBrowseButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFolderDialog
            {
                Title = "コピー先フォルダを選択"
            };
            if (dialog.ShowDialog() == true)
            {
                DestTextBox.Text = dialog.FolderName;
            }
        }

        private async void ExecuteButton_Click(object sender, RoutedEventArgs e)
        {
            if (_isRunning)
            {
                MessageBox.Show("すでに処理が実行中です。完了までお待ちください。", "処理中", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            string source = SourceTextBox.Text.Trim();
            string destination = DestTextBox.Text.Trim();

            if (string.IsNullOrEmpty(source) || string.IsNullOrEmpty(destination))
            {
                MessageBox.Show("コピー元とコピー先を指定してください。", "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            if (!System.IO.Directory.Exists(source))
            {
                MessageBox.Show("指定されたコピー元が存在しません。", "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            try
            {
                if (!System.IO.Directory.Exists(destination))
                {
                    System.IO.Directory.CreateDirectory(destination);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"コピー先フォルダを作成できません: {ex.Message}", "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            _isRunning = true;
            ExecuteButton.IsEnabled = false;
            LogTextBox.Clear();
            CopyProgressBar.Value = 0;

            await Task.Run(() => CopyFiles(source, destination));

            _isRunning = false;
            ExecuteButton.IsEnabled = true;
        }

        private void Log(string message)
        {
            Dispatcher.Invoke(() =>
            {
                LogTextBox.AppendText(message + Environment.NewLine);
                LogTextBox.ScrollToEnd();
            });
        }

        private void ReportProgress(double percentage)
        {
            Dispatcher.Invoke(() =>
            {
                CopyProgressBar.Value = percentage;
            });
        }

        private DateTime GetFileDate(string filePath)
        {
            try
            {
                var ext = Path.GetExtension(filePath).ToLower();
                var imageExts = new[] { ".jpg", ".jpeg", ".png", ".tif", ".tiff" };
                var videoExts = new[] { ".mp4", ".mov", ".avi", ".mpg", ".mpeg", ".m4v" };

                if (imageExts.Contains(ext) || videoExts.Contains(ext))
                {
                    try
                    {
                        var directories = ImageMetadataReader.ReadMetadata(filePath);
                        
                        // Check EXIF
                        var subIfdDirectory = directories.OfType<ExifSubIfdDirectory>().FirstOrDefault();
                        if (subIfdDirectory != null && subIfdDirectory.TryGetDateTime(ExifDirectoryBase.TagDateTimeOriginal, out var dateTime))
                        {
                            return dateTime;
                        }
                        
                        var ifd0Directory = directories.OfType<ExifIfd0Directory>().FirstOrDefault();
                        if (ifd0Directory != null && ifd0Directory.TryGetDateTime(ExifDirectoryBase.TagDateTime, out dateTime))
                        {
                            return dateTime;
                        }

                        // Check QuickTime (MP4/MOV)
                        var qtDirectory = directories.OfType<QuickTimeMovieHeaderDirectory>().FirstOrDefault();
                        if (qtDirectory != null && qtDirectory.TryGetDateTime(QuickTimeMovieHeaderDirectory.TagCreated, out dateTime))
                        {
                            return dateTime;
                        }

                        var aviDirectory = directories.OfType<AviDirectory>().FirstOrDefault();
                        if (aviDirectory != null && aviDirectory.TryGetDateTime(AviDirectory.TagDateTimeOriginal, out dateTime))
                        {
                            return dateTime;
                        }
                    }
                    catch (Exception)
                    {
                        // Ignore metadata extraction errors and fallback
                    }
                }

                // Fallback to file creation time
                return File.GetLastWriteTime(filePath);
            }
            catch (Exception ex)
            {
                Log($"日付情報の取得に失敗: {filePath} - {ex.Message}");
                return DateTime.Now;
            }
        }

        private List<string> FindMediaFolders(string basePath)
        {
            var candidates = new List<string>();
            var expected = new[]
            {
                Path.Combine(basePath, "DCIM"),
                Path.Combine(basePath, "PRIVATE", "M4ROOT", "CLIP")
            };

            foreach (var p in expected)
            {
                if (System.IO.Directory.Exists(p))
                {
                    candidates.Add(p);
                }
            }

            var directoryName = new DirectoryInfo(basePath).Name.ToUpper();
            if ((directoryName == "DCIM" || directoryName == "CLIP") && System.IO.Directory.Exists(basePath))
            {
                candidates.Add(basePath);
            }

            if (candidates.Count == 0)
            {
                try
                {
                    SearchFolders(basePath, candidates, 0, 2);
                }
                catch (Exception) { }
            }

            return candidates.Distinct().ToList();
        }

        private void SearchFolders(string currentPath, List<string> candidates, int depth, int maxDepth)
        {
            if (depth > maxDepth) return;

            try
            {
                foreach (var dir in System.IO.Directory.GetDirectories(currentPath))
                {
                    var dirName = new DirectoryInfo(dir).Name.ToUpper();
                    if (dirName == "DCIM" || dirName == "CLIP")
                    {
                        candidates.Add(dir);
                    }
                    else
                    {
                        SearchFolders(dir, candidates, depth + 1, maxDepth);
                    }
                    
                    if (candidates.Count > 0) return;
                }
            }
            catch (UnauthorizedAccessException) { }
        }

        private void CopyFiles(string source, string destination)
        {
            try
            {
                Log("コピー処理を開始します...");
                Log($"コピー元: {source}");
                Log($"コピー先: {destination}");

                var pathsToCheck = FindMediaFolders(source);

                if (pathsToCheck.Count == 0)
                {
                    Log("コピー元に有効なフォルダ構造が見つかりません。");
                    Dispatcher.Invoke(() => MessageBox.Show("コピー元にDCIMまたはCLIPフォルダが見つかりません。", "警告", MessageBoxButton.OK, MessageBoxImage.Warning));
                    return;
                }

                var allFiles = new List<string>();

                foreach (var path in pathsToCheck)
                {
                    try
                    {
                        var files = System.IO.Directory.GetFiles(path, "*.*", SearchOption.AllDirectories);
                        foreach (var file in files)
                        {
                            if (!file.EndsWith(".xml", StringComparison.OrdinalIgnoreCase) &&
                                !file.EndsWith(".ctg", StringComparison.OrdinalIgnoreCase))
                            {
                                allFiles.Add(file);
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Log($"フォルダの検索中にエラー: {path} - {ex.Message}");
                    }
                }

                if (allFiles.Count == 0)
                {
                    Log("コピー対象ファイルが見つかりません。");
                    Dispatcher.Invoke(() => MessageBox.Show("コピー対象ファイルが見つかりません。", "情報", MessageBoxButton.OK, MessageBoxImage.Information));
                    return;
                }

                Log($"コピー対象ファイル数: {allFiles.Count}");

                int totalFiles = allFiles.Count;
                int copiedFiles = 0;

                foreach (var filePath in allFiles)
                {
                    try
                    {
                        var fileDate = GetFileDate(filePath);
                        string dateFolder = fileDate.ToString("yyyy-MM-dd");

                        string ext = Path.GetExtension(filePath).TrimStart('.').ToUpper();
                        if (string.IsNullOrEmpty(ext))
                        {
                            ext = "OTHER";
                        }

                        string dateFolderPath = Path.Combine(destination, dateFolder);
                        string extFolderPath = Path.Combine(dateFolderPath, ext);

                        System.IO.Directory.CreateDirectory(extFolderPath);

                        string destFile = Path.Combine(extFolderPath, Path.GetFileName(filePath));

                        if (File.Exists(destFile))
                        {
                            string baseName = Path.GetFileNameWithoutExtension(filePath);
                            string extension = Path.GetExtension(filePath);
                            int counter = 1;

                            while (File.Exists(destFile))
                            {
                                string newName = $"{baseName}_{counter}{extension}";
                                destFile = Path.Combine(extFolderPath, newName);
                                counter++;
                            }
                        }

                        File.Copy(filePath, destFile);

                        copiedFiles++;
                        ReportProgress((double)copiedFiles / totalFiles * 100);

                        if (totalFiles < 100 || copiedFiles % 10 == 0)
                        {
                            Log($"コピー: {Path.GetFileName(filePath)} -> {dateFolder}/{ext}/");
                        }
                    }
                    catch (Exception ex)
                    {
                        Log($"エラー: {filePath} のコピーに失敗しました - {ex.Message}");
                    }
                }

                Log($"コピー完了！ 合計 {copiedFiles} ファイルをコピーしました。");
                Dispatcher.Invoke(() => MessageBox.Show($"コピー処理が完了しました。\n合計 {copiedFiles} ファイルをコピーしました。", "完了", MessageBoxButton.OK, MessageBoxImage.Information));
            }
            catch (Exception ex)
            {
                Log($"エラーが発生しました: {ex.Message}");
                Dispatcher.Invoke(() => MessageBox.Show($"処理中にエラーが発生しました:\n{ex.Message}", "エラー", MessageBoxButton.OK, MessageBoxImage.Error));
            }
        }
    }
}