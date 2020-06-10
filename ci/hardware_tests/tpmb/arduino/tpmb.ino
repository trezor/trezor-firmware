#include <Servo.h>

#define right_unpressed 79
#define right_pressed 0
#define left_unpressed 0
#define left_pressed 79


String command;
Servo servo_right;
Servo servo_left;

void setup() {
    // Starting the serial console
    Serial.begin(9600); 
    
    // Attaching both servos
    servo_right.attach(7);
    servo_left.attach(8);
    
    // Setting them un unpressed position
    servo_right.write(right_unpressed);
    servo_left.write(left_unpressed);
    Serial.println("Ready for commands, press my buttons!");
}
 
void loop() {
    if(Serial.available()){
        command = Serial.readStringUntil('\n');
        
        if(command.equals("right press")){
          Serial.println("Pressing right button.");
          servo_right.write(right_pressed);
        }

        else if(command.equals("right unpress")){
          Serial.println("Unpressing right button.");
          servo_right.write(right_unpressed);
        }

        else if(command.equals("left press")){
          Serial.println("Pressing the left button.");
          servo_left.write(left_pressed);
        }

        else if(command.equals("left unpress")){
          Serial.println("Unpressing the left button.");
          servo_left.write(left_unpressed);
        }

        else if(command.equals("left click")){
          Serial.println("Clicking the left button.");
          servo_left.write(left_pressed);
          delay(500);
          servo_left.write(left_unpressed);
        }

        else if(command.equals("right click")){
          Serial.println("Clicking the right button.");
          servo_right.write(right_pressed);
          delay(500);
          servo_right.write(right_unpressed);
        }

        else if(command.equals("all press")){
          Serial.println("Pressing all buttons.");
          servo_right.write(right_pressed);
          servo_left.write(left_pressed);
        }

        else if(command.equals("all unpress")){
          Serial.println("Unpressing all buttons.");
          servo_right.write(right_unpressed);
          servo_left.write(left_unpressed);
        }
    }
}
