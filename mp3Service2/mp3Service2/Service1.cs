using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.ServiceProcess;
using System.Text.RegularExpressions;
using System.Globalization;
using log4net;
using System.Diagnostics;
using mp3Service;

[assembly: log4net.Config.XmlConfigurator(ConfigFile = "Log4Net.config", Watch = true)]

namespace mp3Service2
{
    public partial class mp3Service2 : ServiceBase
    {
        private System.Timers.Timer timer;

        public string BasePath = Config.BasePath;
        public string NetworkPath = Config.NetworkPath;
        public string LocalPath = Config.LocalPath;
        public Int32 PollInterval = Convert.ToInt32(Config.PollInterval);
        public string IncludeShare = Config.IncludeShare;
        public string DesktopPath = Config.DesktopPath;
        public UInt32 bpm;
        public string fileversion = "v1.1.0.4";

        private string bugPath = "";

        private const string _copiedFileList = "copiedList.txt";

        private List<string> mCurrentFileList = new List<string>();

        //Regex strings
        string RegexPattern1 = @"--";
        string RegexPattern2 = @"[_]{1,}";
        string RegexPattern4 = @"^[a-cA-C0-9]{1,3}[\s-_\.]+";
        string RegexPattern5 = @"(\()*(_-\s)*(www\.*)*-*[a-zA-Z0-9\(\-]+\.[\[\(]*(net|com|org|ru)+[\)\]*[\d]*";
        string RegexPattern6 = @"(?!\)-)[-_\)]+[a-zA-Z0-9]{2,3}\.";
        string RegexPattern7 = @"[-_]*siberia";
        //string RegexPattern3 = @"(?!p3)((^[a-zA-Z0-9]{2})+[\s-_]+?)*";

        //Replace strings
        string RegexReplace1 = " - ";
        string RegexReplace2 = " ";
        string RegexReplace4 = "";      
        string RegexReplace5 = "";
        string RegexReplace6 = ".";
        string RegexReplace7 = "";


        public mp3Service2()
        {
            log4net.Config.XmlConfigurator.Configure();
        }

        protected override void OnStart(string[] args)
        {
            ILog Log = LogManager.GetLogger(System.Reflection.MethodBase.GetCurrentMethod().DeclaringType);

            try
            {
                if (!Directory.Exists(BasePath))
                {
                    Directory.CreateDirectory(BasePath);
                    Log.Info("Creating... " + BasePath);
                }
                if (!Directory.Exists(LocalPath))
                {
                    Directory.CreateDirectory(LocalPath);
                    Log.Info("Creating... " + LocalPath);
                }
                if (!Directory.Exists(DesktopPath))
                {
                    Directory.CreateDirectory(DesktopPath);
                    Log.Info("Creating... " + DesktopPath);
                }

                if (IncludeShare.Equals("true", StringComparison.InvariantCultureIgnoreCase))
                {
                    DirectoryInfo di = new DirectoryInfo(NetworkPath);
                    bool networkExists = di.Exists;

                    if (!networkExists)
                    {
                        Directory.CreateDirectory(NetworkPath);
                        Log.Info("Creating... " + NetworkPath);
                    }
                }

                RemoveDirectories(BasePath);
                ProcessMP3();

                timer = new System.Timers.Timer(PollInterval);
                timer.AutoReset = true;
                timer.Enabled = true;
                timer.Elapsed += new System.Timers.ElapsedEventHandler(ProcessFolder);
                timer.Start();

                Log.Info("");
                Log.Info(" -- MP3 Service started -- " + fileversion);
                Log.Info("");
            }
            catch (Exception ex)
            {
                Log.Error(ex.Message);
            }
        }

        //Handle null performers array
        public static string[] InitPerformers(string[] value)
        {
            if (value == null)
            {
                return new[] { String.Empty };
            }
            return value;
        }
        private void ProcessFolder(object sender, System.Timers.ElapsedEventArgs e)
        {
            RemoveDirectories(BasePath);
            ProcessMP3();
        }

        private void ProcessMP3()
        {
            ILog Log = LogManager.GetLogger(System.Reflection.MethodBase.GetCurrentMethod().DeclaringType);


            var fileArr = Directory.GetFiles(BasePath, "*.*", SearchOption.AllDirectories)
                                   .Where(s => s.EndsWith(".mp3") || s.EndsWith(".m4a") || s.ToLower().EndsWith(".wav")
                                       || s.ToLower().EndsWith(".aif") || s.ToLower().EndsWith(".aiff") || s.ToLower().EndsWith(".flac")).ToArray();

            string copiedFileList = BasePath + "\\" + _copiedFileList;

            if (!File.Exists(copiedFileList))
            {
                File.Create(copiedFileList);
            }

            #region update current list

            try
            {
                foreach (var file in fileArr)
                {
                    if (!mCurrentFileList.Contains(file))
                        mCurrentFileList.Add(file);
                }
                var curEntries = File.ReadAllLines(copiedFileList);
                List<string> memCopyListtxt = new List<string>(curEntries);

                var fs = new FileStream(copiedFileList, FileMode.OpenOrCreate, FileAccess.Write);
                var mStreamWriter = new StreamWriter(fs);
                mStreamWriter.BaseStream.Seek(0, SeekOrigin.End);

                foreach (string file in mCurrentFileList)
                {
                    if (!file.Contains("INCOMPLETE~") && !memCopyListtxt.Contains(file))
                    {
                        memCopyListtxt.Add(file);
                        mStreamWriter.WriteLine(file);
                    }
                }
                mStreamWriter.Flush();
                mStreamWriter.Close();
            }
            catch (Exception ex)
            {
                Log.Error(string.Format("GetFiles error: {0}", ex.Message));
            }

            #endregion

            foreach (var file in fileArr)
            {
                string fileName = Path.GetFileName(file);
                string tagArtist = "";
                string tagTitle = "";
                string tempRegFilename = fileName;
                string title = "";
                Process consoleBpmProcess = getProcessInfo("consolebpm.exe");

                tempRegFilename = regexFilename(tempRegFilename, ".mp3");

                if (!file.Contains("INCOMPLETE~"))
                {
                    Log.Info("");
                    Log.Info("---------------------------------------------------------------");
                    Log.Info("PROCESSING: " + fileName);

                    try
                    {
                        //Get BPM
                        string bpmVal;

                        consoleBpmProcess.StartInfo.Arguments = "\"" + file + "\"";
                        consoleBpmProcess.Start();
                        bpmVal = consoleBpmProcess.StandardOutput.ReadLine();
                        consoleBpmProcess.WaitForExit();
                        Log.Info("BPM Detected: " + bpmVal);

                        //Apply to tag
                        TagLib.File mp3tag = TagLib.File.Create(file);

                        if (mp3tag.Tag.BeatsPerMinute.ToString().Length > 1)
                        {
                            if (mp3tag.Tag.BeatsPerMinute > 65 && mp3tag.Tag.BeatsPerMinute < 135)
                            {
                                bpm = mp3tag.Tag.BeatsPerMinute;
                                Log.Info("ID3 BPM: " + bpm);
                                Log.Info("Tag BPM OK");
                            }
                            else
                            {
                                Log.Warn("Tag BPM out of range");
                            }
                        }
                        else
                        {
                            //Cast to UInt and set tag
                            Log.Info("Tag BPM missing...");
                            double d = Convert.ToDouble(bpmVal);
                            int i = (int)Math.Round(d, 0);
                            uint newBpm = Convert.ToUInt32(i);
                            mp3tag.Tag.BeatsPerMinute = newBpm;
                            Log.Info("Setting new BPM: " + "[" + mp3tag.Tag.BeatsPerMinute.ToString() + "]");
                            mp3tag.Save();
                        }

                        if (mp3tag.Tag.Title != null && mp3tag.Tag.Title.Length > 1)
                        {
                            title = mp3tag.Tag.Title;
                        }
                        else
                        {
                            mp3tag.Tag.Title = String.Empty;
                        }

                        if (mp3tag.Tag.Performers.Length < 1 || mp3tag.Tag.Performers == null)
                        {
                            mp3tag.Tag.Performers = new[] { string.Empty };
                            mp3tag.Save();
                        }

                        if (mp3tag.Tag.Performers.Length > 0)
                        {
                            if (mp3tag.Tag.Performers != null && mp3tag.Tag.Performers[0].Length > 1)
                            {
                                string[] performers = mp3tag.Tag.Performers;

                                if (title.Length > 2 && performers[0].Length > 1)
                                {
                                    tagTitle = title;
                                    tagArtist = performers[0].ToString();
                                    Log.Info("ID3 Artist: " + "[" + tagArtist + "]");
                                    Log.Info("ID3 Title: " + "[" + tagTitle + "]");
                                    Log.Info("Tag data OK");
                                }
                            }
                        }
                        //Get artist from filename
                        if (mp3tag.Tag.Performers.Length < 1 || string.IsNullOrEmpty(mp3tag.Tag.Performers[0]))
                        {
                            mp3tag.Tag.Performers = new[] { String.Empty };
                            string prevArtist = string.Empty;

                            if (tempRegFilename.Contains("-"))
                            {
                                Log.Info("Artist data missing...");
                                string[] words = tempRegFilename.Split('-');
                                //Title
                                string lastWord = words.Last();
                                //Artist?

                                {
                                    words[0] = words[0].Trim();
                                    string perf = words[0];
                                    mp3tag.Tag.Performers = new[] { perf };
                                    Log.Info("Artists changed from \'" + prevArtist + "\' to " + "'" + perf + "'");
                                    mp3tag.Save();
                                }
                            }
                            mp3tag.Save();
                        }

                        // Get title from filename
                        if (mp3tag.Tag.Title == null || title.Length < 2)
                        {
                            mp3tag.Tag.Title = "";

                            if (tempRegFilename.Contains("-"))
                            {
                                Log.Info("Title data missing...");
                                string[] words = tempRegFilename.Split('-');
                                {
                                    string prevTitle = mp3tag.Tag.Title;
                                    mp3tag.Tag.Title = words[1].Trim();
                                    Log.Info("Title changed from \'" + prevTitle + "\' to " + "'" + words[1].Trim() + "'");
                                }
                            }
                            mp3tag.Tag.AlbumArtists = new[] { string.Empty };
                            mp3tag.Tag.Composers = new[] { string.Empty };
                            mp3tag.Tag.Comment = string.Empty;
                            mp3tag.Tag.Grouping = string.Empty;
                            mp3tag.Save();
                        }
                        mp3tag.Dispose();
                    }

                    catch (Exception ex)
                    {
                        Log.Error("TAG EXCEPTION: " + ex.Message + "Data: " + "'" + ex.StackTrace + "'" + " for " + fileName + "\r\n" + ex.HelpLink);
                    }

                    try
                    {
                        if (!file.Contains("INCOMPLETE~"))
                        {
                            string tempExt = "";

                            if (file.ToLower().Contains(".mp3"))
                            {
                                tempExt = ".mp3";
                                fileName = regexFilename(fileName, tempExt);
                            }
                            if (file.ToLower().Contains(".m4a"))
                            {
                                tempExt = ".m4a";
                                fileName = regexFilename(fileName, tempExt);
                            }
                            if (file.ToLower().Contains(".wav"))
                            {
                                tempExt = ".wav";
                                fileName = regexFilename(fileName, tempExt);
                            }
                            if (file.ToLower().Contains(".aif"))
                            {
                                tempExt = ".aif";
                                fileName = regexFilename(fileName, tempExt);
                            }
                            if (file.ToLower().Contains(".aiff"))
                            {
                                tempExt = ".aiff";
                                fileName = regexFilename(fileName, tempExt);
                            }
                            if (file.ToLower().Contains(".flac"))
                            {
                                tempExt = ".flac";
                                fileName = regexFilename(fileName, tempExt);
                            }

                            if (tagArtist.Length > 2 && tagTitle.Length > 2)
                                if (!tagArtist.Contains(@"."))
                                {
                                    string tagFull = tagArtist + " - " + tagTitle;
                                    tagFull = regexFilename(tagFull, tempExt);
                                    fileName = tagFull;
                                    Log.Info("New filename: " + tagFull);
                                }
                                else
                                {
                                    Log.Info("Using original filename as Artist tag contains '.'");
                                }

                            if (file.ToLower().Contains(".flac"))
                            {
                                Process flac = getProcessInfo("D:\\soulseek\\flac.exe");
                                flac.Start();
                                string output = consoleBpmProcess.StandardOutput.ReadLine();
                                Log.Info("Flac process: " + output);
                                flac.WaitForExit();
                            }

                            string networkFullPath = Path.Combine(NetworkPath, fileName);
                            string localFullPath = Path.Combine(LocalPath, fileName);
                            string desktopFullPath = Path.Combine(DesktopPath, fileName);

                            FileInfo fileInfo = new FileInfo(file);
                            if (!File.Exists(localFullPath))
                            {
                                try
                                {
                                    File.Copy(file, localFullPath);
                                    Log.Info("Copying file: " + file + " to " + localFullPath);
                                }
                                catch (Exception ex)
                                {
                                    Log.Warn(ex.Message);
                                    Log.Warn("File already exists: " + file);
                                }
                            }
                            else
                            {
                                fileName = fileName + "_1";
                                Log.Warn("Copying temp file: " + fileName);
                                var localFullPath2 = Path.Combine(LocalPath, fileName);
                                File.Copy(file, localFullPath2);
                            }

                            if (File.Exists(localFullPath))
                            {
                                File.Delete(file);
                            }

                            if (IncludeShare.Equals("true", StringComparison.InvariantCultureIgnoreCase))
                            {
                                copyShare(file, networkFullPath);
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Log.Error(string.Format("Replace copy error: {0}",
                                                ex.Message + "\r\n" + "DesktopPath: " + bugPath + "\r\n"));
                    }
                }
            }
        }

        private static Process getProcessInfo(string processName)
        {
            ProcessStartInfo info = new ProcessStartInfo(processName);
            info.UseShellExecute = false;
            info.RedirectStandardError = true;
            info.RedirectStandardInput = true;
            info.RedirectStandardOutput = true;
            info.CreateNoWindow = true;
            info.ErrorDialog = false;
            info.WindowStyle = ProcessWindowStyle.Hidden;

            Process process = Process.Start(info);
            return process;
        }

        public void copyShare(string file, string networkFullPath)
        {
            ILog Log = LogManager.GetLogger(System.Reflection.MethodBase.GetCurrentMethod().DeclaringType);

            DirectoryInfo di = new DirectoryInfo(NetworkPath);
            bool networkExists = di.Exists;

            FileInfo fi = new FileInfo(networkFullPath);
            bool fileExistsOnShare = fi.Exists;

            if (networkExists)
            {
                if (!fileExistsOnShare)
                {
                    File.Copy(file, networkFullPath);
                    Log.Info("Publishing to network: " + Path.GetFileName(file));
                }
            }
            else
            {
                Log.Error("Network copy error: " + file + " NetworkPath: " + networkFullPath);
            }
        }

        //Apply file extention
        private string regexFilename(string fileName, string extention)
        {
            fileName = Regex.Replace(fileName, RegexPattern1, RegexReplace1);
            fileName = Regex.Replace(fileName, RegexPattern2, RegexReplace2);
            fileName = Regex.Replace(fileName, RegexPattern4, RegexReplace4);
            fileName = Regex.Replace(fileName, RegexPattern5, RegexReplace5);
            fileName = Regex.Replace(fileName, RegexPattern6, RegexReplace6);
            fileName = Regex.Replace(fileName, RegexPattern7, RegexReplace7);

            fileName = CultureInfo.CurrentCulture.TextInfo.ToTitleCase(Path.GetFileNameWithoutExtension(fileName));
            fileName = fileName + extention;

            return fileName;
        }

        //Remove redundant subdirs
        private void RemoveDirectories(string test1)
        {
            ILog Log = log4net.LogManager.GetLogger(System.Reflection.MethodBase.GetCurrentMethod().DeclaringType);

            try
            {
                foreach (var d in Directory.GetDirectories(test1))
                {
                    var files = Directory.GetFiles(d)
                               .Where(name => (!name.StartsWith("INCOMPLETE~") && !name.EndsWith(".mp3") && !name.EndsWith(".m4a") && !name.EndsWith(".txt")));

                    foreach (var file in files)
                    {
                        File.Delete(file);
                    }
                    if (Directory.GetFiles(d).Length == 0)
                    {
                        Log.Info("Removing... " + d + "\r\n");
                        Directory.Delete(d);
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error("Error removing folder: " + ex.Message);
            }
        }
    }
}




// Read file from the last UpdateCurrentList 
/*private List<string> ReadCurrentList(string currentListPath)
{
    currentListPath = BasePath + "\\currentList.txt";
    string[] filesRead = File.ReadAllLines(currentListPath);
    var currentList = new List<string>(filesRead);

    return currentList;
}*/


/*DateTime lastChecked = DateTime.Now;
    TimeSpan ts = DateTime.Now.Subtract(lastChecked);
    TimeSpan maxWaitTime = TimeSpan.FromMinutes(2);

    if (maxWaitTime.Subtract(ts).CompareTo(TimeSpan.Zero) > -1)
        timer.Interval = maxWaitTime.Subtract(ts).TotalMilliseconds;
    else
        timer.Interval = 1;
     */
//timer.Start();
