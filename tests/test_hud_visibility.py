import unittest
from headless import Harness

class HudVisibilityTests(unittest.TestCase):
    def test_game_visibility_hides_and_restores_without_changing_enabled(self):
        h=Harness();self.assertTrue(h.frame())
        h.lua.execute('hudUi=ac.getUI();ac.getUI=function() return hudUi end')
        g=h.lua.globals()
        for flag in ('appsHidden','uiHidden'):
            g.hudUi[flag]=True
            self.assertEqual(h.frame(),[])
            g.hudUi[flag]=False
            self.assertTrue(h.frame())
        self.assertEqual(h.ini['HUD']['ENABLED'],'1')
        self.assertEqual(h.saves,0)

    def test_settings_save_while_hidden_and_explicit_disable_stays_disabled(self):
        h=Harness();h.frame()
        h.lua.execute('''hudUi=ac.getUI();hudUi.appsHidden=true
          ac.getUI=function() return hudUi end
          ui.checkbox=function(label) return label=='Show HUD' end
        ''')
        h.lua.globals().script.windowMain()
        self.assertEqual(h.frame(0.41),[])
        self.assertEqual(h.saves,1)
        self.assertEqual(h.ini['HUD']['ENABLED'],'0')
        h.lua.globals().hudUi.appsHidden=False
        self.assertEqual(h.frame(),[])

if __name__=='__main__':unittest.main()
