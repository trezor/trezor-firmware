import sys
from PyQt4.Qt import QApplication, QWidget, QGridLayout, QVBoxLayout
from PyQt4.QtGui import QPushButton, QLineEdit, QSizePolicy, QRegExpValidator
from PyQt4.QtCore import QObject, SIGNAL, QRegExp

class PinButton(QPushButton):
    def __init__(self, password, encoded_value):
        super(PinButton, self).__init__()
        self.password = password
        self.encoded_value = encoded_value

        QObject.connect(self, SIGNAL('clicked()'), self._pressed)

    def _pressed(self):
        self.password.setText(self.password.text() + str(self.encoded_value))
        self.password.setFocus()

class PinMatrixWidget(QWidget):
    '''
        Displays widget with nine blank buttons and password box.
        Encodes button clicks into sequence of numbers for passing
        into PinAck messages of Trezor.
    '''
    def __init__(self, parent=None):
        super(PinMatrixWidget, self).__init__(parent)
        
        self.buttons = []

        self.password = QLineEdit()
        self.password.setValidator(QRegExpValidator(QRegExp('[1-9]+'), None))
        self.password.setEchoMode(QLineEdit.Password)

        grid = QGridLayout()
        grid.setSpacing(0)
        for x in range(9):
            button = PinButton(self.password, x + 1)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.buttons.append(button)
            grid.addWidget(button, x / 3, x % 3)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(self.password)

        self.setLayout(vbox)
        self.move(300, 150)

    def get_value(self):
        return self.password.text()

if __name__ == '__main__':
    '''
        Demo application showing PinMatrix widget in action
    '''
    a = QApplication(sys.argv)

    matrix = PinMatrixWidget()

    def clicked():
        print "PinMatrix value is", matrix.get_value()
        sys.exit()

    ok = QPushButton('OK')
    QObject.connect(ok, SIGNAL('clicked()'), clicked)

    vbox = QVBoxLayout()
    vbox.addWidget(matrix)
    vbox.addWidget(ok)

    w = QWidget()
    w.setLayout(vbox)
    w.show()

    a.exec_()
