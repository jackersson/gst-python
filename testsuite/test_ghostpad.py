# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# gst-python - Python bindings for GStreamer
# Copyright (C) 2002 David I. Lehn
# Copyright (C) 2004 Johan Dahlin
# Copyright (C) 2005 Edward Hervey
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA

from common import gst, unittest, TestCase

import sys
import gc
import gobject

class SrcBin(gst.Bin):
    def prepare(self):
        src = gst.element_factory_make('fakesrc')
        self.add(src)
        pad = src.get_pad("src")
        ghostpad = gst.GhostPad("src", pad)
        self.add_pad(ghostpad)
gobject.type_register(SrcBin)

class SinkBin(gst.Bin):
    def prepare(self):
        sink = gst.element_factory_make('fakesink')
        self.add(sink)
        pad = sink.get_pad("sink")
        ghostpad = gst.GhostPad("sink", pad)
        self.add_pad(ghostpad)
gobject.type_register(SinkBin)

        
class PipeTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.pipeline = gst.Pipeline()
        self.assertEquals(self.pipeline.__gstrefcount__, 1)
        self.assertEquals(sys.getrefcount(self.pipeline), 3)

        self.src = SrcBin()
        self.src.prepare()
        self.sink = SinkBin()
        self.sink.prepare()
        self.assertEquals(self.src.__gstrefcount__, 1)
        self.assertEquals(sys.getrefcount(self.src), 3)
        self.assertEquals(self.sink.__gstrefcount__, 1)
        self.assertEquals(sys.getrefcount(self.sink), 3)

    def tearDown(self):
        self.assertEquals(self.pipeline.__gstrefcount__, 1)
        self.assertEquals(sys.getrefcount(self.pipeline), 3)
        self.assertEquals(self.src.__gstrefcount__, 2)
        self.assertEquals(sys.getrefcount(self.src), 3)
        self.assertEquals(self.sink.__gstrefcount__, 2)
        self.assertEquals(sys.getrefcount(self.sink), 3)
        gst.debug('deleting pipeline')
        del self.pipeline
        self.gccollect()

        self.assertEquals(self.src.__gstrefcount__, 1) # parent gone
        self.assertEquals(self.sink.__gstrefcount__, 1) # parent gone
        self.assertEquals(sys.getrefcount(self.src), 3)
        self.assertEquals(sys.getrefcount(self.sink), 3)
        gst.debug('deleting src')
        del self.src
        self.gccollect()
        gst.debug('deleting sink')
        del self.sink
        self.gccollect()

        TestCase.tearDown(self)
        
    def testBinState(self):
        self.pipeline.add(self.src, self.sink)
        self.src.link(self.sink)

        self.pipeline.set_state_async(gst.STATE_PLAYING)
        while True:
            (ret, cur, pen) = self.pipeline.get_state(timeout=None)
            if ret == gst.STATE_CHANGE_SUCCESS and cur == gst.STATE_PLAYING:
                break

        self.pipeline.set_state_async(gst.STATE_NULL)
        while True:
            (ret, cur, pen) = self.pipeline.get_state(timeout=None)
            if ret == gst.STATE_CHANGE_SUCCESS and cur == gst.STATE_NULL:
                break

    def testProbedLink(self):
        self.pipeline.add(self.src)
        pad = self.src.get_pad("src")
        # FIXME: adding a probe to the ghost pad does not work atm
        # id = pad.add_buffer_probe(self._src_buffer_probe_cb)
        realpad = pad.get_target()
        self._probe_id = realpad.add_buffer_probe(self._src_buffer_probe_cb)

        self._probed = False
        
        self.pipeline.set_state_async(gst.STATE_PLAYING)
        while True:
            (ret, cur, pen) = self.pipeline.get_state(timeout=None)
            if ret == gst.STATE_CHANGE_SUCCESS and cur == gst.STATE_PLAYING:
                break

        while not self._probed:
            pass

        self.pipeline.set_state_async(gst.STATE_NULL)
        while True:
            (ret, cur, pen) = self.pipeline.get_state(timeout=None)
            if ret == gst.STATE_CHANGE_SUCCESS and cur == gst.STATE_NULL:
                break

    def _src_buffer_probe_cb(self, pad, buffer):
        gst.debug("received probe on pad %r" % pad)
        self._probed = True
        gst.debug('adding sink bin')
        self.pipeline.add(self.sink)
        # this seems to get rid of the warnings about pushing on an unactivated
        # pad
        self.sink.set_state(gst.STATE_PAUSED)
        gst.debug('linking')
        self.src.link(self.sink)
        gst.debug('removing buffer probe id %r' % self._probe_id)
        pad.remove_buffer_probe(self._probe_id)
        self._probe_id = None
        gst.debug('done')

if __name__ == "__main__":
    unittest.main()
