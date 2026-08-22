// KuroPulse — application tray native (gitify-like) pour l'intelligence d'entreprise Kuro.
// Compile avec le csc.exe inclus dans Windows (.NET Framework 4.x), zéro dépendance runtime.
// UI : langage Primer devtool (R109) — fond sombre, mono pour les données.

using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Net;
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

    internal class RobotState
    {
        public bool Ok;
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
        public List<string> Failing;
    }

    internal class TrayContext : ApplicationContext
    {
        private const string ApiBase = "http://127.0.0.1:8767";
        private const string KuroRoot = @"C:\Users\Utilisateur\Documents\kuro-rules";

        private readonly NotifyIcon _tray;
        private KuroPanel _panel;
        private RobotState _last = new RobotState();
        private string _lastOverall;
        private int _lastActionCount = -1;
        private DateTime _lastApiStart = DateTime.MinValue;

        public TrayContext()
        {
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;

            _tray = new NotifyIcon
            {
                Icon = MakeIcon(Color.Gray),
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

        // ---------- réseau ----------

        private void EnsureApi()
        {
            try
            {
                using (var wc = new WebClient())
                {
                    wc.DownloadString(ApiBase + "/api/status");
                }
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
                var json = wc.DownloadString(ApiBase + "/api/robot?ts=" +
                                             DateTime.UtcNow.Ticks);
                var ser = new JavaScriptSerializer { MaxJsonLength = 1 << 26 };
                var data = ser.Deserialize<Dictionary<string, object>>(json);

                var state = new RobotState { Ok = true };
                object tmp;
                if (data.TryGetValue("ci_overall", out tmp) && tmp != null)
                {
                    state.Overall = tmp.ToString();
                }

                if (data.TryGetValue("llm_engine", out tmp) && tmp != null)
                    state.Engine = tmp.ToString();

                if (data.TryGetValue("daemon", out tmp))
                {
                    var daemon = tmp as Dictionary<string, object>;
                    if (daemon != null && daemon.ContainsKey("timestamp"))
                        state.DaemonTs = Trim10(daemon["timestamp"].ToString());
                }

                if (data.TryGetValue("actions_tail", out tmp) && tmp != null)
                {
                    foreach (var a in (System.Collections.IEnumerable)tmp)
                    {
                        var line = Clean(a.ToString());
                        if (!line.StartsWith("scan") && !line.Contains("| scan "))
                            state.Actions.Add(line);
                    }
                }

                if (data.TryGetValue("repos", out tmp) && tmp != null)
                {
                    foreach (var r in (System.Collections.IEnumerable)tmp)
                    {
                        var rd = r as Dictionary<string, object>;
                        if (rd == null) continue;
                        var row = new RepoRow
                        {
                            Name = Str(rd, "name"),
                            Health = Str(rd, "health"),
                            ChecksOk = Int(rd, "checks_ok"),
                            ChecksTotal = Int(rd, "checks_total")
                        };
                        row.Failing = new List<string>();
                        object fails;
                        if (rd.TryGetValue("failing", out fails) && fails != null)
                            foreach (var f in (System.Collections.IEnumerable)fails)
                                row.Failing.Add(f.ToString());
                        state.Repos.Add(row);
                    }
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

        // ---------- cycle principal ----------

        private void FetchState(bool manual)
        {
            RobotState state;
            try { state = Fetch(); }
            catch
            {
                _tray.Icon = MakeIcon(Color.Gray);
                _tray.Text = "KuroPulse : API injoignable";
                if (_panel != null && !_panel.IsDisposed)
                    _panel.UpdateError();
                return;
            }

            var previous = _last;
            _last = state;

            var dot = state.Overall == "green" ? Color.FromArgb(63, 185, 80)
                    : state.Overall == "red" ? Color.FromArgb(248, 81, 73)
                    : Color.Gray;
            _tray.Icon = MakeIcon(dot);
            _tray.Text = string.Format("CI {0} | cerveau {1} | daemon {2}",
                state.Overall, state.Engine, state.DaemonTs);

            if (_panel != null && !_panel.IsDisposed)
                _panel.Render(state);

            if (!manual && _lastOverall != null && _lastOverall != state.Overall)
            {
                _tray.BalloonTipTitle = "KuroPulse — CI " + state.Overall.ToUpper();
                _tray.BalloonTipText = state.Overall == "red"
                    ? "Des checks sont passés en rouge."
                    : "Tous les checks sont au vert.";
                _tray.ShowBalloonTip(8000);
            }
            _lastOverall = state.Overall;

            if (!manual && previous.Actions.Count > 0 &&
                state.Actions.Count > _lastActionCount && _lastActionCount >= 0)
            {
                _tray.BalloonTipTitle = "KuroPulse — auto-action";
                _tray.BalloonTipText = state.Actions[state.Actions.Count - 1];
                _tray.ShowBalloonTip(8000);
            }
            _lastActionCount = state.Actions.Count;
        }

        // ---------- panneau ----------

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

        // ---------- utilitaires ----------

        private void OpenUrl(string url)
        {
            try { System.Diagnostics.Process.Start(url); } catch { }
        }

        private void OpenJournal()
        {
            var path = Path.Combine(KuroRoot, "KURO_ACTIONS_LOG.md");
            if (File.Exists(path)) System.Diagnostics.Process.Start("notepad.exe", path);
        }

        private void ExitApp()
        {
            _tray.Visible = false;
            Application.Exit();
        }

        private Icon MakeIcon(Color color)
        {
            using (var bmp = new Bitmap(16, 16))
            using (var g = Graphics.FromImage(bmp))
            {
                g.Clear(Color.Transparent);
                using (var b = new SolidBrush(color))
                    g.FillEllipse(b, 2, 2, 12, 12);
                using (var pen = new Pen(Color.FromArgb(48, 48, 48)))
                    g.DrawEllipse(pen, 2, 2, 12, 12);
                return Icon.FromHandle(bmp.GetHicon());
            }
        }
    }

    internal class KuroPanel : Form
    {
        private static readonly Color Bg = Color.FromArgb(13, 17, 23);
        private static readonly Color Card = Color.FromArgb(22, 27, 34);
        private static readonly Color Border = Color.FromArgb(48, 54, 61);
        private static readonly Color Ink = Color.FromArgb(201, 209, 217);
        private static readonly Color Muted = Color.FromArgb(139, 148, 158);
        private static readonly Color Green = Color.FromArgb(63, 185, 80);
        private static readonly Color Red = Color.FromArgb(248, 81, 73);
        private static readonly Color Accent = Color.FromArgb(88, 166, 255);

        private readonly Action _refresh;
        private readonly Action _openDesk;
        private readonly Action _openActions;
        private readonly Action _openJournal;

        private readonly Panel _content;

        public KuroPanel(Action refresh, Action openDesk, Action openActions, Action openJournal)
        {
            _refresh = refresh; _openDesk = openDesk;
            _openActions = openActions; _openJournal = openJournal;

            Text = "KuroPulse";
            Size = new Size(420, 620);
            BackColor = Bg;
            ForeColor = Ink;
            StartPosition = FormStartPosition.Manual;
            var wa = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(wa.Right - Width - 16, wa.Bottom - Height - 16);
            MinimumSize = new Size(360, 460);
            Font = new Font("Segoe UI", 9f);

            _content = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = Bg,
                Padding = new Padding(14, 10, 14, 10)
            };
            Controls.Add(_content);
        }

        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            if (keyData == Keys.Escape) { Hide(); return true; }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing)
            {
                e.Cancel = true;
                Hide();
                return;
            }
            base.OnFormClosing(e);
        }

        public void UpdateError()
        {
            _content.Controls.Clear();
            var l = new Label
            {
                Text = "API Kuro injoignable.\nElle redémarre automatiquement.",
                ForeColor = Muted, AutoSize = true, Padding = new Padding(8)
            };
            _content.Controls.Add(l);
        }

        private Label SectionLabel(string text)
        {
            return new Label
            {
                Text = text,
                ForeColor = Muted,
                Font = new Font("Consolas", 7.5f, FontStyle.Bold),
                AutoSize = true,
                Margin = new Padding(3, 12, 3, 4)
            };
        }

        public void Render(RobotState s)
        {
            if (InvokeRequired) { BeginInvoke((Action)delegate { Render(s); }); return; }
            if (IsDisposed) return;

            _content.SuspendLayout();
            _content.Controls.Clear();

            var header = new Label
            {
                Text = "● KuroPulse",
                ForeColor = s.Overall == "green" ? Green : s.Overall == "red" ? Red : Muted,
                Font = new Font("Segoe UI Semibold", 15f),
                AutoSize = true,
                Margin = new Padding(0, 0, 0, 2)
            };
            _content.Controls.Add(header);

            _content.Controls.Add(new Label
            {
                Text = "intelligence d'entreprise lambda-Section",
                ForeColor = Muted,
                Font = new Font("Segoe UI", 8f),
                AutoSize = true,
                Margin = new Padding(2, 0, 0, 8)
            });

            var status = new Label
            {
                Text = string.Format("CI {0} · cerveau {1} · daemon {2}",
                    s.Overall, s.Engine, s.DaemonTs),
                ForeColor = Ink,
                BackColor = Card,
                Padding = new Padding(8, 6, 8, 6),
                AutoSize = true,
                Margin = new Padding(0, 2, 0, 4)
            };
            status.Paint += delegate(object sender, PaintEventArgs e)
            {
                var p = sender as Label;
                e.Graphics.DrawRectangle(new Pen(Border), 0, 0, p.Width - 1, p.Height - 1);
            };
            _content.Controls.Add(status);

            _content.Controls.Add(SectionLabel("REPOS"));
            foreach (var repo in s.Repos)
            {
                var green = repo.Health == "green";
                var bullet = new Label
                {
                    Text = green ? "●" : "●",
                    ForeColor = green ? Green : Red,
                    AutoSize = true,
                    Font = new Font("Segoe UI", 9.5f),
                    Margin = new Padding(4, 3, 0, 0),
                    Width = 20
                };
                _content.Controls.Add(bullet);

                var detail = green
                    ? string.Format("{0} checks OK", repo.ChecksTotal)
                    : (repo.Failing.Count > 0
                        ? string.Join(", ", repo.Failing.ToArray())
                        : string.Format("{0}/{1} checks", repo.ChecksOk, repo.ChecksTotal));

                var nameLbl = new Label
                {
                    Text = repo.Name,
                    ForeColor = Ink,
                    AutoSize = true,
                    Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                    Margin = new Padding(0, 3, 4, 0)
                };
                _content.Controls.Add(nameLbl);

                _content.Controls.Add(new Label
                {
                    Text = detail,
                    ForeColor = green ? Muted : Red,
                    AutoSize = true,
                    Font = new Font("Segoe UI", 8f),
                    Margin = new Padding(18, 0, 0, 6)
                });
            }

            _content.Controls.Add(SectionLabel("AUTO-ACTIONS RÉCENTES"));
            if (s.Actions.Count == 0)
            {
                _content.Controls.Add(new Label
                {
                    Text = "Aucune action récente — tout roule.",
                    ForeColor = Muted,
                    AutoSize = true,
                    Margin = new Padding(6, 2, 0, 2)
                });
            }
            else
            {
                var box = new TextBox
                {
                    Multiline = true,
                    ReadOnly = true,
                    ScrollBars = ScrollBars.Vertical,
                    BackColor = Card,
                    ForeColor = Muted,
                    BorderStyle = BorderStyle.FixedSingle,
                    Font = new Font("Consolas", 8f),
                    Dock = DockStyle.Top,
                    Height = 150,
                    Margin = new Padding(4, 2, 4, 2),
                    Text = string.Join(Environment.NewLine, s.Actions.ToArray())
                };
                _content.Controls.Add(box);
            }

            var footer = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 10, 0, 4)
            };
            footer.Controls.Add(LinkBtn("Desk ↗", delegate { _openDesk(); }));
            footer.Controls.Add(LinkBtn("GitHub Actions ↗", delegate { _openActions(); }));
            footer.Controls.Add(LinkBtn("Journal ↗", delegate { _openJournal(); }));
            footer.Controls.Add(LinkBtn("Rafraîchir", delegate { _refresh(); }));
            _content.Controls.Add(footer);

            _content.ResumeLayout();
            PerformLayout();
        }

        private Label LinkBtn(string text, Action onClick)
        {
            var l = new Label
            {
                Text = text,
                ForeColor = Accent,
                AutoSize = true,
                Margin = new Padding(0, 0, 16, 0),
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 8.75f)
            };
            l.Click += delegate { onClick(); };
            l.MouseEnter += delegate { l.ForeColor = Ink; };
            l.MouseLeave += delegate { l.ForeColor = Accent; };
            return l;
        }
    }
}
