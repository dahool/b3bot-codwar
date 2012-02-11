import b3
import b3.plugin

class DummyPlugin(b3.plugin.Plugin):

    def onStartup(self):
        self.bot("onStartup")
        
    def onLoadConfig(self):
        self.bot("onLoadConfig")
                       
if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import superadmin
    import time
        
    p = DummyPlugin(fakeConsole,'@b3/extplugins/conf/dummy.xml')
    p.onStartup()
        
    superadmin.connects(cid=1)
    time.sleep(5)
    p.loadConfig()
