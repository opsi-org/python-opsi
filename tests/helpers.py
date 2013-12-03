#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import shutil
import tempfile

# FAILED (SKIP=1, errors=28, failures=6)



def copyTestfileToTemporaryFolder(filename):
    temporary_folder = tempfile.mkdtemp()
    shutil.copy(filename, temporary_folder)

    (_, new_filename) = os.path.split(filename)

    return os.path.join(temporary_folder, new_filename)
