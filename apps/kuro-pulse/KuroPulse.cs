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

    internal class RepoRowItem : Control
    {
        private readonly RepoRow _d;
        private readonly string _actionsUrl;
        private bool _hover;

        public event Action OpenFirstFailure;

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

        protected override void OnMouseClick(MouseEventArgs e)
        {
            base.OnMouseClick(e);
            if (e.Button == MouseButtons.Right && e.X > Width - 150 && _d.Failing.Count > 0 &&
                !string.IsNullOrEmpty(_d.Failing[0].Url))
                Open(_d.Failing[0].Url);
        }

        protected override void OnMouseEnter(EventArgs e) { _hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hover = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            using (var bg = new SolidBrush(_hover ? Palette.CardHover : Palette.Card))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), 6))
                g.FillPath(bg, path);

            var green = _d.Health == "green";
            g.FillEllipse(new SolidBrush(green ? Palette.Green : Palette.Red), 14, Height / 2f - 4, 8, 8);

            TextRenderer.DrawText(g, _d.Name, new Font("Segoe UI Semibold", 9.25f),
                new Rectangle(30, 7, Width - 140, 18), Palette.Ink,
                TextFormatFlags.Left | TextFormatFlags.NoPadding);

            if (green)
            {
                TextRenderer.DrawText(g, _d.ChecksTotal + " checks OK", new Font("Segoe UI", 8f),
                    new Rectangle(Width - 110, 9, 100, 16), Palette.Muted,
                    TextFormatFlags.Right | TextFormatFlags.NoPadding);
                TextRenderer.DrawText(g, "tous les checks passent", new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 26, Width - 42, 15), Color.FromArgb(90, Palette.Muted),
                    TextFormatFlags.Left | TextFormatFlags.NoPadding);
            }
            else
            {
                var n = _d.Failing.Count;
                TextRenderer.DrawText(g, n + " en échec ↗", new Font("Segoe UI Semibold", 8f),
                    new Rectangle(Width - 120, 9, 108, 16), Palette.Red,
                    TextFormatFlags.Right | TextFormatFlags.NoPadding);
                var names = string.Join(" · ", ConvertAllNames(_d.Failing));
                TextRenderer.DrawText(g, names, new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 26, Width - 42, 15), Palette.Muted,
                    TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
            }
        }

        private static List<string> ConvertAllNames(List<FailItem> items)
        {
            var outp = new List<string>();
            foreach (var i in items) outp.Add(i.Name);
            return outp;
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

    // ---------- panneau ----------

    internal class KuroPanel : Form
    {
        private const string ApiBase = "http://127.0.0.1:8767";

        private readonly Action _refresh;
        private readonly Action _triggerRobot;
        private readonly Action _ackAll;
        private readonly Action _openDesk;

        private readonly BufferedPanel _content;
        private readonly FlowLayoutPanel _feed;
        private readonly ToolTip _tips = new ToolTip();
        private DateTime _lastRender = DateTime.Now;
        private int _lastOkChecks = -1;
        private Point _savedLocation = Point.Empty;

        [DllImport("dwmapi.dll")]
        private static extern void DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

        public KuroPanel(Action refresh, Action triggerRobot, Action ackAll, Action openDesk)
        {
            _refresh = refresh; _triggerRobot = triggerRobot;
            _ackAll = ackAll; _openDesk = openDesk;

            Text = "KuroPulse";
            Size = new Size(450, 720);
            BackColor = Palette.Bg;
            ForeColor = Palette.Ink;
            StartPosition = FormStartPosition.Manual;
            RestoreGeometry();

            _content = new BufferedPanel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = Palette.Bg,
                Padding = new Padding(16, 12, 12, 12)
            };
            Controls.Add(_content);

            _feed = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                FlowDirection = FlowDirection.TopDown,
                WrapContents = false,
                AutoSize = true,
                BackColor = Palette.Card,
                Padding = new Padding(6, 4, 6, 4)
            };
            _feed.Resize += delegate
            {
                foreach (Control c in _feed.Controls)
                    if (c is ActionLine) c.Width = Math.Max(160, _feed.ClientSize.Width - 14);
            };
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
            try
            {
                File.WriteAllText(GeoFile(), Left + ";" + Top + ";" + Width + ";" + Height);
            }
            catch { }
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
                    if (l >= wa.Left - 50 && t >= wa.Top - 10 && l < wa.Right && t < wa.Bottom)
                        Location = new Point(l, t);
                    if (w >= MinimumSize.Width) Size = new Size(w, h);
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
                Padding = new Padding(8)
            });
        }

        private Control Caption(string text)
        {
            var holder = new Panel { Dock = DockStyle.Top, Height = 28, Margin = new Padding(0, 14, 0, 4) };
            holder.Controls.Add(new Label
            {
                Text = text,
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f, FontStyle.Bold),
                AutoSize = true,
                Location = new Point(2, 8)
            });
            holder.Paint += delegate(object s, PaintEventArgs ev)
            {
                using (var pen = new Pen(Color.FromArgb(35, Palette.Border)))
                    ev.Graphics.DrawLine(pen, 2, holder.Height - 6, holder.Width - 2, holder.Height - 6);
            };
            holder.Resize += delegate(object s, EventArgs ev)
            {
                (s as Control).Invalidate();
            };
            return holder;
        }

        private Label LinkBtn(string text, Action onClick)
        {
            var l = new Label
            {
                Text = text,
                ForeColor = Palette.Accent,
                AutoSize = true,
                Margin = new Padding(0, 0, 14, 0),
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

        public void Render(RobotState s)
        {
            if (InvokeRequired) { BeginInvoke((Action)delegate { Render(s); }); return; }
            if (IsDisposed) return;
            _lastRender = DateTime.Now;

            var overallColor = s.Overall == "green" ? Palette.Green
                             : s.Overall == "red" ? Palette.Red : Palette.Muted;

            // préserver la position de scroll
            var savedX = _content.AutoScrollPosition.X;
            var savedY = _content.AutoScrollPosition.Y;

            _content.SuspendLayout();
            _content.Controls.Clear();

            // ---- entête ----
            var header = new Panel { Dock = DockStyle.Top, Height = 56, Margin = Padding.Empty };
            header.Controls.Add(new PictureBox
            {
                Image = Palette.Logo(46, overallColor),
                Size = new Size(46, 46),
                Location = new Point(0, 3),
                SizeMode = PictureBoxSizeMode.Zoom
            });
            header.Controls.Add(new Label
            {
                Text = "KuroPulse",
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI Semibold", 15f),
                AutoSize = true,
                Location = new Point(58, 5)
            });
            header.Controls.Add(new Label
            {
                Text = "v1.2 · intelligence d'entreprise lambda-Section",
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f),
                AutoSize = true,
                Location = new Point(60, 33)
            });
            _content.Controls.Add(header);

            // ---- pilule ----
            var pill = new Pill();
            pill.Set(s.Overall == "green" ? "TOUS LES CHECKS SONT VERTS"
                   : s.Overall == "red" ? "CHECKS EN ÉCHEC" : "ÉTAT INCONNU",
                   overallColor);
            pill.Margin = new Padding(2, 8, 0, 4);
            _content.Controls.Add(pill);

            // ---- stats (4 cartes) ----
            var totalChecks = 0;
            foreach (var r in s.Repos) totalChecks += r.ChecksTotal;
            var okChecks = totalChecks;
            foreach (var r in s.Repos) okChecks -= r.Failing.Count;

            var deltaText = "";
            var deltaColor = Palette.Muted;
            if (_lastOkChecks >= 0 && _lastOkChecks != okChecks)
            {
                var diff = okChecks - _lastOkChecks;
                deltaText = diff > 0 ? "  +" + diff : "  " + diff;
                deltaColor = diff > 0 ? Palette.Green : Palette.Red;
            }
            _lastOkChecks = okChecks;

            var stats = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 58,
                ColumnCount = 4,
                RowCount = 1,
                Margin = new Padding(0, 4, 0, 0)
            };
            for (int i = 0; i < 4; i++) stats.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25f));

            var checksCard = MiniStatCard("CHECKS CI", okChecks + "/" + totalChecks + deltaText,
                s.Overall == "green" ? Palette.Ink : overallColor);
            stats.Controls.Add(checksCard);
            stats.Controls.Add(MiniStatCard("CERVEAU", s.Engine, Palette.Accent));
            stats.Controls.Add(MiniStatCard("DAEMON", RelativeTime(s.DaemonTs), Palette.Ink));
            stats.Controls.Add(MiniStatCard("ALERTES", s.AlertsOpen.ToString(),
                s.AlertsOpen > 0 ? Palette.Red : Palette.Ink));
            _content.Controls.Add(stats);

            // ---- repos ----
            _content.Controls.Add(Caption("REPOS SURVEILLÉS"));
            foreach (var repo in s.Repos)
            {
                var ctrl = BuildRepoRow(repo);
                ctrl.Dock = DockStyle.Top;
                _content.Controls.Add(ctrl);
                ctrl.SendToBack();
            }

            // ---- auto-actions ----
            _content.Controls.Add(Caption("AUTO-ACTIONS RÉCENTES"));
            var feedHolder = new Panel { Dock = DockStyle.Top, BackColor = Palette.Card,
                Margin = new Padding(0, 0, 0, 0), Padding = new Padding(4) };
            feedHolder.Height = s.Actions.Count > 0 ? Math.Min(170, 24 * s.Actions.Count + 8) : 32;
            if (s.Actions.Count == 0)
            {
                feedHolder.Controls.Add(new Label
                {
                    Text = "Aucune action récente — tout roule.",
                    ForeColor = Palette.Muted,
                    AutoSize = true,
                    Location = new Point(6, 7),
                    Font = new Font("Segoe UI", 8f)
                });
            }
            else
            {
                foreach (var a in s.Actions)
                {
                    var lineCtl = new ActionLine(a) { Width = Math.Max(180, _content.ClientSize.Width - 44) };
                    feedHolder.Controls.Add(lineCtl);
                }
            }
            feedHolder.Resize += delegate
            {
                foreach (Control c in feedHolder.Controls)
                    if (c is ActionLine) c.Width = Math.Max(160, feedHolder.ClientSize.Width - 12);
            };
            _content.Controls.Add(feedHolder);

            // ---- actions rapides ----
            _content.Controls.Add(Caption("ACTIONS"));
            var quick = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 2, 0, 2)
            };
            quick.Controls.Add(QuickBtn("Acquitter alertes (" + s.AlertsOpen + ")", delegate { _ackAll(); }));
            quick.Controls.Add(QuickBtn("Déclencher robot", delegate { _triggerRobot(); }));
            quick.Controls.Add(QuickBtn("Desk web", delegate { _openDesk(); }));
            _content.Controls.Add(quick);

            // ---- pied ----
            var footer = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 8, 0, 2)
            };
            footer.Controls.Add(LinkBtn("GitHub Actions ↗", delegate
            {
                try { System.Diagnostics.Process.Start("https://github.com/Lemniscate-world/kuro-rules/actions"); } catch { }
            }));
            footer.Controls.Add(LinkBtn("Journal ↗", delegate
            {
                var p = Path.Combine(@"C:\Users\Utilisateur\Documents\kuro-rules", "KURO_ACTIONS_LOG.md");
                if (File.Exists(p)) { try { System.Diagnostics.Process.Start("notepad.exe", "\"" + p + "\""); } catch { } }
            }));
            footer.Controls.Add(LinkBtn("Discord ↗", delegate
            {
                try { System.Diagnostics.Process.Start("https://discord.com/channels/@me"); } catch { }
            }));
            _content.Controls.Add(footer);

            _content.Controls.Add(new Label
            {
                Text = "Relevé : " + _lastRender.ToString("dd/MM HH:mm:ss") + " · Échap masque · F5 rafraîchit",
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 7f),
                AutoSize = true,
                Margin = new Padding(4, 2, 0, 0)
            });

            _content.ResumeLayout();
            try { _content.AutoScrollPosition = new Point(-savedX, -savedY); } catch { }
            PerformLayout();
        }

        private void OnOpenRepoActions(string url)
        {
            try { System.Diagnostics.Process.Start(url); } catch { }
        }

        private Control BuildRepoRow(RepoRow repo)
        {
            var green = repo.Health == "green";
            var row = new BufferedPanel
            {
                Height = 48,
                BackColor = Palette.Card,
                Cursor = Cursors.Hand,
                Margin = new Padding(0, 0, 0, 8),
                Tag = repo
            };
            row.Paint += delegate(object s, PaintEventArgs ev)
            {
                var p = s as Control;
                using (var pen = new Pen(Palette.Border))
                    ev.Graphics.DrawRectangle(pen, 0, 0, p.Width - 1, p.Height - 1);
            };
            var hoverColor = Palette.CardHover;
            EventHandler enter = delegate { row.BackColor = hoverColor; };
            EventHandler leave = delegate { row.BackColor = Palette.Card; };
            row.MouseEnter += enter; row.MouseLeave += leave;

            row.Click += delegate
            {
                OnOpenRepoActions("https://github.com/" + repo.Name + "/actions");
            };

            var dotColor = green ? Palette.Green : Palette.Red;
            var dot = new Label
            {
                Text = "●",
                ForeColor = dotColor,
                AutoSize = true,
                Location = new Point(12, 15),
                Font = new Font("Segoe UI", 8f),
                BackColor = Color.Transparent
            };
            row.Controls.Add(dot);
            dot.MouseEnter += enter; dot.MouseLeave += leave;
            dot.Click += delegate { OnOpenRepoActions("https://github.com/" + repo.Name + "/actions"); };

            var nameLbl = new Label
            {
                Text = repo.Name,
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI Semibold", 9.25f),
                AutoSize = true,
                Location = new Point(28, 8)
            };
            row.Controls.Add(nameLbl);
            nameLbl.MouseEnter += enter; nameLbl.MouseLeave += leave;
            nameLbl.Click += delegate { OnOpenRepoActions("https://github.com/" + repo.Name + "/actions"); };

            var detail = new Label
            {
                ForeColor = green ? Palette.Muted : Palette.Red,
                Font = new Font("Segoe UI", 7.75f),
                AutoSize = false,
                Size = new Size(row.Width - 42, 16),
                Location = new Point(28, 25)
            };
            detail.Resize += delegate { detail.Size = new Size(Math.Max(80, row.Width - 42), 16); };
            row.Controls.Add(detail);
            detail.MouseEnter += enter; detail.MouseLeave += leave;

            if (green)
            {
                detail.Text = repo.ChecksTotal + " checks OK";
                detail.Click += delegate { OnOpenRepoActions("https://github.com/" + repo.Name + "/actions"); };
            }
            else
            {
                var names = new List<string>();
                var firstUrl = "";
                foreach (var f in repo.Failing)
                {
                    names.Add(f.Name);
                    if (firstUrl == "") firstUrl = f.Url;
                }
                detail.Text = string.Join(" · ", names.ToArray());
                var tipText = string.Join("\n", names.ToArray());
                _tips.SetToolTip(detail, tipText);
                _tips.SetToolTip(nameLbl, tipText);
                if (firstUrl != "")
                {
                    detail.Cursor = Cursors.Hand;
                    var url = firstUrl;
                    detail.Click += delegate { OnOpenRepoActions(url); };
                }
            }
            return row;
        }

        private Panel MiniStatCard(string caption, string value, Color valueColor)
        {
            var card = new Panel
            {
                Dock = DockStyle.Fill,
                BackColor = Palette.Card,
                Margin = new Padding(0, 0, 8, 0),
                Padding = new Padding(9, 7, 6, 5)
            };
            card.Paint += delegate(object s, PaintEventArgs e)
            {
                var p = s as Panel;
                using (var pen = new Pen(Palette.Border))
                    e.Graphics.DrawRectangle(pen, 0, 0, p.Width - 1, p.Height - 1);
            };
            card.Controls.Add(new Label
            {
                Text = caption,
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 6.75f, FontStyle.Bold),
                AutoSize = false,
                Size = new Size(card.Width - 14, 13),
                Location = new Point(8, 7)
            });
            var val = new Label
            {
                Text = value,
                ForeColor = valueColor,
                Font = new Font("Segoe UI Semibold", 10f),
                AutoSize = false,
                Size = new Size(card.Width - 14, 24),
                Location = new Point(8, 21),
                Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
            };
            card.Controls.Add(val);
            return card;
        }

        private Button QuickBtn(string text, Action onClick)
        {
            var b = new Button
            {
                Text = text,
                FlatStyle = FlatStyle.Flat,
                BackColor = Palette.Card,
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI", 8.25f),
                AutoSize = true,
                Margin = new Padding(0, 0, 8, 0),
                Cursor = Cursors.Hand
            };
            b.FlatAppearance.BorderColor = Palette.Border;
            b.FlatAppearance.MouseOverBackColor = Palette.CardHover;
            b.FlatAppearance.BorderSize = 1;
            b.Click += delegate { onClick(); };
            return b;
        }
    }
}
