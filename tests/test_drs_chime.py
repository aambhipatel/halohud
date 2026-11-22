import unittest
from headless import Harness, ROOT


class DRSChimeTests(unittest.TestCase):
    def test_plain_lua_suite(self):
        h = Harness()
        h.lua.execute((ROOT/'tests/test_drs_zone_math.lua').read_text(encoding='utf-8'))

    def detector(self):
        h = Harness()
        h.lua.execute("""
          D=require('drs_chime'); Z=require('drs_zones'); state=D.new()
          cfg={drsCooldown=1.5,drsMargin=40,drsFreeSeconds=2}
          car={drsPresent=true,drsAvailable=false,splinePosition=.18,speedKmh=180}
          zones=Z.parse('[ZONE_0]\\nSTART=.2\\nEND=.22\\nDETECTION=.17\\n[ZONE_1]\\nSTART=.24\\nEND=.29')
          function frame(pos, available, dt, override, id, sessionReady)
            car.splinePosition=pos;car.drsAvailable=available
            local fire,zone=D.update(state,car,id or 'car_folder',dt or .2,5000,zones,cfg,override,nil,sessionReady)
            if fire then D.played(state,zone) end
            return fire
          end
        """)
        return h

    def test_in_zone_edge_only_once_and_next_zone_rearms(self):
        h = self.detector()
        h.lua.execute("""
          assert(#zones==2 and zones[1].detection==.17)
          assert(not frame(.188,false));assert(not frame(.193,false));assert(not frame(.198,false))
          assert(frame(.201,true));assert(state.classification=='zone_restricted')
          for i=1,8 do assert(not frame(.211,false)) end
          assert(not frame(.213,true));assert(state.reason=='already cued in zone')
          for _,p in ipairs({.218,.223,.228,.233,.238}) do assert(not frame(p,false)) end
          assert(frame(.243,true))
        """)

    def test_free_use_dwell_is_sticky_and_per_folder(self):
        self.detector().lua.execute("""
          assert(not frame(.184,false));assert(not frame(.184,true,.25))
          for i=1,6 do assert(not frame(.184,true,.25));assert(state.classification=='unknown') end
          assert(not frame(.184,true,.25));assert(state.classification=='free_use')
          D.reset(state);assert(not frame(.196,false));assert(not frame(.201,true));assert(state.reason=='free-use car')
          assert(not frame(.205,false));assert(not frame(.209,true,.2,'on'))
          for i=1,6 do assert(not frame(.209,true,.25,'on')) end
          for _,p in ipairs({.214,.219,.224,.229,.234,.239}) do assert(not frame(p,true,.2,'on')) end
          assert(frame(.244,true,.2,'on'))
          D.reset(state);state.lastPlayed=-math.huge
          assert(not frame(.197,false,.2,nil,'other'))
          assert(frame(.201,true,.2,nil,'other'));assert(state.classes.car_folder=='free_use')
          D.session(state);assert(state.classes.car_folder==nil)
        """)

    def test_no_zones_first_clean_edge_and_guarded_pit_classification(self):
        self.detector().lua.execute("""
          zones={};assert(not frame(.1,true));assert(not frame(.102,false));assert(frame(.105,true))
          D.session(state);car.isInPitlane=true
          assert(not frame(.12,true,.25));assert(state.classification=='unknown')
          for i=1,24 do assert(not frame(.12,true,.25));assert(state.classification=='unknown') end
          for i=1,5 do assert(not frame(.12,true,.25)) end
          assert(state.classification=='free_use')
          D.session(state);car.isInPitlane=false;car.speedKmh=0
          assert(not frame(.12,true));assert(state.classification=='unknown')
          D.session(state);car.speedKmh=180;car.drsPresent=false
          assert(not frame(.11,true,.2,'on'));assert(state.classification=='no_drs')
        """)

    def test_loading_inside_and_teleport_do_not_chime(self):
        self.detector().lua.execute("""
          assert(not frame(.204,false));assert(not frame(.206,true))
          D.session(state);assert(not frame(.6,false));assert(not frame(.203,true))
          assert(state.reason=='teleport');assert(not frame(.206,true))
        """)

    def test_layout_then_base_lookup_and_unreadable_fallback(self):
        self.detector().lua.execute("""
          ac.getTrackDataFilename=function() return 'layout/data/drs_zones.ini' end
          ac.FolderID={Root=0};ac.getTrackID=function() return 'example' end
          ac.getFolder=function() return 'root' end
          io.load=function(path)
            if path:find('^layout') then error('denied') end
            assert(path=='root/content/tracks/example/data/drs_zones.ini')
            return '[ZONE_0]\\nSTART=.9\\nEND=.1'
          end
          local data,path=Z.load();assert(#data==1 and path:find('^root/'))
          io.load=function() return 'invalid INI' end
          local missing,_,reason=Z.load();assert(#missing==0 and reason)
        """)

    def integration(self, **overrides):
        options={'DRS_CHIME_ENABLED':1,'DEBUG_MODE':1,'DEBUG_DRS':1,**overrides}
        h=Harness(demo='OFF',overrides=options)
        h.lua.execute("""
          starts,created,disposed,scans,reads,fileChecks=0,0,0,0,0,0
          messages={}; ac.log=function(value) messages[#messages+1]=value end
          sim={carsCount=1,currentSessionIndex=0,focusedCar=0,trackLengthM=5000}
          car={index=0,physicsAvailable=true,drsPresent=true,drsAvailable=false,splinePosition=.18,
            speedKmh=180,rpm=2000,gear=2,driverName=function() return 'Driver' end}
          ac.getCar=function(index) assert(index==0);return car end
          ac.getSim=function() return sim end
          ac.getCarID=function() return 'car_folder' end
          ac.getTrackDataFilename=function() return 'zones' end
          io.load=function() reads=reads+1;return '[ZONE_0]\\nSTART=.2\\nEND=.4' end
          io.scanDir=function() scans=scans+1;return {'Second.WAV','notes.txt','drs_chime.wav'} end
          io.fileExists=function(path) fileChecks=fileChecks+1;return not missing end
          ac.AudioEvent={fromFile=function(options,reverb)
            assert(not options.loop and not options.use3D and not reverb)
            created=created+1;file=options.filename
            local consumed,released=false,false
            return {isValid=function() return not consumed and not released and not invalid end,
              isPlaying=function() return true end,
              start=function(self)
                assert(not consumed and not released,'one-shot was already consumed')
                starts=starts+1;consumed=true;volume=self.volume;assert(self.cameraInteriorMultiplier==1)
                return self
              end,
              dispose=function() assert(not released);released=true;disposed=disposed+1 end}

          end}
        """)
        return h

    def test_runtime_replay_pause_focus_and_override_off(self):
        for suppression in ('isPaused','isReplayActive','isReplayOnlyMode','focusedCar','override'):
            with self.subTest(suppression=suppression):
                overrides={'DRS_FORCE_ON':'Car_Folder','DRS_FORCE_OFF':'car_folder'} if suppression=='override' else {}
                h=self.integration(**overrides);h.lua.globals().car.splinePosition=.197;h.frame(.02)
                if suppression=='focusedCar': h.lua.execute('sim.focusedCar=1')
                elif suppression!='override': h.lua.execute(f'sim.{suppression}=true')
                h.lua.execute('car.drsAvailable=true;car.splinePosition=.201');h.frame(.02)
                self.assertEqual(h.lua.globals().starts,0)
                if suppression=='focusedCar': h.lua.execute('sim.focusedCar=0')
                elif suppression!='override': h.lua.execute(f'sim.{suppression}=false')
                h.frame(.02);self.assertEqual(h.lua.globals().starts,0)

    def test_runtime_missing_file_logs_once_and_keeps_drawing(self):
        h=self.integration();h.lua.execute('missing=true')
        self.assertTrue(h.frame(.02));h.lua.execute('car.drsAvailable=true;car.splinePosition=.201')
        for _ in range(5): self.assertTrue(h.frame(.02))
        g=h.lua.globals();self.assertEqual(g.starts,0);self.assertEqual(g.created,0)
        self.assertEqual(len([m for m in g.messages.values() if 'WAV missing or unreadable (' in m]),1)
        self.assertEqual(g.scans,1);self.assertEqual(g.reads,1)

    def test_runtime_playback_and_selector_persist_with_case(self):
        h=self.integration();h.frame(.02)
        for p in (.184,.188,.192,.196,.199):
            h.lua.globals().car.splinePosition=p;h.frame(.02)
        h.lua.execute('car.drsAvailable=true;car.splinePosition=.201');h.frame(.02)
        g=h.lua.globals();self.assertEqual(g.starts,1);self.assertEqual(g.created,1)
        self.assertAlmostEqual(g.volume,.65)
        h.lua.execute("""
          ui.combo=function(_,_,_,content) content() end
          ui.selectable=function(name) return name=='Second.WAV' end
          script.windowMain()
        """)
        h.frame(.41)
        self.assertEqual(g.created,1);self.assertEqual(g.disposed,1)
        self.assertEqual(g.scans,1);self.assertEqual(h.ini['HUD']['DRS_SOUND'],'Second.WAV')
        h.lua.execute("ui.button=function(label) return label=='Test chime' end;script.windowMain()")
        self.assertEqual(g.created,2);self.assertTrue(g.file.endswith('/sounds/Second.WAV'))

    def test_denied_entries_stay_quiet_and_cooldown_blocks_next_edge(self):
        self.detector().lua.execute("""
          for _,p in ipairs({.184,.19,.195,.2,.205,.21,.215,.22,.225,.23,.235,.24,.245}) do
            assert(not frame(p,false))
          end
          assert(frame(.25,true));zones={};assert(not frame(.253,false))
          assert(not frame(.256,true));assert(state.reason=='cooldown')
        """)

    def test_missing_zones_continuous_travel_marks_free_use(self):
        self.detector().lua.execute("""
          zones={};assert(not frame(.1,true,.25))
          for i=1,50 do assert(not frame(.1+.007*i,true,.25)) end
          assert(state.classification=='free_use')
          assert(not frame(.454,false,.25));assert(not frame(.458,true,.25))
        """)

    def test_restart_resets_first_sample_even_with_same_session_index(self):
        h=self.integration();h.lua.globals().car.splinePosition=.197;h.frame(.02)
        h.lua.execute('sessionStartCallback(0,true);car.splinePosition=.201;car.drsAvailable=true')
        h.frame(.02)
        self.assertEqual(h.lua.globals().starts,0)
        self.assertEqual(h.lua.globals().reads,2)

    def test_debug_button_bypasses_replay_enable_and_hidden_hud(self):
        h=self.integration(DRS_CHIME_ENABLED=0, ENABLED=0, DRS_CHIME_VOLUME=0)
        h.lua.execute("""
          sim.isReplayActive=true;sim.isPaused=true;car.drsPresent=false
          io.fileSize=function() return 8054 end
          ui.button=function(label) return label=='Test chime' end
        """)
        h.frame(.02)
        h.lua.globals().script.windowMain()
        h.frame(.02)
        g=h.lua.globals()
        self.assertEqual(g.starts,1);self.assertEqual(g.disposed,0)
        self.assertAlmostEqual(g.volume,.65)
        log='\n'.join(g.messages.values())
        for detail in ('enabled=false','Resolved WAV path:', 'io.fileExists pcall=true returned=true',
                       'io.fileSize (bytes) pcall=true returned=8054','use3D=false, loop=false',
                       'AudioEvent.volume assignment/readback', 'AudioEvent:start pcall=true'):
            self.assertIn(detail,log)

    def test_live_trigger_uses_update_with_no_hud_draw(self):
        h=self.integration(ENABLED=0);g=h.lua.globals()
        g.car.splinePosition=.197;g.script.update(.02)
        g.car.splinePosition=.201;g.car.drsAvailable=True;g.script.update(.02)
        self.assertEqual(g.starts,1)
        self.assertIn('chime fired | playback=true','\n'.join(g.messages.values()))

    def test_wav_header_and_pcall_failure_details(self):
        h=self.integration();h.lua.execute(r"""
          local A=require('drs_audio')
          local fmt=string.char(1,0,1,0,68,172,0,0,136,88,1,0,2,0,16,0)
          local header='RIFF'..string.char(38,0,0,0)..'WAVEJUNK'..string.char(1,0,0,0)..'x'..string.char(0)
            ..'fmt '..string.char(16,0,0,0)..fmt
          local info=A.wavHeader(header)
          assert(info:find('sampleRate=44100 Hz bitDepth=16 channels=1',1,true))
          io.fileSize=function() return #header end
          io.load=function() return header end
          ac.AudioEvent.fromFile=function() error('native loader error') end
          ui.button=function(label) return label=='Test chime' end
        """)
        h.lua.globals().script.update(.02)
        h.lua.globals().script.windowMain()
        log='\n'.join(h.lua.globals().messages.values())
        self.assertEqual(log.count('WAV header: format='),1)
        self.assertIn('ac.AudioEvent.fromFile pcall=false error=',log)
        self.assertIn('native loader error',log)
        self.assertIn('Test chime | playback=false',log)

    def test_repeated_test_clicks_create_fresh_events_without_file_checks(self):
        h=self.integration(DRS_CHIME_ENABLED=0)
        h.lua.execute("io.fileSize=function() return 52 end;ui.button=function(label) return label=='Test chime' end")
        h.frame(.02)
        g=h.lua.globals()
        checks,reads=g.fileChecks,g.reads
        for i in range(12):
            g.script.windowMain()
            if i%2==0: g.script.update(.02)
            self.assertEqual(g.starts,i+1)
            self.assertEqual(g.created,i+1)
            self.assertEqual(g.disposed,i)
        self.assertEqual((g.fileChecks,g.reads),(checks,reads))
        self.assertNotIn('WAV could not be loaded','\n'.join(g.messages.values()))
        g.releaseCallback()
        self.assertEqual(g.disposed,12)

    def test_two_real_zone_entries_create_fresh_events_with_diagnostics(self):
        h=self.integration(ENABLED=0);g=h.lua.globals()
        h.lua.execute(r"""io.load=function()
          return '[ZONE_0]\nSTART=.2\nEND=.22\n[ZONE_1]\nSTART=.28\nEND=.32'
        end""")
        g.car.splinePosition=.197;g.script.update(.25)
        g.car.splinePosition=.201;g.car.drsAvailable=True;g.script.update(.25)
        g.car.drsAvailable=False
        for step in range(1,20):
            g.car.splinePosition=.201+.004*step;g.script.update(.25)
        g.car.splinePosition=.281;g.car.drsAvailable=True;g.script.update(.25)
        self.assertEqual((g.created,g.starts,g.disposed),(2,2,1))
        log='\n'.join(g.messages.values())
        self.assertEqual(log.count('chime fired | playback=true | fresh valid=true | start succeeded=true'),2)
        self.assertIn('classification: zone_restricted',log)
        self.assertIn('in-zone=1',log)
        self.assertIn('suppression: DRS unavailable in zone',log)

    def test_live_debug_heartbeat_and_immediate_edges_with_hud_disabled(self):
        h=self.integration(ENABLED=0);g=h.lua.globals()
        h.lua.execute('now=0;os.preciseClock=function() return now end;car.splinePosition=.201')
        g.script.update(.02)
        g.now=.2;g.car.drsAvailable=True;g.car.drsActive=True;g.script.update(.02)
        log='\n'.join(g.messages.values())
        self.assertEqual(log.count('state | car='),1)
        self.assertIn('drsAvailable false -> true | splinePosition=0.201 | in-zone=0',log)
        self.assertIn('drsActive nil -> true | splinePosition=0.201 | in-zone=0',log)
        g.now=1.01;g.sim.isPaused=True;g.script.update(.02)
        log='\n'.join(g.messages.values())
        self.assertEqual(log.count('state | car='),2)
        self.assertIn('replay=false | paused=true | trigger mode=DRS availability (auto) | last suppression=paused',log)

    def test_active_edge_diagnostic_bypasses_free_use_and_zone_gate(self):
        h=self.integration(ENABLED=0, DEBUG_DRS_ACTIVE_CHIME=1);g=h.lua.globals()
        g.car.drsAvailable=True;g.car.speedKmh=180;g.car.drsActive=False
        for _ in range(9): g.script.update(.25)
        g.car.drsActive=True;g.script.update(.02)
        g.script.update(.02)
        self.assertEqual(g.starts,1)
        log='\n'.join(g.messages.values())
        self.assertIn('unknown -> free_use (sustained availability away from known zones)',log)
        self.assertIn('drsActive false -> true',log)
        self.assertIn('trigger=debug drsActive',log)
        g.car.drsActive=False;g.script.update(.02)
        g.sim.isReplayActive=True;g.car.drsActive=True;g.script.update(.02)
        self.assertEqual(g.starts,1)

    def test_las_vegas_jump_limit_handles_driving_and_timing_line(self):
        h=self.integration();g=h.lua.globals()
        h.lua.execute(r"""io.load=function()
          return '[ZONE_0]\nSTART=.876445\nEND=.0221685\n[ZONE_1]\nSTART=.124952\nEND=.255582\n[ZONE_2]\nSTART=.621411\nEND=.823163'
        end""")
        g.sim.trackLengthM=6200;g.car.speedKmh=360
        for pos in (.995,.997,.999,.001,.003,.005):
            g.car.splinePosition=pos;g.script.update(.124)
        log='\n'.join(g.messages.values())
        self.assertNotIn('state reset: teleport',log)
        self.assertIn('in-zone=0',log)
        g.car.splinePosition=.5;g.script.update(.016)
        log='\n'.join(g.messages.values())
        self.assertIn('state reset: teleport | splinePosition=0.500000 | spline delta=+0.495000',log)
        self.assertIn('raw delta=+0.495000 | limit=0.004032',log)

    def test_startup_grid_and_stops_in_zone_do_not_poison_auto(self):
        self.detector().lua.execute("""
          car.speedKmh=0
          for i=1,60 do assert(not frame(.18,true,.25,nil,nil,false)) end
          for i=1,60 do assert(not frame(.18,true,.25)) end
          assert(state.classification=='unknown')
          car.speedKmh=180
          assert(not frame(.185,false,.25));assert(not frame(.191,false,.25));assert(not frame(.197,false,.25))
          assert(frame(.201,true,.25));assert(state.classification=='zone_restricted')
          car.speedKmh=0
          for i=1,60 do assert(not frame(.201,true,.25)) end
          assert(state.classification=='zone_restricted')
        """)

    def test_stationary_evidence_after_driving_and_reset_grace(self):
        self.detector().lua.execute("""
          assert(not frame(.175,false,.25));assert(not frame(.18,false,.25))
          car.speedKmh=0
          for i=1,23 do assert(not frame(.18,true,.25));assert(state.classification=='unknown') end
          for i=1,8 do assert(not frame(.18,true,.25)) end
          assert(state.classification=='free_use')
          D.reset(state);assert(not frame(.18,false,.25));assert(state.classification=='free_use')
        """)

    def test_spline_requires_forward_start_crossing_and_wraps(self):
        self.detector().lua.execute("""
          cfg.drsTriggerMode='SPLINE';zones={{start=.998,finish=.03}}
          assert(not frame(.995,true,.25));assert(not frame(.997,true,.25))
          assert(frame(.001,true,.25));assert(not frame(.005,false,.25))
          D.session(state);state.lastPlayed=-math.huge
          assert(not frame(.020,false,.25));assert(not frame(.016,false,.25));assert(not frame(.012,true,.25))
          assert(state.reason=='started in zone')
          D.session(state);assert(not frame(.4,false,.25));assert(not frame(.001,false,.25));assert(state.reason=='teleport')
        """)

    def test_force_on_plays_spline_with_flat_availability_and_force_off_wins(self):
        for force_off in ('','car_folder'):
            with self.subTest(force_off=force_off):
                h=self.integration(DRS_FORCE_ON='car_folder',DRS_FORCE_OFF=force_off);g=h.lua.globals()
                g.car.splinePosition=.197;g.script.update(.25)
                g.car.splinePosition=.201;g.script.update(.25)
                self.assertEqual(g.starts,0 if force_off else 1)
                if not force_off:
                    self.assertIn('trigger=spline START','\n'.join(g.messages.values()))

    def test_debug_off_keeps_force_on_and_test_sound_but_stops_diagnostics(self):
        h=self.integration(DEBUG_MODE=0,ENABLED=0,
                           DRS_FORCE_ON='car_folder',DEBUG_DRS_ACTIVE_CHIME=1,DRS_CHIME_VOLUME=0)
        g=h.lua.globals()
        g.car.splinePosition=.19;g.car.drsActive=False;g.script.update(.25)
        g.car.drsActive=True;g.script.update(.25)
        self.assertEqual(g.starts,0)  # Hidden active-edge diagnostic is disabled.
        h.lua.execute("controlTab='DRS Chime';ui.button=function(label) return label=='Test chime' end")
        g.script.windowMain()
        self.assertEqual(g.starts,1)
        self.assertEqual(g.volume,.65)
        h.lua.execute("ui.button=function() return false end")
        # Restore positive gameplay volume through the same controls path.
        h.lua.execute("controlTab='DRS Chime';ui.slider=function(id,v) if id=='##chimeVolume' then return 65 end;return v end")
        g.script.windowMain()
        g.car.splinePosition=.197;g.script.update(.25)
        g.car.splinePosition=.201;g.script.update(.25)
        self.assertEqual(g.starts,2)  # Spline cue, flat availability, no controls draw.
        self.assertEqual(list(g.messages.values()),[])
        g.script.update(.41)
        self.assertEqual(h.ini['HUD']['DEBUG_DRS_ACTIVE_CHIME'],'1')
        self.assertEqual(h.ini['HUD']['DEBUG_DRS'],'1')

    def test_fresh_event_gain_is_restored_if_native_start_resets_it(self):
        h=self.integration();g=h.lua.globals()
        h.lua.execute("""
          ac.AudioEvent.fromFile=function()
            event={isValid=function() return true end,isPlaying=function() return true end,dispose=function() end}
            event.start=function(self)
              assert(self==event and self.volume==.65 and self.cameraInteriorMultiplier==1)
              self.volume=.25;self.cameraInteriorMultiplier=.25
              return self
            end
            return event
          end
          ui.button=function(label) return label=='Test chime' end
        """)
        g.script.update(.02);g.script.windowMain()
        self.assertAlmostEqual(g.event.volume,.65)
        self.assertEqual(g.event.cameraInteriorMultiplier,1)
        self.assertIn('requested=0.65 | pre-start=0.65 | post-start=0.25','\n'.join(g.messages.values()))

    def test_trigger_selector_saves_mode_and_explains_force_on(self):
        h=self.integration();g=h.lua.globals();g.script.update(.02)
        h.lua.execute("""
          controlTab='DRS Chime'
          ui.combo=function(label,_,_,children) if label=='##triggerMode' then children() end end
          ui.selectable=function(label) return label=='When I cross a zone line' end
          ui.itemHovered=function() return true end
          ui.setTooltip=function(value) if value:find("Force-on",1,true) then tooltip=value end end
          script.windowMain()
        """)
        g.script.update(.41)
        self.assertEqual(h.ini['HUD']['DRS_TRIGGER_MODE'],'SPLINE')
        self.assertIn('skipping the availability edge and free-use classification',g.tooltip)
        # Drive to the activation line inside the normal spline jump threshold.
        for pos in (.184,.188,.192,.196,.199,.201):
            g.car.splinePosition=pos;g.script.update(.02)
        self.assertEqual(g.starts,1)
