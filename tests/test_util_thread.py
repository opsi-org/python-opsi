#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing threading utilities.

:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import datetime
import time
import threading
import unittest
from contextlib import contextmanager

from OPSI.Util.Thread import ThreadPoolException, ThreadPool, getGlobalThreadPool, KillableThread


class ThreadPoolTestCase(unittest.TestCase):
    POOL_SIZE = 10

    def setUp(self):
        self.pool = ThreadPool(size=self.POOL_SIZE, autostart=False)
        self.pool.start()

    def tearDown(self):
        self.pool.stop()

    def adjustSize(self, size):
        self.pool.adjustSize(size=size)

    def test_WorkerCreation(self):
        self.pool.adjustSize(size=10)
        self.assertEqual(10, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" % (10, len(self.pool.worker)))

    def test_stopPool(self):
        self.pool.adjustSize(size=10)
        for _ in range(5):
            time.sleep(0.1)
        numThreads = threading.activeCount() - len(self.pool.worker)
        self.pool.stop()

        self.assertEqual(0, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" % (0, len(self.pool.worker)))
        self.assertFalse(self.pool.started, "Expected pool to have stopped, but it hasn't")
        self.assertEqual(threading.activeCount(), numThreads, "Expected %s thread to be alive, but got %s" % (numThreads, threading.activeCount()))

    def test_workerCallback(self):
        self.pool.adjustSize(2)

        result = []
        def assertCallback(success, returned, errors):
            result.append(success)
            result.append(returned)
            result.append(errors)


        self.pool.addJob(function=(lambda: 'test'), callback=assertCallback)

        #give thread time to finish
        time.sleep(1)

        self.assertEqual(True, result[0])
        self.assertEqual(result[1], 'test')
        self.assertEqual(None, result[2])

    def test_workerCallbackWithException(self):
        self.pool.adjustSize(2)

        result = []
        def assertCallback(success, returned, errors):
            result.append(success)
            result.append(returned)
            result.append(errors)

        def raiseError():
            raise Exception("TestException")

        self.pool.addJob(function=raiseError, callback=assertCallback)

        #give thread time to finish
        time.sleep(1)

        self.assertEqual(False, result[0])
        self.assertEqual(None, result[1])
        self.assertNotEqual(None, result[2])

    def test_invalidThreadPoolSize(self):
        self.assertRaises(ThreadPoolException, self.pool.adjustSize, -1)

    def test_adjustPoolSize(self):
        self.pool.adjustSize(size=2)
        self.pool.adjustSize(size=10)

        time.sleep(1)

        self.assertEqual(10, self.pool.size, "Expected pool size to be %s, but got %s." % (10 , self.pool.size))
        self.assertEqual(10, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" %(10, len(self.pool.worker)))

        self.pool.adjustSize(size=2)

        self.assertEqual(2, self.pool.size, "Expected pool size to be %s, but got %s." % (2 , self.pool.size))
        self.assertEqual(2, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" % (2, len(self.pool.worker)))

    def test_floodPool(self):
        self.pool.adjustSize(2)

        results = []
        def callback(success, returned, errors):
            results.append(success)

        def waitJob():
            for _ in range(3):
                time.sleep(1)

        for _ in range(5):
            self.pool.addJob(waitJob, callback=callback)

        self.assertEquals(2, len(self.pool.worker),
            "Expected %s worker in pool, but got %s" % (2, len(self.pool.worker)))
        self.assertTrue(self.pool.jobQueue.unfinished_tasks > len(self.pool.worker),
        "Expected more tasks in Queue than workers in pool, but got %s tasks and %s worker" % (self.pool.jobQueue.unfinished_tasks, len(self.pool.worker)))

        for _ in range(10):
            time.sleep(0.4)
        self.assertEquals(5, len(results), "Expected %s results but, but got %s" % (5, len(results)))

    def test_globalPool(self):
        pool1 = getGlobalThreadPool()
        pool2 = getGlobalThreadPool()

        self.assertTrue(isinstance(pool1, ThreadPool), "Expected %s to be a ThreadPool instance." % pool1)
        self.assertEqual(pool1, pool2)

        pool2.adjustSize(5)
        self.assertEqual(pool1.size, 5)

        pool1.stop()

    def test_dutyAfterNoDuty(self):
        self.pool.adjustSize(5)
        self.pool.stop()
        self.pool.start()

        results = []
        def callback(success, returned, errors):
            results.append(success)

        def shortJob():
            _ = 10 * 10

        for _ in range(10):
            self.pool.addJob(shortJob, callback=callback)

        time.sleep(1)
        self.assertEquals(10, len(results), "Expected %s results, but got %s" % (10, len(results)))

        time.sleep(2)
        results = []
        for _ in range(10):
            self.pool.addJob(shortJob, callback=callback)
        time.sleep(1)
        self.assertEquals(10, len(results), "Expected %s results, but got %s" % (10, len(results)))

    def test_grow(self):
        self.pool.adjustSize(2)
        self.pool.stop()
        self.pool.start()

        results = []
        def callback(success, returned, errors):
            results.append(success)

        def sleepJob():
            time.sleep(2)

        for _ in range(10):
            self.pool.addJob(sleepJob, callback=callback)
        time.sleep(3)
        self.assertEqual(len(results), 2, "Expected %s results, but got %s" % (2, len(results)))

        self.pool.adjustSize(10)
        time.sleep(3)
        self.assertEquals(len(results), 10, "Expected %s results, but got %s" % (10, len(results)))

    def test_shrink(self):
        self.pool.adjustSize(5)
        self.pool.stop()
        self.pool.start()

        results = []
        def callback(success, returned, errors):
            results.append(success)

        def sleepJob():
            time.sleep(2)

        for _ in range(12):
            self.pool.addJob(sleepJob, callback=callback)
        time.sleep(3)
        self.assertEqual(len(results), 5, "Expected %s results, but got %s" % (5, len(results)))

        self.pool.adjustSize(1)
        time.sleep(2)
        self.assertEquals(len(results), 10,  "Expected %s results, but got %s" % (10, len(results)))
        time.sleep(2)
        self.assertEquals(len(results), 11,  "Expected %s results, but got %s" % (11, len(results)))
        time.sleep(2)
        self.assertEquals(len(results), 12,  "Expected %s results, but got %s" % (12, len(results)))

    def testDecreasingUsageCount(self):
        self.pool.increaseUsageCount()
        self.assertEquals(2, self.pool.usageCount)

        self.pool.decreaseUsageCount()
        self.assertEquals(1, self.pool.usageCount)

    def testDecreasingUsageCountBelowZeroStopsThreadPool(self):
        self.assertTrue(self.pool.started)
        self.assertEquals(1, self.pool.usageCount)
        self.pool.decreaseUsageCount()
        self.assertEquals(0, self.pool.usageCount)
        self.assertFalse(self.pool.started)


class KillableThreadTestCase(unittest.TestCase):
    def test_terminating_running_thread(self):
        """
        It must be possible to interrupt running threads even though
        they may still be processing.
        """

        class ThreadWithTimeout(KillableThread):
            def __init__(self, testCase):
                super(ThreadWithTimeout, self).__init__()

                self.testCase = testCase

            def run(self):
                start = datetime.datetime.now()
                timeout = datetime.timedelta(seconds=30)

                while datetime.datetime.now() < (start + timeout):
                    time.sleep(0.1)

                self.testCase.fail("Thread did not get killed in time.")

        @contextmanager
        def getTestThread():
            runningThread = ThreadWithTimeout(self)
            runningThread.start()
            try:
                yield runningThread
            finally:
                runningThread.join(2)

        with getTestThread() as runningThread:
            assert runningThread.isAlive()

            runningThread.terminate()

            runChecks = 0
            while runningThread.isAlive():
                time.sleep(0.1)
                runChecks += 1

                if runChecks > 30:
                    self.fail("Thread should be stopped by now.")

            self.assertFalse(runningThread.isAlive(), "Thread should be killed.")


if __name__ == '__main__':
    unittest.main()
