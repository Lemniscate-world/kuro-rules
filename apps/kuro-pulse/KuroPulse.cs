// KuroPulse v1.2 — application tray native pour l'intelligence d'entreprise Kuro.
// Compile avec le csc.exe inclus dans Windows (.NET Framework 4.x), zéro dépendance runtime.
// UI : langage Primer devtool (R109).

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace KuroPulse
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            bool created;
            using (var mutex = new Mutex(true, "KuroPulseTrayApp", out created))
            {
                if (!created)
                {
                    File.WriteAllText(
                        Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "last-run.log"),
                        DateTime.Now + " : déjà actif");
                    return;
                }
                var logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "last-run.log");
                try
                {
                    File.WriteAllText(logPath, DateTime.Now + " : démarrage\n");
                    Application.EnableVisualStyles();
                    Application.Run(new TrayContext());
                    File.AppendAllText(logPath, DateTime.Now + " : arrêt propre\n");
                }
                catch (Exception ex)
                {
                    File.WriteAllText(logPath,
                        DateTime.Now + " : ERREUR FATALE\n" + ex.ToString());
                }
            }
        }
    }

    internal static class Palette
    {
        public static readonly Color Bg = Color.FromArgb(13, 17, 23);
        public static readonly Color Card = Color.FromArgb(22, 27, 34);
        public static readonly Color CardHover = Color.FromArgb(30, 36, 45);
        public static readonly Color Border = Color.FromArgb(48, 54, 61);
        public static readonly Color Ink = Color.FromArgb(230, 237, 243);
        public static readonly Color Muted = Color.FromArgb(139, 148, 158);
        public static readonly Color Green = Color.FromArgb(63, 185, 80);
        public static readonly Color Red = Color.FromArgb(248, 81, 73);
        public static readonly Color Accent = Color.FromArgb(88, 166, 255);

        public static GraphicsPath Rounded(RectangleF r, float radius)
        {
            var path = new GraphicsPath();
            var d = radius * 2;
            path.AddArc(r.X, r.Y, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        public static Bitmap Logo(int size, Color? dotColor)
        {
            var big = new Bitmap(size * 2, size * 2);
            using (var g = Graphics.FromImage(big))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                g.Clear(Color.Transparent);
                using (var path = Rounded(new RectangleF(1, 1, size * 2f - 2, size * 2f - 2), size * 0.44f))
                using (var bg = new SolidBrush(Bg))
                using (var pen = new Pen(Border, size / 21f))
                    { g.FillPath(bg, path); g.DrawPath(pen, path); }
                using (var font = new Font("Segoe UI Symbol", size * 1.1f, FontStyle.Bold, GraphicsUnit.Pixel))
                using (var accent = new SolidBrush(Accent))
                using (var fmt = new StringFormat
                { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
                {
                    g.DrawString(((char)0x03BB).ToString(), font, accent,
                        new RectangleF(0, -size * 0.10f, size * 2f, size * 2.1f), fmt);
                }
                if (dotColor.HasValue)
                {
                    var d = size * 0.42f;
                    using (var ring = new SolidBrush(Bg))
                    using (var dot = new SolidBrush(dotColor.Value))
                    {
                        g.FillEllipse(ring, size * 2 - d * 1.5f - 2, size * 2 - d * 1.5f - 2, d * 1.5f + 4, d * 1.5f + 4);
                        g.FillEllipse(dot, size * 2 - d * 1.35f, size * 2 - d * 1.35f, d * 1.35f, d * 1.35f);
                    }
                }
            }
            var small = new Bitmap(size, size);
            using (var g2 = Graphics.FromImage(small))
            {
                g2.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g2.DrawImage(big, 0, 0, size, size);
            }
            big.Dispose();
            return small;
        }
    }

    // ---------- données ----------

    internal class FailItem { public string Name; public string Url; }

    internal class RobotState
    {
        public string Overall = "unknown";
        public string Engine = "déterministe";
        public string DaemonTs = "?";
        public int AlertsOpen;
        public List<string> Actions = new List<string>();
        public List<RepoRow> Repos = new List<RepoRow>();
    }

    internal class RepoRow
    {
        public string Name;
        public string Health;
        public int ChecksOk;
        public int ChecksTotal;
        public List<FailItem> Failing = new List<FailItem>();
    }

    // ---------- contrôles dessinés ----------

    internal class BufferedPanel : Panel
    {
        public BufferedPanel() { DoubleBuffered = true; }
    }

    internal class Pill : Control
    {
        private string _value = "";
        private Color _tone = Palette.Green;

        public Pill()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        }

        public void Set(string value, Color tone)
        {
            _value = value; _tone = tone;
            Width = TextRenderer.MeasureText(value, Font).Width + 26;
            Height = 26;
            Invalidate();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            using (var bg = new SolidBrush(Color.FromArgb(40, _tone)))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), Height / 2f))
                e.Graphics.FillPath(bg, path);
            TextRenderer.DrawText(e.Graphics, _value, new Font("Segoe UI Semibold", 8.25f),
                ClientRectangle, _tone,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding);
        }
    }

    internal class ActionLine : Control
    {
        private readonly string _line;

        public ActionLine(string line)
        {
            _line = line;
            Height = 20;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            var parts = _line.Split('|');
            TextRenderer.DrawText(g, parts[0].Trim(), new Font("Consolas", 7.5f),
                new Rectangle(2, 3, 92, 15), Palette.Muted,
                TextFormatFlags.Left | TextFormatFlags.NoPadding);
            var rest = parts.Length > 1 ? _line.Substring(_line.IndexOf('|') + 1).Trim() : "";
            TextRenderer.DrawText(g, rest, new Font("Consolas", 7.75f),
                new Rectangle(100, 3, Math.Max(60, Width - 104), 15), Palette.Ink,
                TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
        }
    }

    // ---------- tray ----------

    internal class TrayContext : ApplicationContext
    {
        private const string ApiBase = "http://127.0.0.1:8767";
        private const string KuroRoot = @"C:\Users\Utilisateur\Documents\kuro-rules";

        private readonly NotifyIcon _tray;
        private KuroPanel _panel;
        private RobotState _last = new RobotState();
        private string _lastOverall;
        private DateTime _lastApiStart = DateTime.MinValue;

        public TrayContext()
        {
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;

            _tray = new NotifyIcon
            {
                Icon = Icon.FromHandle(Palette.Logo(16, null).GetHicon()),
                Text = "KuroPulse : connexion...",
                Visible = true
            };

            var menu = new ContextMenuStrip();
            menu.Items.Add("Panneau KuroPulse", null, delegate { ShowPanel(); });
            menu.Items.Add("Desk web", null, delegate { OpenUrl(ApiBase + "/"); });
            menu.Items.Add("Journal des actions", null, delegate { OpenJournal(); });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Rafraîchir", null, delegate { FetchState(true); });
            menu.Items.Add("Quitter", null, delegate { ExitApp(); });
            _tray.ContextMenuStrip = menu;
            _tray.DoubleClick += delegate { ShowPanel(); };

            var timer = new System.Windows.Forms.Timer { Interval = 60000 };
            timer.Tick += delegate { FetchState(false); };
            timer.Start();

            FetchState(false);
        }

        private void EnsureApi()
        {
            try
            {
                using (var wc = new WebClient())
                    wc.DownloadString(ApiBase + "/api/status");
            }
            catch
            {
                if ((DateTime.Now - _lastApiStart).TotalMinutes > 10)
                {
                    _lastApiStart = DateTime.Now;
                    var apiScript = Path.Combine(KuroRoot, "scripts", "kuro_api.py");
                    if (File.Exists(apiScript))
                        System.Diagnostics.Process.Start(
                            "pythonw",
                            string.Format("\"{0}\" --port 8767", apiScript));
                }
            }
        }

        private RobotState Fetch()
        {
            EnsureApi();
            using (var wc = new WebClient())
            {
                wc.Headers["User-Agent"] = "KuroPulse/1.0";
                var json = wc.DownloadString(ApiBase + "/api/robot?ts=" + DateTime.UtcNow.Ticks);
                var ser = new JavaScriptSerializer { MaxJsonLength = 1 << 26 };
                var data = ser.Deserialize<Dictionary<string, object>>(json);

                var state = new RobotState();
                object tmp;
                if (data.TryGetValue("ci_overall", out tmp) && tmp != null)
                    state.Overall = tmp.ToString();

                if (data.TryGetValue("llm_engine", out tmp) && tmp != null)
                    state.Engine = tmp.ToString();

                if (data.TryGetValue("alerts_open", out tmp) && tmp is int)
                    state.AlertsOpen = (int)tmp;

                if (data.TryGetValue("daemon", out tmp))
                {
                    var daemon = tmp as Dictionary<string, object>;
                    if (daemon != null && daemon.ContainsKey("timestamp"))
                        state.DaemonTs = Trim10(daemon["timestamp"].ToString());
                }

                if (data.TryGetValue("actions_tail", out tmp) && tmp != null)
                    foreach (var a in (System.Collections.IEnumerable)tmp)
                    {
                        var line = Clean(a.ToString());
                        if (!line.Contains("| scan "))
                            state.Actions.Add(line);
                    }

                if (data.TryGetValue("repos", out tmp) && tmp != null)
                    foreach (var r in (System.Collections.IEnumerable)tmp)
                    {
                        var rd = r as Dictionary<string, object>;
                        if (rd == null) continue;
                        var row = new RepoRow
                        {
                            Name = Str(rd, "name"),
                            Health = Str(rd, "health"),
                            ChecksOk = Int(rd, "checks_ok"),
                            ChecksTotal = Int(rd, "checks_total"),
                            Failing = new List<FailItem>()
                        };
                        object fails;
                        if (rd.TryGetValue("failing", out fails) && fails != null)
                            foreach (var f in (System.Collections.IEnumerable)fails)
                            {
                                var fd = f as Dictionary<string, object>;
                                if (fd == null) continue;
                                row.Failing.Add(new FailItem
                                {
                                    Name = Str(fd, "name"),
                                    Url = Str(fd, "url")
                                });
                            }
                        state.Repos.Add(row);
                    }
                return state;
            }
        }

        private static string Str(Dictionary<string, object> d, string k)
        {
            object v; return d.TryGetValue(k, out v) && v != null ? v.ToString() : "";
        }

        private static int Int(Dictionary<string, object> d, string k)
        {
            object v;
            if (d.TryGetValue(k, out v) && v is int) return (int)v;
            int parsed;
            return int.TryParse(Str(d, k), out parsed) ? parsed : 0;
        }

        private static string Trim10(string s)
        {
            s = s.Replace("T", " ").Replace("Z", "");
            return s.Length >= 16 ? s.Substring(0, 16) : s;
        }

        private static string Clean(string s)
        {
            return s.TrimStart('-', ' ')
                   .Replace("| relance (dry-run)", "| relance")
                   .Replace("| issue (dry-run)", "| issue");
        }

        private void SetTray(RobotState s)
        {
            var dot = s.Overall == "green" ? Palette.Green
                    : s.Overall == "red" ? Palette.Red : (Color?)Palette.Muted;
            _tray.Icon = Icon.FromHandle(Palette.Logo(16, dot).GetHicon());
            var tip = string.Format("CI {0} | cerveau {1} | daemon {2} | alertes {3}",
                s.Overall, s.Engine, s.DaemonTs, s.AlertsOpen);
            _tray.Text = tip.Length > 63 ? tip.Substring(0, 63) : tip;
        }

        private void FetchState(bool manual)
        {
            RobotState state;
            try { state = Fetch(); }
            catch
            {
                SetTray(new RobotState());
                _tray.Text = "KuroPulse : API injoignable";
                if (_panel != null && !_panel.IsDisposed) _panel.UpdateError();
                return;
            }

            var previousActions = _last.Actions.Count;
            var previousAlerts = _last.AlertsOpen;
            _last = state;
            SetTray(state);

            if (_panel != null && !_panel.IsDisposed) _panel.Render(state);

            if (!manual && _lastOverall != null && _lastOverall != state.Overall)
            {
                _tray.BalloonTipTitle = "KuroPulse — CI " + state.Overall.ToUpper();
                _tray.BalloonTipText = state.Overall == "red"
                    ? "Des checks sont passés en rouge."
                    : "Tous les checks sont au vert.";
                _tray.ShowBalloonTip(8000);
            }
            _lastOverall = state.Overall;

            if (!manual && previousActions > 0 &&
                state.Actions.Count > previousActions &&
                state.Actions.Count > 0)
            {
                _tray.BalloonTipTitle = "KuroPulse — auto-action";
                _tray.BalloonTipText = state.Actions[state.Actions.Count - 1];
                _tray.ShowBalloonTip(8000);
            }
        }

        private void AckAllAlerts()
        {
            var confirm = MessageBox.Show(
                "Acquitter toutes les alertes ouvertes (" + _last.AlertsOpen + ") ?\n\n" +
                "Elles resteront consultables dans kuro.db.",
                "KuroPulse", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (confirm != DialogResult.Yes) return;
            try
            {
                using (var wc = new WebClient())
                {
                    wc.Headers["Content-Type"] = "application/json";
                    wc.UploadString(ApiBase + "/api/alerts/ack-all", "{}");
                }
                _tray.BalloonTipTitle = "KuroPulse";
                _tray.BalloonTipText = "Alertes acquittées.";
                _tray.ShowBalloonTip(4000);
                FetchState(true);
            }
            catch (Exception exc)
            {
                MessageBox.Show("Echec: " + exc.Message, "KuroPulse");
            }
        }

        private void TriggerRobot()
        {
            try
            {
                System.Diagnostics.Process.Start("powershell", "-NoProfile -Command \"gh workflow run kuro.yml --repo Lemniscate-world/kuro-rules\"");
                _tray.BalloonTipTitle = "KuroPulse";
                _tray.BalloonTipText = "Cycle du robot déclenché.";
                _tray.ShowBalloonTip(4000);
            }
            catch (Exception exc)
            {
                MessageBox.Show("Echec: " + exc.Message, "KuroPulse");
            }
        }

        private void ShowPanel()
        {
            if (_panel == null || _panel.IsDisposed)
            {
                _panel = new KuroPanel(
                    delegate { FetchState(true); },
                    delegate { OpenUrl(ApiBase + "/"); },
                    delegate { TriggerRobot(); },
                    delegate { AckAllAlerts(); });
                _panel.Render(_last);
            }
            _panel.Show();
            _panel.Activate();
        }

        private void OpenUrl(string url)
        {
            try { System.Diagnostics.Process.Start(url); } catch { }
        }

        private void OpenJournal()
        {
            var path = Path.Combine(KuroRoot, "KURO_ACTIONS_LOG.md");
            if (File.Exists(path)) System.Diagnostics.Process.Start("notepad.exe", "\"" + path + "\"");
        }

        private void ExitApp()
        {
            _tray.Visible = false;
            Application.Exit();
        }
    }

    // ---------- hôte de colonne centrée (anti-étirement) ----------

    internal class ColumnHost : BufferedPanel
    {
        public int ColumnWidth = 430;

        public ColumnHost()
        {
            AutoScroll = true;
            Resize += delegate { Recenter(); };
            ControlAdded += delegate { Recenter(); };
        }

        public void Track(Control c, int y, int h)
        {
            c.SetBounds(0, y, ColumnWidth, h);
            Controls.Add(c);
        }

        public void Recenter()
        {
            int x = Math.Max(Padding.Left + 2, (ClientSize.Width - ColumnWidth) / 2 - Padding.Left);
            foreach (Control c in Controls)
                if (!(c is ActionLine))
                    c.Left = x;
                else
                    c.Left = x + 6;
        }
    }

    internal class RepoRowItem : Control
    {
        private readonly RepoRow _d;
        private readonly string _actionsUrl;
        private bool _hover;

        public RepoRowItem(RepoRow d, string actionsUrl)
        {
            _d = d; _actionsUrl = actionsUrl;
            Height = 48;
            Cursor = Cursors.Hand;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw | ControlStyles.Selectable, true);
            Click += delegate { Open(_actionsUrl); };
        }

        private void Open(string url)
        {
            try { System.Diagnostics.Process.Start(url); } catch { }
        }

        protected override void OnMouseEnter(EventArgs e) { _hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hover = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnMouseClick(MouseEventArgs e)
        {
            base.OnMouseClick(e);
            // clic sur la zone droite du détail -> premier run en échec
            if (e.Button == MouseButtons.Right && e.X > Width - 150 && _d.Failing.Count > 0 &&
                !string.IsNullOrEmpty(_d.Failing[0].Url))
                Open(_d.Failing[0].Url);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            using (var bg = new SolidBrush(_hover ? Palette.CardHover : Palette.Card))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), 6))
                g.FillPath(bg, path);

            var green = _d.Health == "green";
            g.FillEllipse(new SolidBrush(green ? Palette.Green : Palette.Red), 14, Height / 2f - 11, 8, 8);

            TextRenderer.DrawText(g, _d.Name, new Font("Segoe UI Semibold", 9.25f),
                new Rectangle(30, 6, Width - 130, 18), Palette.Ink,
                TextFormatFlags.Left | TextFormatFlags.NoPadding);

            if (green)
            {
                TextRenderer.DrawText(g, _d.ChecksTotal + " checks OK", new Font("Segoe UI", 8f),
                    new Rectangle(Width - 110, 8, 100, 16), Palette.Muted,
                    TextFormatFlags.Right | TextFormatFlags.NoPadding);
                TextRenderer.DrawText(g, "tous les checks passent", new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 26, Width - 42, 15), Color.FromArgb(90, Palette.Muted),
                    TextFormatFlags.Left | TextFormatFlags.NoPadding);
            }
            else
            {
                TextRenderer.DrawText(g, _d.Failing.Count + " en échec ↗", new Font("Segoe UI Semibold", 8f),
                    new Rectangle(Width - 120, 8, 108, 16), Palette.Red,
                    TextFormatFlags.Right | TextFormatFlags.NoPadding);
                var names = new List<string>();
                foreach (var f in _d.Failing) names.Add(f.Name);
                TextRenderer.DrawText(g, string.Join(" · ", names.ToArray()), new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 26, Width - 42, 15), Palette.Muted,
                    TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
            }
        }
    }

    internal class SectionCaption : Control
    {
        public SectionCaption(string text)
        {
            Height = 26;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            Paint += delegate(object s, PaintEventArgs e)
            {
                var g = e.Graphics;
                TextRenderer.DrawText(g, text, new Font("Segoe UI", 7.5f, FontStyle.Bold),
                    new Rectangle(1, 4, Width - 2, 14), Palette.Muted,
                    TextFormatFlags.Left | TextFormatFlags.NoPadding);
                using (var pen = new Pen(Color.FromArgb(35, Palette.Border)))
                    g.DrawLine(pen, 1, Height - 5, Width - 1, Height - 5);
            };
        }
    }

    internal class StatCard : Control
    {
        private readonly string _caption;
        private readonly string _value;
        private readonly Color _valueColor;

        public StatCard(string caption, string value, Color valueColor)
        {
            _caption = caption; _value = value; _valueColor = valueColor;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            using (var bg = new SolidBrush(Palette.Card))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), 6))
                g.FillPath(bg, path);
            TextRenderer.DrawText(g, _caption, new Font("Segoe UI", 6.75f, FontStyle.Bold),
                new Rectangle(10, 7, Width - 16, 13), Palette.Muted,
                TextFormatFlags.Left | TextFormatFlags.NoPadding);
            TextRenderer.DrawText(g, _value, new Font("Segoe UI Semibold", 10f),
                new Rectangle(10, 22, Width - 16, Height - 26), _valueColor,
                TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
        }
    }

    internal class KuroPanel : Form
    {
        private const string ApiBase = "http://127.0.0.1:8767";

        private readonly Action _refresh;
        private readonly Action _triggerRobot;
        private readonly Action _ackAll;
        private readonly Action _openDesk;

        private readonly ColumnHost _content;
        private DateTime _lastRender = DateTime.Now;
        private int _lastOkChecks = -1;

        [DllImport("dwmapi.dll")]
        private static extern void DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

        public KuroPanel(Action refresh, Action triggerRobot, Action ackAll, Action openDesk)
        {
            _refresh = refresh; _triggerRobot = triggerRobot;
            _ackAll = ackAll; _openDesk = openDesk;

            Text = "KuroPulse";
            Size = new Size(480, 800);
            BackColor = Palette.Bg;
            ForeColor = Palette.Ink;
            StartPosition = FormStartPosition.Manual;
            RestoreGeometry();

            _content = new ColumnHost
            {
                BackColor = Palette.Bg,
                Padding = new Padding(12, 12, 12, 12)
            };
            Controls.Add(_content);
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            try
            {
                var one = 1;
                DwmSetWindowAttribute(Handle, 20, ref one, 4);
                DwmSetWindowAttribute(Handle, 19, ref one, 4);
            }
            catch { }
            try
            {
                using (var bmp = Palette.Logo(64, null))
                    Icon = Icon.FromHandle(bmp.GetHicon());
            }
            catch { }
        }

        private string GeoFile()
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "KuroPulse");
            return Path.Combine(dir, "panel.pos");
        }

        private void SaveGeometry()
        {
            if (WindowState != FormWindowState.Normal) return;
            try { File.WriteAllText(GeoFile(), Left + ";" + Top + ";" + Width + ";" + Height); } catch { }
        }

        private void RestoreGeometry()
        {
            try
            {
                var file = GeoFile();
                if (!File.Exists(file)) return;
                var parts = File.ReadAllText(file).Split(';');
                int l, t, w, h;
                if (parts.Length == 4 &&
                    int.TryParse(parts[0], out l) && int.TryParse(parts[1], out t) &&
                    int.TryParse(parts[2], out w) && int.TryParse(parts[3], out h))
                {
                    var wa = Screen.PrimaryScreen.WorkingArea;
                    w = Math.Max(380, Math.Min(w, 560));   // fenêtre compacte type gitify
                    h = Math.Max(500, Math.Min(h, wa.Height - 20));
                    if (l >= wa.Left - 40 && t >= wa.Top && l < wa.Right && t < wa.Bottom)
                        Location = new Point(l, t);
                    Size = new Size(w, h);
                }
            }
            catch { }
        }

        protected override void OnLocationChanged(EventArgs e)
        {
            base.OnLocationChanged(e);
            SaveGeometry();
        }

        protected override void OnResizeEnd(EventArgs e)
        {
            base.OnResizeEnd(e);
            SaveGeometry();
        }

        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            if (keyData == Keys.Escape) { Hide(); return true; }
            if (keyData == Keys.F5) { _refresh(); return true; }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; SaveGeometry(); Hide(); return; }
            base.OnFormClosing(e);
        }

        public void UpdateError()
        {
            _content.Controls.Clear();
            _content.Controls.Add(new Label
            {
                Text = "API Kuro injoignable.\nElle redémarre automatiquement.",
                ForeColor = Palette.Muted,
                AutoSize = true,
                Location = new Point(12, 12)
            });
        }

        private Control Caption(string text)
        {
            return new SectionCaption(text);
        }

        private Label LinkBtn(string text, Action onClick)
        {
            var l = new Label
            {
                Text = text,
                ForeColor = Palette.Accent,
                AutoSize = true,
                Margin = new Padding(0),
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 8.75f)
            };
            l.Click += delegate { onClick(); };
            l.MouseEnter += delegate { l.ForeColor = Palette.Ink; };
            l.MouseLeave += delegate { l.ForeColor = Palette.Accent; };
            return l;
        }

        private static string RelativeTime(string ts)
        {
            DateTime parsed;
            if (!DateTime.TryParse(ts, out parsed)) return ts;
            var delta = DateTime.Now - parsed;
            if (delta.TotalMinutes < 90) return "il y a " + Math.Max(1, (int)delta.TotalMinutes) + " min";
            if (delta.TotalHours < 36) return "il y a " + (int)Math.Round(delta.TotalHours) + " h";
            return "il y a " + (int)delta.TotalDays + " j";
        }

        private class PillBox : Control
        {
            public string Value = "";
            public Color Tone = Palette.Green;
            protected override void OnPaint(PaintEventArgs e)
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                e.Graphics.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
                using (var bg = new SolidBrush(Color.FromArgb(40, Tone)))
                using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), Height / 2f))
                    e.Graphics.FillPath(bg, path);
                TextRenderer.DrawText(e.Graphics, Value, new Font("Segoe UI Semibold", 8.25f),
                    ClientRectangle, Tone,
                    TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding);
            }
        }

        private class FeedLine : Control
        {
            private readonly string _line;
            public FeedLine(string line)
            {
                _line = line; Height = 20;
                SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                         ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            }
            protected override void OnPaint(PaintEventArgs e)
            {
                var g = e.Graphics;
                g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
                var parts = _line.Split('|');
                TextRenderer.DrawText(g, parts[0].Trim(), new Font("Consolas", 7.5f),
                    new Rectangle(4, 3, 92, 15), Palette.Muted,
                    TextFormatFlags.Left | TextFormatFlags.NoPadding);
                var rest = parts.Length > 1 ? _line.Substring(_line.IndexOf('|') + 1).Trim() : "";
                TextRenderer.DrawText(g, rest, new Font("Consolas", 7.75f),
                    new Rectangle(102, 3, Math.Max(60, Width - 106), 15), Palette.Ink,
                    TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
            }
        }

        private class FeedCard : Control
        {
            public readonly List<FeedLine> Lines = new List<FeedLine>();
            public FeedCard() { SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true); }
            protected override void OnPaint(PaintEventArgs e)
            {
                using (var bg = new SolidBrush(Palette.Card))
                using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), 6))
                    e.Graphics.FillPath(bg, path);
            }
        }

        public void Render(RobotState s)
        {
            if (InvokeRequired) { BeginInvoke((Action)delegate { Render(s); }); return; }
            if (IsDisposed) return;
            _lastRender = DateTime.Now;

            var overallColor = s.Overall == "green" ? Palette.Green
                             : s.Overall == "red" ? Palette.Red : Palette.Muted;

            _content.Controls.Clear();

            const int colW = 430;
            int y = 4;

            // entête
            var header = new Panel { Height = 50, BackColor = Color.Transparent };
            var logo = new PictureBox
            {
                Image = Palette.Logo(46, overallColor),
                Size = new Size(46, 46),
                Location = new Point(0, 2),
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = Color.Transparent
            };
            header.Controls.Add(logo);
            header.Controls.Add(new Label
            {
                Text = "KuroPulse",
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI Semibold", 15f),
                AutoSize = true,
                Location = new Point(58, 4),
                BackColor = Color.Transparent
            });
            header.Controls.Add(new Label
            {
                Text = "v1.3 · intelligence d'entreprise lambda-Section",
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f),
                AutoSize = true,
                Location = new Point(60, 32),
                BackColor = Color.Transparent
            });
            _content.Track(header, y, 52); y += 58;

            // pilule état
            var pill = new PillBox();
            pill.Value = s.Overall == "green" ? "TOUS LES CHECKS SONT VERTS"
                       : s.Overall == "red" ? "CHECKS EN ÉCHEC" : "ÉTAT INCONNU";
            pill.Tone = overallColor;
            var pillW = TextRenderer.MeasureText(pill.Value, new Font("Segoe UI Semibold", 8.25f)).Width + 30;
            pill.SetBounds(0, y, pillW, 26);
            _content.Controls.Add(pill);
            y += 38;

            // stats 4 cartes
            var totalChecks = 0;
            foreach (var r in s.Repos) totalChecks += r.ChecksTotal;
            var okChecks = totalChecks;
            foreach (var r in s.Repos) okChecks -= r.Failing.Count;

            var deltaText = "";
            var deltaColor = Palette.Muted;
            if (_lastOkChecks >= 0 && _lastOkChecks != okChecks)
            {
                var diff = okChecks - _lastOkChecks;
                deltaText = diff > 0 ? " +" + diff : " " + diff;
                deltaColor = diff > 0 ? Palette.Green : Palette.Red;
            }
            _lastOkChecks = okChecks;

            var statY = y;
            var statW = (colW - 3 * 8) / 4;
            var checksValue = okChecks + "/" + totalChecks + deltaText;
            var checksColor = s.Overall == "green" ? Palette.Ink : overallColor;
            for (int i = 0; i < 4; i++)
            {
                StatCard card;
                switch (i)
                {
                    case 0: card = new StatCard("CHECKS CI", checksValue, checksColor); break;
                    case 1: card = new StatCard("CERVEAU", s.Engine, Palette.Accent); break;
                    case 2: card = new StatCard("DAEMON", RelativeTime(s.DaemonTs), Palette.Ink); break;
                    default: card = new StatCard("ALERTES", s.AlertsOpen.ToString(),
                        s.AlertsOpen > 0 ? Palette.Red : Palette.Ink); break;
                }
                card.SetBounds(i * (statW + 8), statY, statW, 54);
                _content.Controls.Add(card);
            }
            y += 62;

            // repos
            _content.Controls.Add(Caption("REPOS SURVEILLÉS"));
            var cap = _content.Controls[_content.Controls.Count - 1];
            cap.SetBounds(0, y, colW, 24); y += 28;
            foreach (var repo in s.Repos)
            {
                var row = new RepoRowItem(repo, "https://github.com/" + repo.Name + "/actions");
                row.SetBounds(0, y, colW, 48);
                _content.Controls.Add(row);
                y += 54;
            }

            // auto-actions
            _content.Controls.Add(Caption("AUTO-ACTIONS RÉCENTES"));
            cap = _content.Controls[_content.Controls.Count - 1];
            cap.SetBounds(0, y, colW, 24); y += 26;

            var feedCard = new FeedCard();
            var feedLines = s.Actions.Count > 0 ? s.Actions : new List<string> { "Aucune action récente — tout roule." };
            foreach (var a in feedLines)
                feedCard.Lines.Add(new FeedLine(a));
            var feedH = feedLines.Count * 21 + 10;
            feedCard.SetBounds(0, y, colW, feedH);
            int fy = 5;
            foreach (var fl in feedCard.Lines)
            {
                fl.SetBounds(0, fy, colW - 8, 19);
                feedCard.Controls.Add(fl);
                fy += 20;
            }
            _content.Controls.Add(feedCard);
            y += feedH + 14;

            // actions rapides
            _content.Controls.Add(Caption("ACTIONS"));
            cap = _content.Controls[_content.Controls.Count - 1];
            cap.SetBounds(0, y, colW, 24); y += 26;

            int bx = 0;
            foreach (var def in new[] {
                Tuple.Create<string, Action>("Acquitter alertes (" + s.AlertsOpen + ")", delegate { _ackAll(); }),
                Tuple.Create<string, Action>("Déclencher robot", delegate { _triggerRobot(); }),
                Tuple.Create<string, Action>("Desk web ↗", delegate { _openDesk(); }),
            })
            {
                var b = new Button
                {
                    Text = def.Item1,
                    FlatStyle = FlatStyle.Flat,
                    BackColor = Palette.Card,
                    ForeColor = Palette.Ink,
                    Font = new Font("Segoe UI", 8.25f),
                    AutoSize = true,
                    Location = new Point(bx, y),
                    Cursor = Cursors.Hand
                };
                b.FlatAppearance.BorderColor = Palette.Border;
                b.FlatAppearance.MouseOverBackColor = Palette.CardHover;
                b.FlatAppearance.BorderSize = 1;
                var act = def.Item2;
                var w = TextRenderer.MeasureText(def.Item1, b.Font).Width + 22;
                b.Width = w;
                b.Click += delegate { act(); };
                _content.Controls.Add(b);
                bx += w + 8;
            }
            y += 36;

            // pied
            int fx = 0;
            foreach (var def in new[] {
                Tuple.Create<string, Action>("GitHub Actions ↗", delegate {
                    try { System.Diagnostics.Process.Start("https://github.com/Lemniscate-world/kuro-rules/actions"); } catch {} }),
                Tuple.Create<string, Action>("Journal ↗", delegate {
                    var p = Path.Combine(KuroRootConst, "KURO_ACTIONS_LOG.md");
                    if (File.Exists(p)) { try { System.Diagnostics.Process.Start("notepad.exe", "\"" + p + "\""); } catch {} } }),
                Tuple.Create<string, Action>("Discord ↗", delegate {
                    try { System.Diagnostics.Process.Start("https://discord.com/channels/@me"); } catch {} }),
            })
            {
                var l = LinkBtn(def.Item1, def.Item2);
                l.SetBounds(fx, y, l.PreferredWidth, 18);
                fx += l.PreferredWidth + 14;
            }
            var stamp = new Label
            {
                Text = "Relevé : " + _lastRender.ToString("dd/MM HH:mm:ss"),
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 7f),
                AutoSize = true,
                BackColor = Color.Transparent
            };
            stamp.SetBounds(0, y + 22, colW, 16);
            _content.Controls.Add(stamp);
            y += 44;

            _content.AutoScrollMinSize = new Size(colW, y + 10);
            _content.Recenter();
        }

        private const string KuroRootConst = @"C:\Users\Utilisateur\Documents\kuro-rules";
    }
}
