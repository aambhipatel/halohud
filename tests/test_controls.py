import unittest
from headless import Harness


class ControlsTests(unittest.TestCase):
    def test_override_helpers_preserve_legacy_ids_and_match_case_insensitively(self):
        Harness().lua.execute("""
          local M=require('controls_model')
          local rows,lookup=M.parseList('Car_one;CAR_ONE, Car_Two')
          assert(#rows==2 and rows[1].name=='Car_one' and lookup.car_two)
          assert(M.editList('Car_one;CAR_ONE, Car_Two',' car_one ',false)=='Car_one;CAR_ONE, Car_Two')
          assert(M.editList('Car_one;CAR_ONE, Car_Two','car_one',true)=='Car_Two')
          assert(M.editList('Car_one','BMW_M3',false)=='Car_one, BMW_M3')
          assert(M.editList('Car_one','missing',true)=='Car_one')
          local value,reason=M.editList('Car_one','two ids',false)
          assert(not value and reason=='Enter one car folder ID.')
        """)

    def test_reset_uses_schema_defaults_and_only_selected_keys(self):
        Harness().lua.execute("""
          local M=require('controls_model');local S=require('settings')
          local values={scale=1.4,drsVolume=.2,debugMode=true,debugDRS=true,drsForceOn='car_a',drsForceOff='car_b',
            theme='AMBER',lockHUD=true}
          local function set(key,value) values[key]=value end
          M.reset('layout',S.schema,set)
          assert(values.scale==1 and values.lockHUD and values.drsVolume==.2 and values.theme=='AMBER')
          for section in pairs(M.sections) do
            if section~='overrides' then M.reset(section,S.schema,set) end
          end
          assert(values.debugMode and values.lockHUD and values.drsForceOn=='car_a' and values.drsForceOff=='car_b')
          assert(values.debugDRS==false and values.demo=='AUTO')
          M.reset('overrides',S.schema,set)
          assert(values.debugMode and values.lockHUD and values.drsForceOn=='' and values.drsForceOff=='')
        """)

    def test_all_suppression_messages_and_audio_error_details(self):
        Harness().lua.execute("""
          local M=require('controls_model')
          for key,text in pairs(M.reasons) do
            assert(M.skipped(key)=='Last skipped chime: '..text)
          end
          assert(M.skipped('started in zone')=='Last skipped chime: you started inside a zone.')
          assert(M.skipped('AudioEvent:start failed: native details')=='Last skipped chime: CSP could not start playback.')
          assert(M.skipped('unknown private details')=='Last skipped chime: the cue was skipped. See DRS debug logging for details.')
        """)

    def test_status_text_for_conflict_missing_sound_and_spline(self):
        Harness().lua.execute("""
          local M=require('controls_model');local s={}
          M.status(s,'Ready','file',3,'car','unknown',false,false,'AUTO',nil)
          assert(s.soundTone=='good' and s.trackText=='Track: 3 DRS zones loaded')
          assert(s.carText=='Car ID: car' and s.modeText=='This car: not classified yet')
          M.status(s,'WAV missing or unreadable',nil,0,'car','free_use',true,true,'SPLINE','override off')
          assert(s.soundTone=='bad' and s.modeText=='This car: forced off')
          assert(s.trackText:find('need track zone data',1,true) and s.skipped:find('force-off',1,true))
          M.status(s,'Ready','file',nil,'car','no_drs',false,false,'AUTO',nil)
          assert(s.modeText=='This car: no DRS support' and s.trackTone=='warn')
        """)

    def test_changed_status_only_reformats_when_input_changes(self):
        Harness().lua.execute("""
          local M=require('controls_model');local s={}
          M.status(s,'Ready','file',3,'car','free_use',false,false,'AUTO','paused')
          local render=M.skipped;local changes=0
          M.skipped=function(...) changes=changes+1;return render(...) end
          for i=1,20 do M.status(s,'Ready','file',3,'car','free_use',false,false,'AUTO','paused') end
          assert(changes==0)
          M.status(s,'Ready','file',3,'car','free_use',false,false,'AUTO','replay')
          assert(changes==1)
        """)

    def test_controls_tabs_and_advanced_sections(self):
        h=Harness(overrides={'DEBUG_MODE':1,'DEBUG_DRS':1});h.frame(.02)
        h.lua.execute("""
          tabs={};local tab=ui.tabItem
          ui.tabItem=function(name,flags,body) tabs[#tabs+1]=name;tab(name,flags,body) end
          controlTab='Advanced';openControlSections={}
          toggles={};ui.checkbox=function(label) toggles[label]=true;return false end
          script.windowMain()
          assert(table.concat(tabs,',')=='General,HUD,DRS Chime,Advanced')
          assert(not toggles['Force demo telemetry'] and not toggles['DRS debug logging'])
          openControlSections.Diagnostics=true;script.windowMain()
          assert(toggles['Force demo telemetry'] and toggles['DRS debug logging'] and toggles['Test cue when DRS opens'])
        """)
        self.assertEqual(h.ini['HUD']['DEBUG_DRS'],'1')

    def test_live_override_edits_save_and_show_with_debug_mode(self):
        h=Harness(demo='OFF',overrides={'DEBUG_MODE':1});h.lua.execute("""
          player={index=0,physicsAvailable=true,drsPresent=true,driverName=function() return 'Player' end}
          ac.getSim=function() return {carsCount=1,currentSessionIndex=0} end
          ac.getCar=function() return player end
          ac.getCarID=function() return 'player_car' end
          controlTab='DRS Chime'
          ac.getTrackDataFilename=function() return 'test_zones' end
          io.load=function() return '[ZONE_0]\\nSTART=.2\\nEND=.4' end
          texts={};ui.textWrapped=function(t) texts[t]=true end
          ui.button=function(label) return label=='Add current car to force-on' or label=='Add current car to force-off' end
        """)
        h.frame(.02);g=h.lua.globals();g.script.windowMain();h.frame(.41)
        self.assertEqual(h.ini['HUD']['DRS_FORCE_ON'],'PLAYER_CAR')
        self.assertEqual(h.ini['HUD']['DRS_FORCE_OFF'],'PLAYER_CAR')
        h.lua.execute("ui.button=function() return false end;script.windowMain()")
        self.assertTrue(g.texts['This car: forced off'])
        self.assertTrue(g.texts['Track: 1 DRS zone loaded'])
        self.assertTrue(g.texts['Conflict: at least one car is in both lists. Force-off wins.'])
        h.lua.execute("ui.button=function(label) return label=='Remove' end;script.windowMain()")
        h.frame(.41)
        self.assertEqual(h.ini['HUD']['DRS_FORCE_ON'],'')
        self.assertEqual(h.ini['HUD']['DRS_FORCE_OFF'],'')

    def test_diagnostics_settings_are_gated_without_mutation(self):
        Harness().lua.execute('''
          local S=require('settings')
          local c=S.read(nil)
          assert(c.debugMode==false and c.lockHUD==false)
          c.debugDRS,c.debugDRSActive,c.profileCPU,c.demo=true,true,true,'ON'
          local d={}
          S.diagnostics(c,d)
          assert(not d.drsLog and not d.activeCue and not d.profile and not d.forceDemo)
          assert(c.debugDRS and c.debugDRSActive and c.profileCPU and c.demo=='ON')
          c.debugMode=true
          S.diagnostics(c,d)
          assert(d.drsLog and d.activeCue and d.profile and d.forceDemo)
          c.debugDRS=false
          S.diagnostics(c,d)
          assert(not d.drsLog and not d.activeCue and d.profile and d.forceDemo)
        ''')
 
    def test_debug_toggle_hides_controls_and_skips_hidden_status_work(self):
        h=Harness(overrides={'DEBUG_DRS':1,'PROFILE_CPU':1})
        h.lua.execute(r'''
          local M=require('controls_model')
          local status=M.status
          statusCalls=0
          M.status=function(...) statusCalls=statusCalls+1;return status(...) end
          logCount=0;ac.log=function() logCount=logCount+1 end
          controlTab='General'
          toggleDebug=false
          local toggles={}
          ui.checkbox=function(label) toggles[label]=true;return label=='Debug Mode' and toggleDebug end
          local headers,sections,texts,buttons,combos={},{},{},{},{}
          ui.header=function(label) headers[label]=true end
          ui.textWrapped=function(label) texts[label]=true end
          local tree=ui.treeNode
          ui.treeNode=function(name,...) sections[name]=true;tree(name,...) end
          ui.button=function(label) buttons[label]=true;return false end
          ui.combo=function(label) combos[label]=true end
          script.update(.02)
          script.windowMain();assert(toggles['Debug Mode'] and toggles['Lock HUD position'])
          controlTab='DRS Chime'
          script.windowMain()
          assert(statusCalls==0 and not headers['Live status'] and not headers['Car overrides'])
          assert(not buttons['Add current car to force-on'] and buttons['Test chime'] and buttons['Reset section'])
          assert(combos['##drsSound'] and combos['##triggerMode'])
          assert(texts['The selected sound could not play. Choose a readable WAV from the sounds folder.'])
          controlTab='Advanced'
          script.windowMain();assert(sections['DRS tuning'] and not sections.Diagnostics and not sections['Live telemetry'])
          controlTab='General';toggleDebug=true;script.windowMain();toggleDebug=false
          controlTab='DRS Chime';script.windowMain()
          assert(statusCalls==1 and headers['Live status'] and headers['Car overrides'])
          controlTab='Advanced';script.windowMain()
          assert(sections.Diagnostics and sections['Live telemetry'] and toggles['DRS debug logging'])
          assert(toggles['Force demo telemetry'] and toggles['Measure Lua CPU time'] and toggles['Test cue when DRS opens'])
          controlTab='General';toggleDebug=true;script.windowMain();toggleDebug=false
          local previous=logCount
          script.update(.41)
          controlTab='DRS Chime';script.windowMain()
          assert(statusCalls==1 and logCount==previous)
        ''')
        self.assertEqual(h.ini['HUD']['DEBUG_MODE'],'0')
        self.assertEqual(h.ini['HUD']['DEBUG_DRS'],'1')
        self.assertEqual(h.ini['HUD']['PROFILE_CPU'],'1')

    def test_narrow_controls_keep_positive_width_for_test_chime_row(self):
        h=Harness();h.frame(.02)
        h.lua.execute("""
          controlWidth=280;controlTab='DRS Chime';testSeen=false
          ui.setNextItemWidth=function(w) assert(w>0 and w<=controlWidth) end
          ui.button=function(label) if label=='Test chime' then testSeen=true end;return false end
          script.windowMain();assert(testSeen)
        """)
