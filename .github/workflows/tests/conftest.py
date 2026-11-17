# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Put the bots' dir on sys.path, so their `import ghlib` works."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
