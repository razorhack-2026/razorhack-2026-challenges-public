// crew_setup.cs -- the onboarding helper's "workstation setup" tool (First Boot).
//
// Benign stand-in, never shipped: only the traces it leaves on the console do.
// Run from the ONBOARD stick, it enumerates <stick>\profiles\*.cal, reads the
// first profile and records it in the user's hive, then "weakens" the digester
// sterilization hold (the story beat). The flag is split across the two
// artifact types:
//   - head: the profile's contents (Base64), copied into
//           HKCU\Software\KOT\WasteSystems\Digester\CalProfile  (NTUSER.DAT)
//   - tail: the profile's filename (hex), which only survives in the
//           Prefetch file-reference list for CREW_SETUP.EXE
//
// Built inside the VM with the .NET Framework csc.exe (C# 5), see src/vm/build.ps1.
using System;
using System.IO;
using System.Threading;
using Microsoft.Win32;

class CrewSetup
{
    static int Main(string[] args)
    {
        string home = AppDomain.CurrentDomain.BaseDirectory;
        string dir = Path.Combine(home, "profiles");

        Console.WriteLine("KOT Waste Systems - crew workstation setup");
        Console.WriteLine("Looking for calibration profiles on " + Path.GetPathRoot(home));

        string[] found = Directory.GetFiles(dir, "*.cal");
        if (found.Length == 0)
        {
            Console.WriteLine("No calibration profile found.");
            return 1;
        }

        string profile = File.ReadAllText(found[0]).Trim();
        Console.WriteLine("Applying digester calibration profile...");

        using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"Software\KOT\WasteSystems\Digester"))
        {
            k.SetValue("CalProfile", profile, RegistryValueKind.String);
            k.SetValue("ProfileSource", "removable", RegistryValueKind.String);
            k.SetValue("SterilizeHoldSec", 0, RegistryValueKind.DWord);
        }

        // Stay alive past the prefetch trace window's first file accesses.
        Thread.Sleep(4000);
        Console.WriteLine("Done. Thanks for helping keep the KOT running!");
        Thread.Sleep(3000);
        return 0;
    }
}
