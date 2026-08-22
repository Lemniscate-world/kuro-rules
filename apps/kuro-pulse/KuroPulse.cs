// KuroPulse — application tray native (gitify-like) pour l'intelligence d'entreprise Kuro.
// Compile avec le csc.exe inclus dans Windows (.NET Framework 4.x), zéro dépendance runtime.
// UI : langage Primer devtool (R109) — panneau sombre entièrement dessiné main.

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

    // ---------- palette Primer-dark (R109) ----------

    internal static class Palette
    {
        public static readonly Color Bg = Color.FromArgb(13, 17, 23);
        public static readonly Color Card = Color.FromArgb(22, 27, 34);
        public static readonly Color CardHover = Color.FromArgb(30, 36, 45);
        public static readonly Color Border = Color.FromArgb(48, 54, 61);
        public static readonly Color Ink = Color.FromArgb(230, 237, 243);
        public static readonly Color Muted = Color.FromArgb(139, 148, 158);
        public static readonly Color Green = Color.FromArgb(63, 185, 80);
        public static readonly Color GreenTint = Color.FromArgb(46, 160, 67, 40);
        public static readonly Color Red = Color.FromArgb(248, 81, 73);
        public static readonly Color RedTint = Color.FromArgb(248, 81, 73, 36);
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
            var bmp = new Bitmap(size * 2, size * 2);
            using (var g = Graphics.FromImage(bmp))
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
                g2.DrawImage(bmp, 0, 0, size, size);
            }
            bmp.Dispose();
            return small;
        }
    }

    // ---------- contrôles dessinés ----------

    internal class Pill : Control
    {
        public string Value = "";
        public Color Tone = Palette.Green;

        public Pill() { SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                                 ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            var toneBg = Color.FromArgb(40, Tone);
            using (var bg = new SolidBrush(toneBg))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), Height / 2f))
                e.Graphics.FillPath(bg, path);
            TextRenderer.DrawText(e.Graphics, Value, new Font("Segoe UI Semibold", 8.25f),
                new Rectangle(0, 0, Width, Height), Tone,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding);
        }
    }

    internal class RepoRow : Control
    {
        private readonly RepoRowData _d;
        private bool _hover;

        public RepoRow(RepoRowData d, string url)
        {
            _d = d;
            Height = 46;
            Cursor = Cursors.Hand;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw | ControlStyles.Selectable, true);
            Click += delegate { try { System.Diagnostics.Process.Start(url); } catch { } };
        }

        protected override void OnMouseEnter(EventArgs e) { _hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hover = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            if (_hover)
            {
                _hover = false;
            }
            using (var bg = new SolidBrush(_hover ? Palette.CardHover : Palette.Card))
            using (var path = Palette.Rounded(new RectangleF(0, 0, Width - 1, Height - 1), 6))
                g.FillPath(bg, path);

            var dotColor = _d.Health == "green" ? Palette.Green : Palette.Red;
            g.FillEllipse(new SolidBrush(dotColor), 14, Height / 2f - 4, 8, 8);

            var green = _d.Health == "green";
            TextRenderer.DrawText(g, _d.Name, new Font("Segoe UI Semibold", 9.25f),
                new Rectangle(30, 6, Width - 130, 18),
                Palette.Ink, TextFormatFlags.Left | TextFormatFlags.NoPadding);

            var rightText = green ? _d.ChecksTotal + " checks OK"
                : (_d.Failing.Count > 0 ? _d.Failing.Count + " en échec" : _d.ChecksOk + "/" + _d.ChecksTotal);
            TextRenderer.DrawText(g, rightText, new Font("Segoe UI", 8f),
                new Rectangle(Width - 120, 8, 110, 16),
                green ? Palette.Muted : Palette.Red,
                TextFormatFlags.Right | TextFormatFlags.NoPadding);

            if (!green && _d.Failing.Count > 0)
            {
                var names = string.Join(" · ", _d.Failing.ToArray());
                TextRenderer.DrawText(g, names, new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 25, Width - 42, 15),
                    Palette.Muted, TextFormatFlags.Left | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
            }
            else
            {
                TextRenderer.DrawText(g, "tous les checks passent", new Font("Segoe UI", 7.5f),
                    new Rectangle(30, 25, Width - 42, 15),
                    Color.FromArgb(90, Palette.Muted), TextFormatFlags.Left | TextFormatFlags.NoPadding);
            }
        }
    }

    internal class ActionRow : Control
    {
        private readonly string _line;

        public ActionRow(string line)
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
            // format : ts | type | cible | détail
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

    // ---------- données ----------

    internal class RobotState
    {
        public string Overall = "unknown";
        public string Engine = "déterministe";
        public string DaemonTs = "?";
        public List<string> Actions = new List<string>();
        public List<RepoRowData> Repos = new List<RepoRowData>();
    }

    internal class RepoRowData
    {
        public string Name;
        public string Health;
        public int ChecksOk;
        public int ChecksTotal;
        public List<string> Failing = new List<string>();
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
            menu.Items.Add("GitHub Actions", null,
                delegate { OpenUrl("https://github.com/Lemniscate-world/kuro-rules/actions"); });
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
                        var row = new RepoRowData
                        {
                            Name = Str(rd, "name"),
                            Health = Str(rd, "health"),
                            ChecksOk = Int(rd, "checks_ok"),
                            ChecksTotal = Int(rd, "checks_total"),
                            Failing = new List<string>()
                        };
                        object fails;
                        if (rd.TryGetValue("failing", out fails) && fails != null)
                            foreach (var f in (System.Collections.IEnumerable)fails)
                                row.Failing.Add(f.ToString());
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
            var newIcon = Icon.FromHandle(Palette.Logo(16, dot).GetHicon());
            _tray.Icon = newIcon;
            _tray.Text = string.Format("CI {0} | cerveau {1} | daemon {2}",
                s.Overall, s.Engine, s.DaemonTs);
        }

        private void FetchState(bool manual)
        {
            RobotState state;
            try { state = Fetch(); }
            catch
            {
                SetTray(new RobotState { Overall = "unknown" });
                _tray.Text = "KuroPulse : API injoignable";
                if (_panel != null && !_panel.IsDisposed) _panel.UpdateError();
                return;
            }

            var previousActions = _last.Actions.Count;
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

        private void ShowPanel()
        {
            if (_panel == null || _panel.IsDisposed)
            {
                _panel = new KuroPanel(
                    delegate { FetchState(true); },
                    delegate { OpenUrl(ApiBase + "/"); },
                    delegate { OpenUrl("https://github.com/Lemniscate-world/kuro-rules/actions"); },
                    delegate { OpenJournal(); });
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
        private readonly Action _refresh;
        private readonly Action _openDesk;
        private readonly Action _openActions;
        private readonly Action _openJournal;

        private readonly Panel _content;
        private readonly FlowLayoutPanel _feed;
        private DateTime _lastRender = DateTime.Now;

        [DllImport("dwmapi.dll")]
        private static extern void DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

        public KuroPanel(Action refresh, Action openDesk, Action openActions, Action openJournal)
        {
            _refresh = refresh; _openDesk = openDesk;
            _openActions = openActions; _openJournal = openJournal;

            Text = "KuroPulse";
            Size = new Size(440, 700);
            BackColor = Palette.Bg;
            ForeColor = Palette.Ink;
            StartPosition = FormStartPosition.Manual;
            var wa = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(wa.Right - Width - 16, wa.Bottom - Height - 16);
            MinimumSize = new Size(380, 520);
            Font = new Font("Segoe UI", 9f);

            _content = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = Palette.Bg,
                Padding = new Padding(16, 12, 16, 12)
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

        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            if (keyData == Keys.Escape) { Hide(); return true; }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; Hide(); return; }
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
            return new Label
            {
                Text = text,
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f, FontStyle.Bold),
                AutoSize = true,
                Margin = new Padding(3, 16, 3, 6)
            };
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

            var overallColor = s.Overall == "green" ? Palette.Green
                             : s.Overall == "red" ? Palette.Red : Palette.Muted;

            _content.SuspendLayout();
            _content.Controls.Clear();

            // ---- entête ----
            var header = new Panel { Dock = DockStyle.Top, Height = 56, Margin = Padding.Empty };
            var logoBox = new PictureBox
            {
                Image = Palette.Logo(46, overallColor),
                Size = new Size(46, 46),
                Location = new Point(0, 3),
                SizeMode = PictureBoxSizeMode.Zoom
            };
            header.Controls.Add(logoBox);
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
                Text = "v1.1 · intelligence d'entreprise lambda-Section",
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f),
                AutoSize = true,
                Location = new Point(60, 33)
            });
            _content.Controls.Add(header);

            // ---- pilule état global ----
            var pill = new Pill
            {
                Value = s.Overall == "green" ? "TOUS LES CHECKS SONT VERTS"
                      : s.Overall == "red" ? "CHECKS EN ÉCHEC" : "ÉTAT INCONNU",
                Tone = s.Overall == "green" ? Palette.Green : s.Overall == "red" ? Palette.Red : Palette.Muted,
                Width = 220, Height = 26,
                Margin = new Padding(2, 8, 0, 4)
            };
            _content.Controls.Add(pill);

            // ---- stats ----
            var totalChecks = 0;
            foreach (var r in s.Repos) totalChecks += r.ChecksTotal;
            var okChecks = totalChecks;
            foreach (var r in s.Repos) okChecks -= r.Failing.Count;

            var grid = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 58,
                ColumnCount = 3,
                RowCount = 1,
                Margin = new Padding(0, 4, 0, 0)
            };
            for (int i = 0; i < 3; i++) grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 33.3f));
            grid.Controls.Add(MiniStat("CHECKS CI", okChecks + "/" + totalChecks,
                s.Overall == "green" ? Palette.Ink : overallColor));
            grid.Controls.Add(MiniStat("CERVEAU", s.Engine, Palette.Accent));
            grid.Controls.Add(MiniStat("DAEMON", RelativeTime(s.DaemonTs), Palette.Ink));
            _content.Controls.Add(grid);

            // ---- repos ----
            _content.Controls.Add(Caption("REPOS SURVEILLÉS"));
            foreach (var repo in s.Repos)
            {
                var row = new RepoRow(repo, "https://github.com/" + repo.Name + "/actions")
                {
                    Dock = DockStyle.Top,
                    Margin = new Padding(0, 0, 0, 6)
                };
                _content.Controls.Add(row);
            }

            // ---- auto-actions ----
            _content.Controls.Add(Caption("AUTO-ACTIONS RÉCENTES"));
            _feed.Controls.Clear();
            if (s.Actions.Count == 0)
            {
                var empty = new Label
                {
                    Text = "Aucune action récente — tout roule.",
                    ForeColor = Palette.Muted,
                    AutoSize = true,
                    Margin = new Padding(4, 3, 4, 3),
                    Font = new Font("Segoe UI", 8f)
                };
                _feed.Controls.Add(empty);
            }
            else
            {
                foreach (var a in s.Actions)
                    _feed.Controls.Add(new ActionRow(a) { Width = Math.Max(200, _content.ClientSize.Width - 40) });
            }
            _content.Controls.Add(_feed);

            // ---- pied ----
            var footer = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 10, 0, 2)
            };
            footer.Controls.Add(LinkBtn("Desk ↗", delegate { _openDesk(); }));
            footer.Controls.Add(LinkBtn("GitHub Actions ↗", delegate { _openActions(); }));
            footer.Controls.Add(LinkBtn("Journal ↗", delegate { _openJournal(); }));
            footer.Controls.Add(LinkBtn("Rafraîchir", delegate { _refresh(); }));
            _content.Controls.Add(footer);

            _content.Controls.Add(new Label
            {
                Text = "Relevé : " + DateTime.Now.ToString("dd/MM HH:mm:ss"),
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 7f),
                AutoSize = true,
                Margin = new Padding(4, 2, 0, 0)
            });

            _content.ResumeLayout();
            PerformLayout();
        }

        private Panel MiniStat(string caption, string value, Color valueColor)
        {
            var card = new Panel { Dock = DockStyle.Fill, BackColor = Palette.Card, Padding = new Padding(10, 8, 6, 6), Margin = new Padding(0, 0, 8, 0) };
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
                AutoSize = true,
                Location = new Point(8, 7)
            });
            var val = new Label
            {
                Text = value,
                ForeColor = valueColor,
                Font = new Font("Segoe UI Semibold", 10.5f),
                AutoSize = false,
                Size = new Size(card.Width - 12, 24),
                Location = new Point(8, 23),
                Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
            };
            card.Controls.Add(val);
            return card;
        }
    }
}
