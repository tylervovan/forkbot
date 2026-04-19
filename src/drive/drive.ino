// --- Pin Definitions ---
// RC Receiver Pins
const int ch1Pin = A4; // Channel 1 (Left/Right - X axis)
const int ch2Pin = A5; // Channel 2 (Up/Down - Y axis)
const int ch4Pin = 12; // Channel 4 (Aux Left/Right)

// Motor A (Left Motor)
const int enA = 11;    // Speed Control Pin (PWM)
const int in1 = 5;     // Direction Pin 1
const int in2 = 7;     // Direction Pin 2 (On Pin 7 for software bypass)

// Motor B (Right Motor)
const int enB = 10;    // Speed Control Pin (PWM)
const int in3 = 3;     // Direction Pin 1
const int in4 = 2;     // Direction Pin 2

// Aux Output Pin
const int auxOutPin = 13; // Output for Channel 4 trigger (Taser)

// --- Configuration ---
const int deadZone = 40; // Prevents buzzing when joystick is mostly centered
const unsigned long rcTimeout = 50000; // 50ms timeout to prevent dropped signals

void setup() {
  Serial.begin(9600);
  Serial.println("Robot starting up with Aux trigger...");

  // Receiver pins
  pinMode(ch1Pin, INPUT);
  pinMode(ch2Pin, INPUT);
  pinMode(ch4Pin, INPUT); // Initialize new channel
  
  // Motor A pins
  pinMode(enA, OUTPUT);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  
  // Motor B pins
  pinMode(enB, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);

  // Aux Output pin
  pinMode(auxOutPin, OUTPUT);
  digitalWrite(auxOutPin, LOW); // Make sure it starts turned off

  // Ensure motors are off at startup
  driveLeftMotor(0);
  driveRightMotor(0);
}

void loop() {
  // 1. Read signals with a longer timeout to catch every pulse
  int ch1 = pulseIn(ch1Pin, HIGH, rcTimeout);
  int ch2 = pulseIn(ch2Pin, HIGH, rcTimeout);
  int ch4 = pulseIn(ch4Pin, HIGH, rcTimeout); // Read new channel

  // Failsafe: If signal is 0 (disconnected) or totally out of range, force to center (1500)
  if (ch1 < 900 || ch1 > 2100) ch1 = 1500;
  if (ch2 < 900 || ch2 > 2100) ch2 = 1500;
  if (ch4 < 900 || ch4 > 2100) ch4 = 1500;

  // ==========================================
  // --- Channel 4 Aux Trigger Logic ---
  // ==========================================
  // If the stick is pushed far left (<1100) OR far right (>1900)
  if (ch4 < 1100 || ch4 > 1900) {
    digitalWrite(auxOutPin, HIGH); // Send HIGH signal out to Pin 13
  } else {
    digitalWrite(auxOutPin, LOW);  // Otherwise, keep it LOW
  }

  // 2. Map RC signals to motor speeds (-255 to 255)
  int x = map(ch1, 1000, 2000, -255, 255); // Left / Right
  int y = map(ch2, 1000, 2000, -255, 255); // Forward / Backward

  // 3. Apply Deadzone (force strictly to 0 if stick is near the middle)
  if (abs(x) < deadZone) x = 0;
  if (abs(y) < deadZone) y = 0;

  // 4. Arcade Drive Mixing
  int leftSpeed = constrain(y + x, -255, 255);
  int rightSpeed = constrain(y - x, -255, 255);

  // 5. Send speeds to the motors
  driveLeftMotor(leftSpeed);
  driveRightMotor(rightSpeed);

  // ==========================================
  // --- Serial Monitor Diagnostic Output ---
  // ==========================================
  Serial.print("X: "); Serial.print(ch1);
  Serial.print(" | Y: "); Serial.print(ch2);
  Serial.print(" | Ch4: "); Serial.print(ch4);
  
  // NEW: Taser Status Output
  if (digitalRead(auxOutPin) == HIGH) {
    Serial.print(" || *** TASER IS ON *** ");
  } else {
    Serial.print(" || Taser: OFF ");
  }
  
  Serial.print(" || Motor L: "); Serial.print(leftSpeed);
  Serial.print(" | Motor R: "); Serial.println(rightSpeed);

  delay(20); // Small delay for stability
}

// ==========================================
// --- Helper Functions for Motor Control ---
// ==========================================

void driveLeftMotor(int speed) {
  if (speed > 0) { // Forward
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
    analogWrite(enA, speed);
  } else if (speed < 0) { // Backward
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
    analogWrite(enA, abs(speed));
  } else { // Stop
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(enA, 0);
  }
}

void driveRightMotor(int speed) {
  if (speed > 0) { // Forward
    digitalWrite(in3, HIGH);
    digitalWrite(in4, LOW);
    analogWrite(enB, speed);
  } else if (speed < 0) { // Backward
    digitalWrite(in3, LOW);
    digitalWrite(in4, HIGH);
    analogWrite(enB, abs(speed));
  } else { // Stop
    digitalWrite(in3, LOW);
    digitalWrite(in4, LOW);
    analogWrite(enB, 0);
  }
}