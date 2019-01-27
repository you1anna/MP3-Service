using System.Configuration;


namespace mp3Service
{
    public static class Config
    {
        public static string FlacPath
        {
            get { return ConfigurationManager.AppSettings[@"FlacPath"]; }
        }

        public static string BasePath
        { 
            get { return ConfigurationManager.AppSettings[@"BasePath"]; }
        }
        public static string NetworkPath
        {
            get { return ConfigurationManager.AppSettings[@"NetworkPath"]; }
        }
        public static string LocalPath
        {
            get { return ConfigurationManager.AppSettings[@"LocalPath"]; }
        }
        public static string PollInterval
        {
            get { return ConfigurationManager.AppSettings["PollInterval"]; }
        }
        public static string IncludeShare
        {
            get { return ConfigurationManager.AppSettings["IncludeShare"]; }
        }
        public static string DesktopPath
        {
            get { return ConfigurationManager.AppSettings["DesktopPath"]; }
        }
    }
}
