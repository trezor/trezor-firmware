from trezor import ui
import utime

ui.touch.start(lambda x, y: print('touch start %d %d\n' % (x, y)))
ui.touch.move(lambda x, y: print('touch move %d %d\n' % (x, y)))
ui.touch.end(lambda x, y: print('touch end %d %d\n' % (x, y)))

import playground
playground.run()
