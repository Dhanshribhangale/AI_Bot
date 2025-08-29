#!/usr/bin/env python3
"""
Demo script for AI Voice Bot Voice Input functionality
This script demonstrates how to interact with the bot using voice messages
"""

import asyncio
import websockets
import json
import time

class VoiceBotDemo:
    def __init__(self, uri="ws://localhost:8765"):
        self.uri = uri
        self.session_id = None
        
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print("✅ Connected to AI Voice Bot")
            
            # Wait for welcome message
            welcome_msg = await self.websocket.recv()
            welcome_data = json.loads(welcome_msg)
            self.session_id = welcome_data.get('client_id', 'unknown')
            print(f"🤖 {welcome_data.get('message', 'Welcome!')}")
            print(f"🆔 Session ID: {self.session_id[:8]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def send_voice_message(self, message):
        """Send a voice message to the bot"""
        try:
            voice_payload = {
                "type": "voice_message",
                "message": message,
                "client_agent": "voice-demo-script"
            }
            
            print(f"🎤 Sending voice message: '{message}'")
            await self.websocket.send(json.dumps(voice_payload))
            
            # Wait for response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('type') == 'voice_message_response':
                print(f"🤖 AI Response: {response_data.get('message', 'No response')}")
                print(f"⏱️ Response time: {response_data.get('response_time_ms', 0)}ms")
                return True
            else:
                print(f"❌ Unexpected response: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending voice message: {e}")
            return False
    
    async def send_text_message(self, message):
        """Send a regular text message to the bot"""
        try:
            text_payload = {
                "type": "message",
                "message": message,
                "client_agent": "voice-demo-script"
            }
            
            print(f"📝 Sending text message: '{message}'")
            await self.websocket.send(json.dumps(text_payload))
            
            # Wait for response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('type') == 'assistant':
                print(f"🤖 AI Response: {response_data.get('message', 'No response')}")
                print(f"⏱️ Response time: {response_data.get('response_time_ms', 0)}ms")
                return True
            else:
                print(f"❌ Unexpected response: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending text message: {e}")
            return False
    
    async def close(self):
        """Close the WebSocket connection"""
        if hasattr(self, 'websocket'):
            await self.websocket.close()
            print("🔌 Connection closed")

async def run_demo():
    """Run the voice input demo"""
    print("🎤 AI Voice Bot - Voice Input Demo")
    print("=" * 50)
    
    demo = VoiceBotDemo()
    
    # Connect to the bot
    if not await demo.connect():
        print("❌ Failed to connect. Make sure the bot is running!")
        return
    
    try:
        # Demo 1: Voice message (simulated)
        print("\n🎯 Demo 1: Voice Message Processing")
        print("-" * 30)
        
        voice_messages = [
            "Hello, how are you today?",
            "What's the weather like?",
            "Tell me a joke",
            "What can you help me with?"
        ]
        
        for i, message in enumerate(voice_messages, 1):
            print(f"\n🎤 Voice Message {i}:")
            success = await demo.send_voice_message(message)
            if success:
                print("✅ Voice message processed successfully!")
            else:
                print("❌ Voice message failed!")
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        # Demo 2: Regular text message
        print("\n🎯 Demo 2: Regular Text Message")
        print("-" * 30)
        
        text_message = "This is a regular text message to compare with voice messages."
        success = await demo.send_text_message(text_message)
        if success:
            print("✅ Text message processed successfully!")
        else:
            print("❌ Text message failed!")
        
        print("\n🎉 Demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
    finally:
        await demo.close()

async def interactive_demo():
    """Run an interactive demo where user can type messages"""
    print("🎤 AI Voice Bot - Interactive Demo")
    print("=" * 50)
    print("Type your messages and see AI responses!")
    print("Type 'voice: <message>' to simulate voice input")
    print("Type 'quit' to exit")
    print("-" * 50)
    
    demo = VoiceBotDemo()
    
    if not await demo.connect():
        print("❌ Failed to connect. Make sure the bot is running!")
        return
    
    try:
        while True:
            user_input = input("\n💬 You: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower().startswith('voice:'):
                # Simulate voice message
                message = user_input[6:].strip()
                if message:
                    await demo.send_voice_message(message)
            elif user_input:
                # Regular text message
                await demo.send_text_message(user_input)
            else:
                print("❌ Please enter a message")
                
    except KeyboardInterrupt:
        print("\n⏹️ Interactive demo interrupted")
    except Exception as e:
        print(f"\n❌ Interactive demo error: {e}")
    finally:
        await demo.close()

async def main():
    """Main demo function"""
    print("Choose demo mode:")
    print("1. Automated demo (recommended for first time)")
    print("2. Interactive demo (type your own messages)")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            await run_demo()
        elif choice == "2":
            await interactive_demo()
        else:
            print("❌ Invalid choice. Running automated demo...")
            await run_demo()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    print("🚀 Starting AI Voice Bot Demo...")
    print("Make sure the bot is running with: python main.py")
    print()
    
    asyncio.run(main())
