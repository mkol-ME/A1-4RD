// Double-click launcher for a client script (client/listen.py to talk,
// client/chat.py to type), so reaching Alfred does not start with a PowerShell
// prompt. Built by build.ps1 with the stock .NET Framework compiler that ships
// with Windows; nothing to install. The script and window title are baked in
// at build time, so this one source makes both exes.
//
// Finds the project from the path baked in at build time, or failing that by
// walking up from wherever the exe sits, then runs the project's own venv in
// this console window. Any arguments are passed through: Alfred.exe --open.

using System;
using System.Diagnostics;
using System.IO;
using System.Linq;

static class Alfred
{
    static string FindProject()
    {
        if (IsProject(BuildInfo.ProjectDir))
            return BuildInfo.ProjectDir;
        var dir = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        for (; dir != null; dir = dir.Parent)
            if (IsProject(dir.FullName))
                return dir.FullName;
        return null;
    }

    static bool IsProject(string dir)
    {
        return !string.IsNullOrEmpty(dir)
            && File.Exists(Path.Combine(dir, BuildInfo.Script))
            && File.Exists(Path.Combine(dir, ".venv-tts", "Scripts", "python.exe"));
    }

    static string Quote(string arg)
    {
        return arg.Length > 0 && arg.IndexOfAny(new[] { ' ', '\t', '"' }) < 0
            ? arg : "\"" + arg.Replace("\"", "\\\"") + "\"";
    }

    static int Fail(string message)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine(message);
        Console.ResetColor();
        Console.WriteLine("Press Enter to close.");
        Console.ReadLine();
        return 1;
    }

    static int Main(string[] args)
    {
        Console.Title = BuildInfo.Title;
        string script = Path.GetFileName(BuildInfo.Script);
        string project = FindProject();
        if (project == null)
            return Fail("Could not find the A1-4RD project (" + BuildInfo.Script + " and .venv-tts).\n"
                      + "Rebuild with client\\launcher\\build.ps1 if the folder has moved.");

        var start = new ProcessStartInfo
        {
            FileName = Path.Combine(project, ".venv-tts", "Scripts", "python.exe"),
            Arguments = string.Join(" ", new[] { BuildInfo.Script }.Concat(args.Select(Quote))),
            WorkingDirectory = project,
            UseShellExecute = false,   // share this console, so Ctrl+C and output behave normally
        };
        // Ctrl+C reaches the script too. Stay alive until it has shut down cleanly
        // (tunnels closed), instead of vanishing and leaving it half-stopped.
        Console.CancelKeyPress += (sender, e) => e.Cancel = true;

        try
        {
            using (var client = Process.Start(start))
            {
                client.WaitForExit();
                // 0 is a normal goodbye; Ctrl+C in Python exits with 0xC000013A.
                if (client.ExitCode == 0 || client.ExitCode == unchecked((int)0xC000013A))
                    return 0;
                // Anything else has already said its piece on this console -- its own
                // message, or a traceback. Hold the window open so it can be read
                // instead of talking over it in red.
                Console.WriteLine();
                Console.WriteLine(script + " stopped (exit code " + client.ExitCode + "). Press Enter to close.");
                Console.ReadLine();
                return client.ExitCode;
            }
        }
        catch (Exception error)
        {
            return Fail("Could not start " + script + ": " + error.Message);
        }
    }
}
