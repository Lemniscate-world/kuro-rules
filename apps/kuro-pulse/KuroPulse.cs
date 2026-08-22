// KuroPulse — application tray native (gitify-like) pour l'intelligence d'entreprise Kuro.
// Compile avec le csc.exe inclus dans Windows (.NET Framework 4.x), zéro dépendance runtime.
// UI : langage Primer devtool (R109) — fond sombre, cartes, mono pour les données.

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
        public static readonly Color Border = Color.FromArgb(48, 54, 61);
        public static readonly Color Ink = Color.FromArgb(201, 209, 217);
        public static readonly Color Muted = Color.FromArgb(139, 148, 158);
        public static readonly Color Green = Color.FromArgb(63, 185, 80);
        public static readonly Color Red = Color.FromArgb(248, 81, 73);
        public static readonly Color Accent = Color.FromArgb(88, 166, 255);

        public static Bitmap Logo(int size, Color? dotColor)
        {
            var bmp = new Bitmap(size, size);
            using (var g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                g.Clear(Color.Transparent);

                var r = size * 0.22f;
                using (var path = RoundedRect(new RectangleF(1, 1, size - 2, size - 2), r))
                using (var bg = new SolidBrush(Bg))
                using (var pen = new Pen(Border, Math.Max(1f, size / 42f)))
                    { g.FillPath(bg, path); g.DrawPath(pen, path); }

                using (var font = new Font("Segoe UI Symbol", size * 0.55f, FontStyle.Bold, GraphicsUnit.Pixel))
                using (var accent = new SolidBrush(Accent))
                using (var fmt = new StringFormat
                {
                    Alignment = StringAlignment.Center,
                    LineAlignment = StringAlignment.Center
                })
                {
                    var box = new RectangleF(0, -size * 0.05f, size, size * 1.05f);
                    g.DrawString(((char)0x03BB).ToString(), font, accent, box, fmt);
                }

                if (dotColor.HasValue)
                {
                    var d = size * 0.20f;
                    using (var dotBg = new SolidBrush(Bg))
                    using (var dot = new SolidBrush(dotColor.Value))
                    {
                        g.FillEllipse(dotBg, size - d * 1.6f - 1, size - d * 1.6f - 1, d * 1.6f + 2, d * 1.6f + 2);
                        g.FillEllipse(dot, size - d * 1.4f - 1, size - d * 1.4f - 1, d * 1.4f, d * 1.4f);
                    }
                }
            }
            return bmp;
        }

        private static GraphicsPath RoundedRect(RectangleF rect, float radius)
        {
            var path = new GraphicsPath();
            var d = radius * 2;
            path.AddArc(rect.X, rect.Y, d, d, 180, 90);
            path.AddArc(rect.Right - d, rect.Y, d, d, 270, 90);
            path.AddArc(rect.Right - d, rect.Bottom - d, d, d, 0, 90);
            path.AddArc(rect.X, rect.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    // ---------- données ----------

    internal class RobotState
    {
        public string Overall = "unknown";
        public string Engine = "déterministe";
        public string DaemonTs = "?";
        public List<string> Actions = new List<string>();
        public List<RepoRow> Repos = new List<RepoRow>();
    }

    internal class RepoRow
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

        [DllImport("dwmapi.dll")]
        private static extern void DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

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
                        var row = new RepoRow
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
            // GDI : ne jamais disposer une icône encore référencée par le tray.
            // On garde la précédente vivante et on ne libère que celle d'avant.
            var newIcon = Icon.FromHandle(Palette.Logo(16, dot).GetHicon());
            var old = _tray.Icon;
            _prevIcon = _tray.Icon;
            _tray.Icon = newIcon;
            try { if (_prevOld != null) _prevOld.Dispose(); } catch { }
            _prevOld = old;

            _tray.Text = string.Format("CI {0} | cerveau {1} | daemon {2}",
                s.Overall, s.Engine, s.DaemonTs);
        }

        private Icon _prevIcon;
        private Icon _prevOld;

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

            if (!manual && state.Actions.Count > 0 &&
                _panel != null && !_panel.IsDisposed)
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
        private DateTime _lastRender = DateTime.Now;

        [DllImport("dwmapi.dll")]
        private static extern void DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

        public KuroPanel(Action refresh, Action openDesk, Action openActions, Action openJournal)
        {
            _refresh = refresh; _openDesk = openDesk;
            _openActions = openActions; _openJournal = openJournal;

            Text = "KuroPulse";
            Size = new Size(430, 640);
            BackColor = Palette.Bg;
            ForeColor = Palette.Ink;
            StartPosition = FormStartPosition.Manual;
            var wa = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(wa.Right - Width - 16, wa.Bottom - Height - 16);
            MinimumSize = new Size(370, 480);
            Font = new Font("Segoe UI", 9f);

            _content = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = Palette.Bg,
                Padding = new Padding(14, 10, 14, 10)
            };
            Controls.Add(_content);
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            try
            {
                var one = 1;
                DwmSetWindowAttribute(Handle, 20, ref one, 4);   // barre de titre sombre (Win10+/11)
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

        private Label Caption(string text)
        {
            return new Label
            {
                Text = text,
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 7.5f, FontStyle.Bold),
                AutoSize = true,
                Margin = new Padding(3, 14, 3, 4)
            };
        }

        private Panel Card(int height)
        {
            var card = new Panel
            {
                Height = height,
                BackColor = Palette.Card,
                Margin = new Padding(0, 2, 0, 2),
                Padding = new Padding(10, 8, 10, 8)
            };
            card.Paint += delegate(object s, PaintEventArgs e)
            {
                var p = s as Panel;
                using (var pen = new Pen(Palette.Border))
                    e.Graphics.DrawRectangle(pen, 0, 0, p.Width - 1, p.Height - 1);
            };
            return card;
        }

        private Control StatCard(string caption, string value, Color valueColor)
        {
            var card = Card(56);
            card.Margin = new Padding(0, 2, 8, 2);
            card.Controls.Add(new Label
            {
                Text = caption,
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 6.75f, FontStyle.Bold),
                AutoSize = false,
                Size = new Size(card.Width - 16, 14),
                Location = new Point(10, 8)
            });
            var val = new Label
            {
                Text = value,
                ForeColor = valueColor,
                Font = new Font("Segoe UI Semibold", 11f),
                AutoSize = false,
                Size = new Size(card.Width - 16, 26),
                Location = new Point(10, 24)
            };
            card.Controls.Add(val);
            return card;
        }

        private Control RepoRowControl(RepoRow repo)
        {
            var green = repo.Health == "green";
            var row = Card(40);
            row.Padding = new Padding(10, 9, 10, 9);
            row.Cursor = Cursors.Hand;
            row.Tag = "https://github.com/" + repo.Name + "/actions";

            var dotColor = green ? Palette.Green : Palette.Red;
            row.Paint += delegate(object s, PaintEventArgs e)
            {
                using (var b = new SolidBrush(dotColor))
                    e.Graphics.FillEllipse(b, 12, 15, 9, 9);
            };

            var name = new Label
            {
                Text = repo.Name,
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI Semibold", 9.25f),
                AutoSize = true,
                Location = new Point(28, 10)
            };
            row.Controls.Add(name);

            var detailText = green
                ? repo.ChecksTotal + " checks OK"
                : (repo.Failing.Count > 0
                    ? repo.Failing.Count + " en échec : " + string.Join(", ", repo.Failing.ToArray())
                    : repo.ChecksOk + "/" + repo.ChecksTotal + " checks");

            var detail = new Label
            {
                Text = detailText,
                ForeColor = green ? Palette.Muted : Palette.Red,
                Font = new Font("Segoe UI", 7.75f),
                AutoSize = false,
                Width = row.Width - 44,
                Location = new Point(28, 23),
                MaximumSize = new Size(row.Width - 44, 0)
            };
            row.Controls.Add(detail);

            EventHandler enter = delegate { row.BackColor = Color.FromArgb(30, 36, 45); };
            EventHandler leave = delegate { row.BackColor = Palette.Card; };
            row.MouseEnter += enter; row.MouseLeave += leave;
            name.MouseEnter += enter; name.MouseLeave += leave;
            detail.MouseEnter += enter; detail.MouseLeave += leave;
            row.Click += delegate { OnOpenRepo(row.Tag as string); };
            name.Click += delegate { OnOpenRepo(row.Tag as string); };
            detail.Click += delegate { OnOpenRepo(row.Tag as string); };

            row.Resize += delegate
            {
                detail.Width = Math.Max(60, row.Width - 44);
            };
            return row;
        }

        protected virtual void OnOpenRepo(string url)
        {
            try { System.Diagnostics.Process.Start(url); } catch { }
        }

        public void Render(RobotState s)
        {
            if (InvokeRequired) { BeginInvoke((Action)delegate { Render(s); }); return; }
            if (IsDisposed) return;
            _lastRender = DateTime.Now;

            var overallColor = s.Overall == "green" ? Palette.Green
                             : s.Overall == "red" ? Palette.Red : Palette.Muted;

            _content.SuspendLayout();
            _content.Controls.Clear();

            // ---- entête : logo + titres ----
            var header = new Panel { Dock = DockStyle.Top, Height = 52, Margin = Padding.Empty };
            var logoBox = new PictureBox
            {
                Image = Palette.Logo(44, overallColor),
                Size = new Size(44, 44),
                Location = new Point(0, 2),
                SizeMode = PictureBoxSizeMode.Zoom
            };
            header.Controls.Add(logoBox);
            header.Controls.Add(new Label
            {
                Text = "KuroPulse",
                ForeColor = Palette.Ink,
                Font = new Font("Segoe UI Semibold", 15f),
                AutoSize = true,
                Location = new Point(54, 4)
            });
            header.Controls.Add(new Label
            {
                Text = "v1.0 · intelligence d'entreprise lambda-Section",
                ForeColor = Palette.Muted,
                Font = new Font("Segoe UI", 7.5f),
                AutoSize = true,
                Location = new Point(56, 32)
            });
            _content.Controls.Add(header);

            // ---- cartes stats ----
            var totalChecks = 0;
            foreach (var r in s.Repos) totalChecks += r.ChecksTotal;
            var okChecks = 0;
            foreach (var r in s.Repos)
                foreach (var w in r.Failing) { /* compteur via failing */ }
            okChecks = totalChecks;
            foreach (var r in s.Repos) okChecks -= r.Failing.Count;

            var stats = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 62,
                ColumnCount = 3,
                RowCount = 1,
                Margin = new Padding(0, 6, 0, 0)
            };
            for (int i = 0; i < 3; i++) stats.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 33.3f));

            var cChecks = StatCard("CHECKS CI", okChecks + "/" + totalChecks,
                s.Overall == "green" ? Palette.Green : s.Overall == "red" ? Palette.Red : Palette.Muted);
            var cBrain = StatCard("CERVEAU", s.Engine, Palette.Accent);
            var cDaemon = StatCard("DAEMON", RelativeTime(s.DaemonTs), Palette.Ink);
            stats.Controls.Add(cChecks); stats.Controls.Add(cBrain); stats.Controls.Add(cDaemon);
            _content.Controls.Add(stats);

            // ---- repos ----
            _content.Controls.Add(Caption("REPOS SURVEILLÉS"));
            foreach (var repo in s.Repos)
            {
                var ctrl = RepoRowControl(repo);
                ctrl.Dock = DockStyle.Top;
                _content.Controls.Add(ctrl);
                ctrl.SendToBack();
            }

            // ---- auto-actions ----
            _content.Controls.Add(Caption("AUTO-ACTIONS RÉCENTES"));
            var actionsBox = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                BackColor = Palette.Card,
                ForeColor = Palette.Ink,
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Consolas", 8f),
                Dock = DockStyle.Top,
                Height = 140,
                Margin = new Padding(0, 2, 0, 2),
                Text = s.Actions.Count > 0
                    ? string.Join(Environment.NewLine, s.Actions.ToArray())
                    : "Aucune action récente — tout roule."
            };
            _content.Controls.Add(actionsBox);

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
                Text = "Relevé : " + _lastRender.ToString("dd/MM HH:mm:ss"),
                ForeColor = Palette.Muted,
                Font = new Font("Consolas", 7f),
                AutoSize = true,
                Margin = new Padding(4, 2, 0, 0)
            });

            _content.ResumeLayout();
            PerformLayout();
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

        private Label LinkBtn(string text, Action onClick)
        {
            var l = new Label
            {
                Text = text,
                ForeColor = Palette.Accent,
                AutoSize = true,
                Margin = new Padding(0, 0, 16, 0),
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 8.75f)
            };
            l.Click += delegate { onClick(); };
            l.MouseEnter += delegate { l.ForeColor = Palette.Ink; };
            l.MouseLeave += delegate { l.ForeColor = Palette.Accent; };
            return l;
        }
    }
}
