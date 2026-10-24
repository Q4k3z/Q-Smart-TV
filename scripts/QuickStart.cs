using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

internal static class QuickStart
{
    [STAThread]
    private static int Main()
    {
        string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        string identity;
        using (var hash = SHA256.Create())
            identity = BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(root.ToUpperInvariant()))).Replace("-", "");
        using (var mutex = new Mutex(false, @"Local\QSmartTVQuickStart-" + identity))
        {
            bool owned;
            try { owned = mutex.WaitOne(0); }
            catch (AbandonedMutexException) { owned = true; }
            if (!owned) return 0;
            try { return Run(root); }
            finally { mutex.ReleaseMutex(); }
        }
    }

    private static int Run(string root)
    {
        string logPath = Path.Combine(root, "data", "logs", "quickstart.log");
        try
        {
            string python = Path.Combine(root, ".venv", "Scripts", "python.exe");
            string script = Path.Combine(root, "scripts", "start_smarttv.py");
            if (!File.Exists(python) || !File.Exists(script) || !File.Exists(Path.Combine(root, "server.py")))
                throw new InvalidOperationException(
                    "Giữ Q Smart TV.exe trong thư mục Qsmarttv cùng mã ứng dụng và .venv. " +
                    "Nếu chưa cài môi trường, chạy setup.bat một lần rồi mở lại.");

            Directory.CreateDirectory(Path.GetDirectoryName(logPath));
            var output = new StringBuilder();
            object outputLock = new object();
            using (var process = new Process())
            {
                process.StartInfo = new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = "\"" + script + "\"",
                    WorkingDirectory = root,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };
                process.StartInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                DataReceivedEventHandler receive = delegate(object sender, DataReceivedEventArgs e)
                {
                    if (e.Data == null) return;
                    string line = Regex.Replace(e.Data, @"(token=)[^\s]+", "$1[REDACTED]", RegexOptions.IgnoreCase);
                    lock (outputLock) output.AppendLine(line);
                };
                process.OutputDataReceived += receive;
                process.ErrorDataReceived += receive;
                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                if (!process.WaitForExit(60000))
                    throw new TimeoutException("Khởi động quá lâu. Kiểm tra data\\logs\\startup.log và server.log. Server có thể vẫn đang chạy.");
                // Drain both redirected streams before writing the result.
                process.WaitForExit();
                lock (outputLock)
                    File.WriteAllText(logPath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + Environment.NewLine + output, Encoding.UTF8);
                if (process.ExitCode != 0)
                    throw new InvalidOperationException("Chưa mở được Q Smart TV. Xem data\\logs\\quickstart.log và startup.log.");
                return 0;
            }
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Q Smart TV — Không khởi động được", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
