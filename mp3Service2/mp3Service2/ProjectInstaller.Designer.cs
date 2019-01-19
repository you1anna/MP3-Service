namespace mp3Service2
{
    partial class ProjectInstaller
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary> 
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Component Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.mp3Service2Installer = new System.ServiceProcess.ServiceProcessInstaller();
            this.serviceInstaller1 = new System.ServiceProcess.ServiceInstaller();
            // 
            // mp3Service2Installer
            // 
            this.mp3Service2Installer.Account = System.ServiceProcess.ServiceAccount.LocalService;
            this.mp3Service2Installer.Password = null;
            this.mp3Service2Installer.Username = null;
            this.mp3Service2Installer.AfterInstall += new System.Configuration.Install.InstallEventHandler(this.mp3Service2Installer_AfterInstall);
            // 
            // serviceInstaller1
            // 
            this.serviceInstaller1.ServiceName = "mp3Service2";
            this.serviceInstaller1.StartType = System.ServiceProcess.ServiceStartMode.Automatic;
            this.serviceInstaller1.AfterInstall += new System.Configuration.Install.InstallEventHandler(this.serviceInstaller1_AfterInstall);
            // 
            // ProjectInstaller
            // 
            this.Installers.AddRange(new System.Configuration.Install.Installer[] {
            this.mp3Service2Installer,
            this.serviceInstaller1});

        }

        #endregion

        private System.ServiceProcess.ServiceProcessInstaller mp3Service2Installer;
        private System.ServiceProcess.ServiceInstaller serviceInstaller1;
    }
}