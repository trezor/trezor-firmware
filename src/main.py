from trezor import ui
import layout
import utime

layout.show_send('1BitkeyP2nDd5oa64x7AjvBbbwST54W5Zmx2', 110.126967)

# ui.touch.callback_start(lambda x, y: print('touch start %d %d\n', x, y))
# ui.touch.callback_move(lambda x, y: print('touch move %d %d\n', x, y))
# ui.touch.callback_end(lambda x, y: print('touch end %d %d\n', x, y))

import playground
playground.run()
