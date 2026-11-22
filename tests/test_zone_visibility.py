from collections import Counter
from itertools import product
import json
import unittest

from headless import Harness


KEYS = ('SHOW_LEFT_ZONE', 'SHOW_CENTER_ZONE', 'SHOW_RIGHT_ZONE')


class ZoneVisibilityTests(unittest.TestCase):
    def test_all_visibility_combinations_keep_other_geometry_fixed(self):
        def draws(flags):
            commands = Harness(overrides=dict(zip(KEYS, flags))).snapshot()
            return Counter(map(json.dumps, commands))

        zones = [draws(tuple(int(i == k) for i in range(3))) for k in range(3)]
        for zone, texture in zip(zones, ('left_fill.png', 'dial_fill.png', 'right_fill.png')):
            self.assertTrue(any(texture in command for command in zone))
        self.assertTrue(any('curved_pedal_segments.png' in command for command in zones[1]))
        self.assertTrue(any('battery.png' in command for command in zones[1]))
        for flags in product((0, 1), repeat=3):
            with self.subTest(flags=flags):
                expected = sum((zone for on, zone in zip(flags, zones) if on), Counter())
                self.assertEqual(draws(flags), expected)
        arc = Harness(overrides={**dict.fromkeys(KEYS, 0), 'OUTER_ARC': 1})
        self.assertEqual(len(arc.frame(0)), 96)

    def test_control_applies_immediately_autosaves_and_resets(self):
        h = Harness()
        g = h.lua.globals()
        h.frame(0)
        h.lua.execute('''
          controlTab='HUD'
          ui.checkbox=function(label) return label:find('Left zone',1,true)==1 end
          script.windowMain()
        ''')
        h.commands=[]
        g.script.drawHUD()
        self.assertFalse(any(c[0]=='assets/left_fill.png' for c in h.commands))
        h.frame(.41)
        self.assertEqual(h.ini['HUD']['SHOW_LEFT_ZONE'],'0')
        h.lua.execute('''
          ui.checkbox=function() return false end
          ui.button=function(label) return controlID=='elements' and label=='Reset to defaults' end
          script.windowMain()
          ui.button=function(label) return controlID=='elements' and label=='Confirm reset' end
          script.windowMain()
        ''')
        self.assertTrue(any(c[0]=='assets/left_fill.png' for c in h.frame(.41)))
        self.assertTrue(all(h.ini['HUD'][key]=='1' for key in KEYS))
