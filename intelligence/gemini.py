from vision import camera
from sensors import ultrasonic
from actuators import motor
from actuators import servo
from google.genai import types
from google.gemini import client

class GeminiController:
    def __init__(self):
        self.client = client.Client()
        self.model = "gemini-2.0-flash"

    def ask(self, question):
        response = self.client.generate_content(
            model=self.model,
            contents=[question],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=types.Schema(
                    type=types.Schema.Type.OBJECT,
                    properties=[
                        types.Property(
                            name="motor_command",
                            type=types.Schema.Type.STRING,
                            description="Command for the motor controller."
                        ),
                        types.Property(
                            name="servo_command",
                            type=types.Schema.Type.STRING,
                            description="Command for the servo controller."
                        )
                    ]
                )
            )
        )
        return response.text